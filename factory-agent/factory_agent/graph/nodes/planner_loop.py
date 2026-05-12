"""Phase 3 planner loop: Planner → DecisionGuard → Tool execution → Planner."""

from __future__ import annotations

import json
import re
from typing import Any, Literal

from ...config import Settings
from ...llm.models import build_planner_chat_model
from ...observability.telemetry import log_event, log_llm_prompt
from ...schemas import ControlAction, PlannerDecision, ToolCall, ToolInfo
from ..errors import LangGraphPlannerError
from ..planner_graph_helpers import _deterministic_plan_repair, _message_content_text, _tool_cards
from ..state import AgentPlanOutput, AgentPlanStep, AgentState, user_query_text

RouteKey = Literal["clarify_end", "continue_planner", "decision_guard", "synthesize_plan"]


def _get_by_path(obj: dict[str, Any], path: str) -> Any:
    cur: Any = obj
    for part in path.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def _constraint_violated(*, constraint: dict[str, Any], tool_args: dict[str, Any]) -> bool:
    if constraint.get("strength") == "soft":
        return False
    field = str(constraint.get("field") or "")
    if not field:
        return False
    op = str(constraint.get("operator") or "=")
    expected = constraint.get("value")
    actual = _get_by_path(tool_args, field) if "." in field else tool_args.get(field)
    if op == "=":
        if actual is None:
            return True
        if isinstance(expected, str) and isinstance(actual, str):
            return expected.strip().upper() != actual.strip().upper()
        return actual != expected
    if op == "!=":
        return actual == expected
    if op == "in":
        if not isinstance(expected, list):
            return True
        return actual not in expected
    if op == "not_in":
        if not isinstance(expected, list):
            return False
        return actual in expected
    return False


def _collect_ref_tokens(obj: Any, out: set[str]) -> None:
    if isinstance(obj, str) and obj.startswith("$ref:") and len(obj) < 200:
        out.add(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            _collect_ref_tokens(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _collect_ref_tokens(v, out)


def _assign_missing_output_refs(raw_calls: list[dict[str, Any]], tools_by_name: dict[str, ToolInfo]) -> None:
    for i, tc in enumerate(raw_calls):
        tool = tools_by_name.get(str(tc.get("tool_name") or ""))
        if not tool or tool.is_read_only:
            continue
        ref = tc.get("output_ref")
        if isinstance(ref, str) and ref.startswith("$ref:"):
            continue
        nm = re.sub(r"[^A-Za-z0-9_]+", "_", str(tc.get("tool_name") or "tool"))[:40]
        tc["output_ref"] = f"$ref:{nm}_{i}"


def _forward_ref_violation(raw_calls: list[dict[str, Any]], tools_by_name: dict[str, ToolInfo]) -> str | None:
    declared: dict[str, int] = {}
    for i, tc in enumerate(raw_calls):
        tool = tools_by_name.get(str(tc.get("tool_name") or ""))
        if not tool or tool.is_read_only:
            continue
        ref = tc.get("output_ref")
        if isinstance(ref, str) and ref.startswith("$ref:"):
            if ref in declared:
                return f"duplicate_output_ref:{ref}"
            declared[ref] = i
    for i, tc in enumerate(raw_calls):
        need: set[str] = set()
        _collect_ref_tokens(tc.get("args"), need)
        for r in need:
            if r not in declared:
                return f"unknown_ref:{r}"
            if declared[r] >= i:
                return f"forward_or_self_ref:{r}"
    return None


def _constraints_violated(*, constraints: list[dict[str, Any]], tool_calls: list[dict[str, Any]]) -> bool:
    for tc in tool_calls:
        args = tc.get("args") if isinstance(tc.get("args"), dict) else {}
        for c in constraints:
            if not isinstance(c, dict):
                continue
            if _constraint_violated(constraint=c, tool_args=args):
                return True
    return False


def _intent_dependencies_satisfied(working: list[dict[str, Any]], idx: int) -> bool:
    intent = working[idx]
    for dep_id in intent.get("depends_on") or []:
        if not isinstance(dep_id, str):
            continue
        dep = next((x for x in working if x.get("intent_id") == dep_id), None)
        if dep is None:
            continue
        if dep.get("status") != "completed":
            return False
    return True


def _next_active_intent_index(working: list[dict[str, Any]], start: int) -> int | None:
    for i in range(max(0, start), len(working)):
        st = working[i].get("status")
        if st in ("pending", "in_progress") and _intent_dependencies_satisfied(working, i):
            return i
    return None


def _cascade_cancel_dependents(working: list[dict[str, Any]], failed_id: str, *, reason: str) -> None:
    bad: set[str] = {failed_id}
    while True:
        progressed = False
        for it in working:
            if it.get("status") != "pending":
                continue
            deps = {str(d) for d in (it.get("depends_on") or []) if isinstance(d, str)}
            if deps & bad:
                it["status"] = "cancelled_due_to_dependency_failure"
                it["failure_reason"] = reason
                iid = str(it.get("intent_id") or "")
                if iid:
                    bad.add(iid)
                progressed = True
        if not progressed:
            break


def _risk_for_tools(tool_calls: list[ToolCall], tools_by_name: dict[str, ToolInfo]) -> str:
    for tc in tool_calls:
        info = tools_by_name.get(tc.tool_name)
        if not info:
            continue
        if info.method != "GET" or not info.is_read_only:
            return "write_dry_run"
    return "read"


def _build_planner_decision_prompt(*, state: AgentState, current: dict[str, Any], tools_by_name: dict[str, ToolInfo]) -> str:
    tool_cards = state.get("tool_cards") or _tool_cards(list(tools_by_name.values()))
    recent_outputs = state.get("tool_outputs") or []
    truncated_at = int(state.get("tool_outputs_truncated_at") or 0)
    if isinstance(recent_outputs, list):
        visible = recent_outputs[max(0, truncated_at) :]
        tail = visible[-4:]
    else:
        tail = []
    failed = state.get("failed_strategies") or []
    return (
        "You are the factory planner brain (Phase 3). Emit ONE strict JSON object only — no markdown.\n"
        "Shape:\n"
        '{"intent_id":"string","kind":"domain_tool|parallel_read_tools|request_clarification|request_approval|'
        'intent_completed|intent_failed|halt",'
        '"tool_calls":[{"tool_name":"string","args":{}}],'
        '"control_action":null|{"name":"request_clarification|mark_intent_completed|mark_intent_failed","payload":{}},'
        '"decision_summary":"string",'
        '"risk_level":"read|write_dry_run|write_commit|high_risk"}\n'
        "Rules:\n"
        "- intent_id MUST match the current intent id.\n"
        "- For domain_tool / parallel_read_tools, only use tool_name values from the tool catalog.\n"
        "- For dependent writes in one decision, use $ref:... placeholders in args and optional output_ref per write call; "
        "the guard auto-fills missing output_ref.\n"
        "- Prefer read-only GET tools before writes; keep args minimal and schema-safe.\n"
        "- If mandatory user facts are missing, use kind request_clarification with control_action "
        '{"name":"request_clarification","payload":{"question":"..."}} and empty tool_calls.\n'
        "- When the current intent is fully satisfied using tool results already in state, use intent_completed "
        'with empty tool_calls and a short summary in decision_summary.\n'
        "- If the intent is impossible or unsafe, use intent_failed with decision_summary explaining why.\n"
        "- halt stops planning for this session (rare; catastrophic issues only).\n"
        f"Current intent JSON: {json.dumps(current, ensure_ascii=False)}\n"
        f"User query: {user_query_text(state)}\n"
        f"Recent tool_outputs (last up to 4): {json.dumps(tail, ensure_ascii=False)}\n"
        f"failed_strategies: {json.dumps(failed[-3:], ensure_ascii=False)}\n"
        f"Tool catalog: {json.dumps(tool_cards, ensure_ascii=False)}\n"
    )


def _coerce_decision_dict(raw: dict[str, Any], *, tools_by_name: dict[str, ToolInfo]) -> PlannerDecision:
    tcs: list[ToolCall] = []
    for item in raw.get("tool_calls") or []:
        if not isinstance(item, dict):
            continue
        name = item.get("tool_name")
        if not isinstance(name, str) or not name.strip():
            continue
        args = item.get("args") if isinstance(item.get("args"), dict) else {}
        out_ref = item.get("output_ref")
        out_ref_s = out_ref.strip() if isinstance(out_ref, str) else None
        tcs.append(
            ToolCall(
                tool_name=name.strip(),
                args=args,
                output_ref=out_ref_s if out_ref_s and out_ref_s.startswith("$ref:") else None,
            )
        )
    ctrl = raw.get("control_action")
    control = ControlAction.model_validate(ctrl) if isinstance(ctrl, dict) else None
    kind = raw.get("kind")
    if kind not in (
        "domain_tool",
        "parallel_read_tools",
        "request_clarification",
        "request_approval",
        "intent_completed",
        "intent_failed",
        "halt",
    ):
        kind = "halt"
    summary = raw.get("decision_summary")
    if not isinstance(summary, str) or not summary.strip():
        summary = "Planner step."
    risk = raw.get("risk_level")
    if risk not in ("read", "write_dry_run", "write_commit", "high_risk"):
        risk = _risk_for_tools(tcs, tools_by_name)
    intent_id = str(raw.get("intent_id") or "")
    if not intent_id:
        intent_id = "unknown"
    return PlannerDecision(
        intent_id=intent_id,
        kind=kind,  # type: ignore[arg-type]
        tool_calls=tcs,
        control_action=control,
        decision_summary=summary.strip(),
        risk_level=risk,  # type: ignore[arg-type]
        violates_constraints=bool(raw.get("violates_constraints")),
    )


def _fallback_decision_from_repair(
    *,
    clause: str,
    scoped_tools: list[ToolInfo],
    current_intent: dict[str, Any],
) -> PlannerDecision | None:
    repaired = _deterministic_plan_repair(clause, scoped_tools, context={})
    if repaired is None or not repaired.steps:
        return None
    first = repaired.steps[0]
    tools_by_name = {t.name: t for t in scoped_tools}
    tcs = [ToolCall(tool_name=first.tool_name, args=dict(first.args or {}))]
    return PlannerDecision(
        intent_id=str(current_intent.get("intent_id") or "unknown"),
        kind="domain_tool",
        tool_calls=tcs,
        decision_summary="Deterministic repair selected the first safe tool step.",
        risk_level=_risk_for_tools(tcs, tools_by_name),
    )


def make_planner_node(settings: Settings):
    async def planner_node(state: AgentState) -> dict[str, Any]:
        if not (settings.planner_openai_base_url or settings.openai_api_key):
            raise LangGraphPlannerError(
                "LangGraph planner requires PLANNER_OPENAI_BASE_URL (or OPENAI_BASE_URL) or OPENAI_API_KEY."
            )

        scoped = state.get("scoped_tools") or []
        tools_by_name = {t.name: t for t in scoped if getattr(t, "name", None)}
        working = [dict(x) for x in (state.get("working_intents") or [])]
        if not working:
            working = [
                {
                    "intent_id": "intent-fallback",
                    "description": user_query_text(state),
                    "depends_on": [],
                    "explicit_constraints": [],
                    "status": "pending",
                    "category": "unknown",
                }
            ]

        iteration = int(state.get("planner_iteration") or 0) + 1
        max_loops = max(settings.max_plan_steps * 3, 12)

        if iteration > max_loops:
            rep = _deterministic_plan_repair(user_query_text(state), scoped, context=state.get("context") or {})
            if rep is not None:
                steps = [
                    ToolCall(tool_name=s.tool_name, args=dict(s.args or {}))
                    for s in rep.steps[: settings.max_plan_steps]
                ]
                dec = PlannerDecision(
                    intent_id=str(working[min(state.get("intent_cursor") or 0, len(working) - 1)].get("intent_id")),
                    kind="domain_tool",
                    tool_calls=steps,
                    decision_summary="Iteration cap reached; using deterministic repair sequence.",
                    risk_level=_risk_for_tools(steps, tools_by_name),
                )
                return {
                    "planner_iteration": iteration,
                    "working_intents": working,
                    "pending_decision": dec.model_dump(mode="json"),
                    "next_route": "decision_guard",
                    "status": "planning",
                }
            return {
                "planner_iteration": iteration,
                "working_intents": working,
                "next_route": "synthesize_plan",
                "status": "planning",
            }

        cursor = int(state.get("intent_cursor") or 0)
        nxt = _next_active_intent_index(working, cursor)
        if nxt is None:
            return {
                "planner_iteration": iteration,
                "working_intents": working,
                "pending_decision": None,
                "next_route": "synthesize_plan",
                "status": "validating",
            }

        if nxt != cursor:
            cursor = nxt
        current = working[cursor]
        if current.get("status") == "pending":
            current["status"] = "in_progress"
        working[cursor] = current

        prompt = _build_planner_decision_prompt(state=state, current=current, tools_by_name=tools_by_name)
        log_llm_prompt(
            component="planner_loop",
            backend="langgraph",
            model=settings.planner_model,
            prompt=prompt,
            metadata={"intent_cursor": cursor, "intent_id": current.get("intent_id")},
        )
        model = build_planner_chat_model(settings, json_mode=True)
        try:
            raw_resp = await model.ainvoke(prompt)
        except Exception as exc:
            raise LangGraphPlannerError(str(exc)) from exc
        content = _message_content_text(raw_resp)
        try:
            parsed = json.loads(content)
        except Exception:
            parsed = {}
        if not isinstance(parsed, dict):
            parsed = {}

        decision = _coerce_decision_dict(parsed, tools_by_name=tools_by_name)
        if decision.intent_id != str(current.get("intent_id")):
            fb = _fallback_decision_from_repair(
                clause=str(current.get("description") or user_query_text(state)),
                scoped_tools=scoped,
                current_intent=current,
            )
            if fb is not None:
                decision = fb
            else:
                decision = PlannerDecision(
                    intent_id=str(current.get("intent_id")),
                    kind="request_clarification",
                    tool_calls=[],
                    control_action=None,
                    decision_summary="Model returned mismatched intent_id or invalid JSON.",
                    risk_level="read",
                )

        if decision.kind in ("domain_tool", "parallel_read_tools") and decision.tool_calls:
            unknown = [tc.tool_name for tc in decision.tool_calls if tc.tool_name not in tools_by_name]
            if unknown:
                log_event(
                    "planner_unknown_tools",
                    level="WARNING",
                    unknown_tools=unknown,
                    intent_id=current.get("intent_id"),
                )
                fb = _fallback_decision_from_repair(
                    clause=str(current.get("description") or user_query_text(state)),
                    scoped_tools=scoped,
                    current_intent=current,
                )
                decision = fb or PlannerDecision(
                    intent_id=str(current.get("intent_id")),
                    kind="request_clarification",
                    tool_calls=[],
                    decision_summary=f"Planner proposed unsupported tools: {unknown}.",
                    risk_level="read",
                )

        next_route: RouteKey = "decision_guard"
        extra: dict[str, Any] = {}
        pending_payload: dict[str, Any] | None = decision.model_dump(mode="json")

        if decision.kind == "request_clarification":
            q = None
            if decision.control_action and isinstance(decision.control_action.payload, dict):
                q = decision.control_action.payload.get("question")
            if not isinstance(q, str) or not q.strip():
                q = decision.decision_summary
            extra["clarification"] = q.strip()
            extra["status"] = "awaiting_clarification"
            next_route = "clarify_end"
            pending_payload = None
        elif decision.kind == "intent_completed":
            current["status"] = "completed"
            working[cursor] = current
            later = _next_active_intent_index(working, cursor + 1)
            if later is not None:
                extra["intent_cursor"] = later
                next_route = "continue_planner"
            else:
                next_route = "synthesize_plan"
                extra["status"] = "validating"
        elif decision.kind == "intent_failed":
            reason = decision.decision_summary
            current["status"] = "failed"
            current["failure_reason"] = reason
            working[cursor] = current
            failed_id = str(current.get("intent_id"))
            _cascade_cancel_dependents(working, failed_id, reason=reason)
            nxt2 = _next_active_intent_index(working, 0)
            if nxt2 is not None:
                extra["intent_cursor"] = nxt2
                next_route = "continue_planner"
            else:
                next_route = "synthesize_plan"
                extra["status"] = "validating"
        elif decision.kind == "halt":
            next_route = "synthesize_plan"
            extra["status"] = "validating"
        elif decision.kind in ("domain_tool", "parallel_read_tools", "request_approval"):
            next_route = "decision_guard"
        else:
            next_route = "decision_guard"

        prev_decisions = list(state.get("decisions") or [])
        planner_trace = [
            {
                "phase": "planner",
                "intent_id": decision.intent_id,
                "kind": decision.kind,
                "summary": decision.decision_summary,
                "iteration": iteration,
            }
        ]

        new_cursor = int(extra.get("intent_cursor", cursor))
        if working and 0 <= new_cursor < len(working):
            cur_obj: dict[str, Any] | None = working[new_cursor]
        else:
            cur_obj = working[cursor] if working and 0 <= cursor < len(working) else None

        out: dict[str, Any] = {
            "planner_iteration": iteration,
            "working_intents": working,
            "intent_cursor": new_cursor,
            "current_intent": cur_obj,
            "pending_decision": pending_payload,
            "decisions": prev_decisions + [decision.model_dump(mode="json")],
            "completed_actions": planner_trace,
            "next_route": next_route,
            "status": extra.get("status", "planning"),
        }
        out.update({k: v for k, v in extra.items() if k != "intent_cursor"})
        return out

    return planner_node


def decision_guard_node(state: AgentState) -> dict[str, Any]:
    pending = state.get("pending_decision")
    if not isinstance(pending, dict):
        return {"next_route": "continue_planner"}
    scoped = state.get("scoped_tools") or []
    tools_by_name = {t.name: t for t in scoped if getattr(t, "name", None)}
    current = state.get("current_intent")
    constraints: list[dict[str, Any]] = []
    if isinstance(current, dict):
        constraints = [c for c in (current.get("explicit_constraints") or []) if isinstance(c, dict)]

    raw_calls = pending.get("tool_calls") or []
    if not isinstance(raw_calls, list):
        raw_calls = []
    fixed_calls: list[dict[str, Any]] = [dict(x) for x in raw_calls if isinstance(x, dict)]
    _assign_missing_output_refs(fixed_calls, tools_by_name)
    ref_err = _forward_ref_violation(fixed_calls, tools_by_name)
    if ref_err:
        pending2 = dict(pending)
        pending2["violates_constraints"] = True
        pending2["tool_calls"] = []
        pending2["decision_summary"] = (
            str(pending2.get("decision_summary") or "") + f" [guard: invalid transaction refs: {ref_err}]"
        ).strip()
        log_event(
            "decision_guard_blocked",
            level="WARNING",
            intent_id=pending2.get("intent_id"),
            detail=ref_err,
        )
        return {
            "pending_decision": pending2,
            "next_route": "continue_planner",
            "failed_strategies": [
                {
                    "phase": "decision_guard",
                    "intent_id": pending2.get("intent_id"),
                    "reason": "transaction_ref_violation",
                    "detail": ref_err,
                    "repair_instruction": "Revise the decision without forward, missing, duplicate, or self references.",
                }
            ],
            "completed_actions": [
                {
                    "phase": "decision_guard",
                    "intent_id": pending2.get("intent_id"),
                    "kind": "transaction_ref_violation",
                    "summary": ref_err,
                }
            ],
        }

    pending = dict(pending)
    pending["tool_calls"] = fixed_calls

    if constraints and fixed_calls and _constraints_violated(constraints=constraints, tool_calls=fixed_calls):
        pending["violates_constraints"] = True
        pending["tool_calls"] = []
        pending["decision_summary"] = (
            str(pending.get("decision_summary") or "")
            + " [guard: proposed args violated explicit user constraints; skipped tool execution]"
        ).strip()
        log_event(
            "decision_guard_blocked",
            level="WARNING",
            intent_id=pending.get("intent_id"),
            constraints=constraints,
        )
        return {
            "pending_decision": pending,
            "next_route": "continue_planner",
            "failed_strategies": [
                {
                    "phase": "decision_guard",
                    "intent_id": pending.get("intent_id"),
                    "reason": "constraint_violation",
                    "constraints": constraints,
                    "repair_instruction": "Revise tool args so every hard explicit user constraint is preserved.",
                }
            ],
            "completed_actions": [
                {
                    "phase": "decision_guard",
                    "intent_id": pending.get("intent_id"),
                    "kind": "constraint_violation",
                    "summary": "Skipped tool execution; routing to planner for repair.",
                }
            ],
        }
    return {"pending_decision": pending, "next_route": "tool_execution"}


def synthesize_plan_node(state: AgentState) -> dict[str, Any]:
    """Build a structured plan blueprint from the graph execution trace."""
    scoped = state.get("scoped_tools") or []
    tools_by_name = {t.name: t for t in scoped if getattr(t, "name", None)}
    steps: list[AgentPlanStep] = []
    for entry in state.get("completed_actions") or []:
        if not isinstance(entry, dict):
            continue
        if entry.get("phase") != "tool_execution":
            continue
        name = entry.get("tool_name")
        if not isinstance(name, str) or name not in tools_by_name:
            continue
        args = entry.get("args") if isinstance(entry.get("args"), dict) else {}
        steps.append(
            AgentPlanStep(
                tool_name=name,
                args=dict(args),
                evidence={},
                confidence=0.85,
                missing_required=[],
                depends_on=[len(steps) - 1] if steps else [],
            )
        )

    if not steps:
        rep = _deterministic_plan_repair(user_query_text(state), scoped, context=state.get("context") or {})
        if rep is not None:
            return {"plan_blueprint": rep, "risk_summary": rep.risk_summary, "status": "planning"}

        return {
            "plan_blueprint": AgentPlanOutput(
                plan_explanation=f"No tool steps recorded; cannot map request: {user_query_text(state)}",
                risk_summary="Empty planner trace.",
                steps=[],
                clarification="I could not derive executable tool steps from the planner loop.",
            ),
            "status": "awaiting_clarification",
        }

    expl_parts = [str(s.get("summary", "")) for s in (state.get("completed_actions") or []) if isinstance(s, dict) and s.get("phase") == "planner"]
    plan_explanation = " ".join(expl_parts).strip() or f"Planned tool sequence for: {user_query_text(state)}"
    risk = state.get("risk_summary") or "Review tool calls before execution."
    return {
        "plan_blueprint": AgentPlanOutput(
            plan_explanation=plan_explanation,
            risk_summary=str(risk),
            steps=steps,
            clarification=None,
        ),
        "status": "planning",
    }


def clarify_end_node(state: AgentState) -> dict[str, Any]:
    return {"status": "awaiting_clarification", "next_route": "clarify_end"}


def route_after_planner(state: AgentState) -> str:
    r = state.get("next_route")
    if r in ("clarify_end", "continue_planner", "decision_guard", "synthesize_plan"):
        return str(r)
    return "decision_guard"


def route_after_guard(state: AgentState) -> str:
    r = state.get("next_route")
    if r == "continue_planner":
        return "continue_planner"
    if r == "tool_execution":
        return "tool_execution"
    return "tool_execution"
