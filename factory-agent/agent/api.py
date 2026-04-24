from __future__ import annotations

import contextlib
from datetime import datetime
import time
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import HTMLResponse, PlainTextResponse
from jsonschema import Draft202012Validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Approval as ApprovalRow
from models import DeadLetter as DeadLetterRow
from models import Message as MessageRow
from models import Plan as PlanRow
from models import PlanStep as PlanStepRow
from models import Session as SessionRow
from models import generate_uuid

from .config import Settings
from .events import AgentEvent, EventBus
from .execution import ExecutionEngine, compute_idempotency_key
from .metrics import metrics
from .planner import PlannerAdapter, PlannerBackendError, PlannerClarificationError
from .plan_validator import validate_plan
from .schemas import (
    ApprovalDecisionRequest,
    ApprovalResponse,
    DeadLetterDismissRequest,
    DeadLetterPushRequest,
    DeadLetterReplayRequest,
    DeadLetterResponse,
    MessageCreateRequest,
    MessageResponse,
    PlanStepResponse,
    PlanCreateRequest,
    PlanResponse,
    SessionCreateRequest,
    SessionSnapshotResponse,
    SessionResponse,
    SessionUpdateRequest,
    TimelineEventResponse,
    ToolInfo,
    ValidationErrorResponse,
)
from .session_manager import SessionManager, TransitionError, VersionConflictError
from .security import JwtValidationError, validate_bearer_token
from .summary_backend import SummaryAdapter, SummaryBackendError
from .telemetry import log_event, log_step_status_changed
from .tool_registry import ToolRegistry
from .tool_scope import filter_tools_for_intent


def _normalize_session_name(name: str | None) -> str | None:
    normalized = (name or "").strip()
    return normalized or None


def _session_to_response(s: SessionRow) -> SessionResponse:
    return SessionResponse(
        session_id=s.session_id,
        user_id=s.user_id,
        name=_normalize_session_name(getattr(s, "name", None)),
        status=s.status,
        current_intent=s.current_intent,
        plan_id=s.plan_id,
        plan_version=s.plan_version or 0,
        plan_hash=s.plan_hash,
        current_step_index=s.current_step_index or 0,
        step_count=s.step_count or 0,
        replan_count=s.replan_count or 0,
        llm_call_count=s.llm_call_count or 0,
        session_started_at=s.session_started_at,
        replan_context=s.replan_context,
        pending_user_message=s.pending_user_message,
        created_at=s.created_at,
        updated_at=s.updated_at,
        completed_at=s.completed_at,
        error=s.error,
    )


def _plan_to_response(plan: PlanRow) -> PlanResponse:
    return PlanResponse(
        plan_id=plan.plan_id,
        session_id=plan.session_id,
        version=plan.version,
        dependency_graph=plan.dependency_graph,
        parallel_groups=plan.parallel_groups,
        plan_hash=plan.plan_hash,
        plan_explanation=plan.plan_explanation,
        risk_summary=plan.risk_summary,
        created_at=plan.created_at,
        created_by=plan.created_by,
    )


def _message_to_response(m: MessageRow) -> MessageResponse:
    return MessageResponse(
        message_id=m.message_id,
        session_id=m.session_id,
        role=m.role,
        content=m.content,
        created_at=m.created_at,
        step_id=m.step_id,
        tool_name=m.tool_name,
    )


def _approval_to_response(a: ApprovalRow) -> ApprovalResponse:
    return ApprovalResponse(
        approval_id=a.approval_id,
        session_id=a.session_id,
        step_id=a.step_id,
        tool_name=a.tool_name,
        args=a.args,
        risk_summary=a.risk_summary,
        side_effect_level=a.side_effect_level,
        status=a.status,
        expires_at=a.expires_at,
        decided_by=a.decided_by,
        decided_at=a.decided_at,
        rejection_reason=a.rejection_reason,
        created_at=a.created_at,
    )


def _step_to_response(s: PlanStepRow) -> PlanStepResponse:
    return PlanStepResponse(
        step_id=s.step_id,
        plan_id=s.plan_id,
        session_id=s.session_id,
        step_index=s.step_index,
        tool_name=s.tool_name,
        args=s.args or {},
        status=s.status,
        idempotency_key=s.idempotency_key,
        requires_approval=bool(s.requires_approval),
        approval_id=s.approval_id,
        retry_count=s.retry_count or 0,
        max_retries=s.max_retries or 0,
        last_error=s.last_error,
        result=s.result,
        result_summary=s.result_summary,
        started_at=s.started_at,
        completed_at=s.completed_at,
    )


def _timeline_event(
    *,
    event_id: str,
    event_type: str,
    content: str,
    created_at: datetime,
    role: str = "assistant",
    turn_id: str | None = None,
    step_context: dict[str, Any] | None = None,
    step_id: str | None = None,
    approval_id: str | None = None,
    tool_name: str | None = None,
    status: str | None = None,
    details: dict[str, Any] | None = None,
) -> TimelineEventResponse:
    return TimelineEventResponse(
        event_id=event_id,
        event_type=event_type,  # type: ignore[arg-type]
        content=content,
        created_at=created_at,
        role=role,  # type: ignore[arg-type]
        turn_id=turn_id,
        step_context=step_context,
        step_id=step_id,
        approval_id=approval_id,
        tool_name=tool_name,
        status=status,
        details=details,
    )


_TIMELINE_EVENT_PRIORITY = {
    "user_message": 0,
    "plan_created": 1,
    "execution_started": 2,
    "tool_started": 3,
    "approval_required": 3,
    "tool_result": 4,
    "approval_decided": 5,
    "replan_requested": 6,
    "session_blocked": 7,
    "session_failed": 8,
    "session_completed": 9,
}


def build_router(
    *,
    settings: Settings,
    tool_registry: ToolRegistry,
    event_bus: EventBus,
    enqueue_session: Any | None = None,
    planner_adapter: PlannerAdapter | None = None,
) -> APIRouter:
    router = APIRouter()
    session_mgr = SessionManager(settings)
    executor = ExecutionEngine(settings, event_bus)
    planner = planner_adapter or PlannerAdapter(settings=settings, tool_registry=tool_registry)
    summary_adapter = SummaryAdapter(settings)

    def _session_duration_s(sess: SessionRow) -> int:
        if not sess.session_started_at:
            return 0
        return int((datetime.utcnow() - sess.session_started_at).total_seconds())

    def _log_step_status(sess: SessionRow, step: PlanStepRow, status: str) -> None:
        log_step_status_changed(
            session_id=sess.session_id,
            plan_id=sess.plan_id,
            plan_version=sess.plan_version,
            step_id=step.step_id,
            step_index=step.step_index,
            tool=step.tool_name,
            status=status,
            idempotency_key=step.idempotency_key,
            required_approval=bool(step.requires_approval),
            session_step_count=sess.step_count,
            session_llm_call_count=sess.llm_call_count,
            session_replan_count=sess.replan_count,
            session_duration_s=_session_duration_s(sess),
            user_id=sess.user_id,
        )

    def require_admin(x_admin_key: str = Header(..., alias="X-Admin-Key")) -> None:
        if x_admin_key != settings.admin_api_key:
            raise HTTPException(status_code=403, detail="forbidden")

    def require_jwt(authorization: str | None = Header(None, alias="Authorization")) -> dict[str, Any]:
        try:
            return validate_bearer_token(authorization, settings=settings)
        except JwtValidationError as e:
            raise HTTPException(status_code=401, detail=str(e))

    async def load_session_snapshot(*, db: AsyncSession, session_id: str) -> SessionSnapshotResponse | None:
        sess = await session_mgr.get_session(db, session_id=session_id)
        if not sess:
            return None
        tools_by_name = await tool_registry.get_tools_by_name(db)

        current_plan = None
        if sess.plan_id:
            current_plan = (
                await db.execute(select(PlanRow).where(PlanRow.plan_id == sess.plan_id))
            ).scalars().first()

        plan_rows = (
            await db.execute(
                select(PlanRow)
                .where(PlanRow.session_id == session_id)
                .order_by(PlanRow.created_at.asc())
            )
        ).scalars().all()
        step_rows = (
            await db.execute(
                select(PlanStepRow)
                .where(PlanStepRow.session_id == session_id)
                .order_by(PlanStepRow.step_index.asc())
            )
        ).scalars().all()
        message_rows = (
            await db.execute(
                select(MessageRow)
                .where(MessageRow.session_id == session_id)
                .order_by(MessageRow.created_at.asc())
            )
        ).scalars().all()
        approval_rows = (
            await db.execute(
                select(ApprovalRow)
                .where(ApprovalRow.session_id == session_id)
                .order_by(ApprovalRow.created_at.asc())
            )
        ).scalars().all()

        pending_approval = next((row for row in reversed(approval_rows) if row.status == "PENDING"), None)
        tool_result_messages = [row for row in message_rows if row.role == "tool_result"]
        user_messages = [row for row in message_rows if row.role == "user"]
        assistant_messages = [row for row in message_rows if row.role == "assistant"]
        plan_messages = [row for row in assistant_messages if row.tool_name == "__plan__"]

        user_messages_sorted = sorted(user_messages, key=lambda m: m.created_at)

        def _turn_id_for_time(ts: datetime | None) -> str | None:
            if not user_messages_sorted:
                return None
            if ts is None:
                return user_messages_sorted[-1].message_id
            selected = None
            for msg in user_messages_sorted:
                if msg.created_at <= ts:
                    selected = msg
                else:
                    break
            return (selected or user_messages_sorted[-1]).message_id

        def _session_ctx() -> dict[str, Any]:
            return {
                "session_id": sess.session_id,
                "status": sess.status,
                "plan_version": sess.plan_version or 0,
                "current_step_index": sess.current_step_index or 0,
            }

        def _missing_required_fields(tool_name: str | None, args: dict[str, Any] | None) -> list[str]:
            if not tool_name:
                return []
            tool = tools_by_name.get(tool_name)
            schema = tool.input_schema if tool else {}
            required = schema.get("required") if isinstance(schema, dict) else None
            if not isinstance(required, list):
                return []
            payload = args if isinstance(args, dict) else {}
            missing: list[str] = []
            for key in required:
                if not isinstance(key, str) or not key:
                    continue
                if key not in payload or payload.get(key) is None or payload.get(key) == "":
                    missing.append(key)
            return missing

        events: list[TimelineEventResponse] = []
        for msg in user_messages:
            events.append(
                _timeline_event(
                    event_id=f"user:{msg.message_id}",
                    event_type="user_message",
                    content=msg.content,
                    created_at=msg.created_at,
                    role="user",
                    turn_id=msg.message_id,
                    step_context={**_session_ctx(), "message_id": msg.message_id},
                )
            )

        for idx, plan_row in enumerate(plan_rows):
            plan_message = plan_messages[idx] if idx < len(plan_messages) else None
            content = (
                plan_message.content
                if plan_message and plan_message.content
                else (plan_row.plan_explanation or "Execution plan created.")
            )
            events.append(
                _timeline_event(
                    event_id=f"plan:{plan_row.plan_id}",
                    event_type="plan_created",
                    content=content,
                    created_at=plan_row.created_at,
                    status="PLANNING",
                    turn_id=_turn_id_for_time(plan_row.created_at),
                    step_context={**_session_ctx(), "plan_id": plan_row.plan_id, "plan_version": plan_row.version},
                    details={
                        "plan_id": plan_row.plan_id,
                        "version": plan_row.version,
                        "plan_explanation": plan_row.plan_explanation,
                        "risk_summary": plan_row.risk_summary,
                    },
                )
            )
            if plan_row.invalidated_at:
                reason = plan_row.invalidated_reason or "replan requested"
                events.append(
                    _timeline_event(
                        event_id=f"replan:{plan_row.plan_id}",
                        event_type="replan_requested",
                        content=f"Replan requested: {reason}.",
                        created_at=plan_row.invalidated_at,
                        status="PLANNING",
                        turn_id=_turn_id_for_time(plan_row.invalidated_at),
                        step_context={**_session_ctx(), "plan_id": plan_row.plan_id, "plan_version": plan_row.version},
                        details={"plan_id": plan_row.plan_id, "reason": reason},
                    )
                )

        execution_started_at = min((step.started_at for step in step_rows if step.started_at), default=None)
        if execution_started_at:
            events.append(
                _timeline_event(
                    event_id=f"exec:{session_id}",
                    event_type="execution_started",
                    content="Execution started.",
                    created_at=execution_started_at,
                    status="EXECUTING",
                    turn_id=_turn_id_for_time(execution_started_at),
                    step_context=_session_ctx(),
                )
            )

        tool_messages_by_step = {msg.step_id: msg for msg in tool_result_messages if msg.step_id}
        for step in step_rows:
            if step.status == "IN_PROGRESS" and step.started_at:
                events.append(
                    _timeline_event(
                        event_id=f"step-started:{step.step_id}",
                        event_type="tool_started",
                        content="Step started.",
                        created_at=step.started_at,
                        turn_id=_turn_id_for_time(step.started_at),
                        step_context={
                            **_session_ctx(),
                            "step_id": step.step_id,
                            "step_index": step.step_index,
                            "tool_name": step.tool_name,
                            "approval_id": step.approval_id,
                        },
                        step_id=step.step_id,
                        tool_name=step.tool_name,
                        status=step.status,
                        details={"args": step.args},
                    )
                )
                continue

            if step.step_id in tool_messages_by_step:
                msg = tool_messages_by_step[step.step_id]
                created_at = msg.created_at
                content = msg.content
            elif step.status in ("DONE", "FAILED", "AMBIGUOUS") and (step.completed_at or step.started_at):
                created_at = step.completed_at or step.started_at
                content = (
                    step.result_summary
                    or (f"{step.tool_name} failed: {step.last_error}" if step.status == "FAILED" else f"{step.tool_name} completed.")
                )
            else:
                continue

            events.append(
                _timeline_event(
                    event_id=f"step:{step.step_id}",
                    event_type="tool_result",
                    content=content,
                    created_at=created_at,
                    turn_id=_turn_id_for_time(created_at),
                    step_context={
                        **_session_ctx(),
                        "step_id": step.step_id,
                        "step_index": step.step_index,
                        "tool_name": step.tool_name,
                        "approval_id": step.approval_id,
                    },
                    step_id=step.step_id,
                    tool_name=step.tool_name,
                    status=step.status,
                    details={"args": step.args, "result": step.result, "last_error": step.last_error},
                )
            )

        for approval in approval_rows:
            tool = tools_by_name.get(approval.tool_name)
            missing_required = _missing_required_fields(approval.tool_name, approval.args)
            tool_schema = tool.input_schema if tool else None
            events.append(
                _timeline_event(
                    event_id=f"approval-required:{approval.approval_id}",
                    event_type="approval_required",
                    content=(
                        "Waiting for your approval."
                        if not approval.risk_summary
                        else f"Waiting for your approval: {approval.risk_summary}"
                    ),
                    created_at=approval.created_at,
                    turn_id=_turn_id_for_time(approval.created_at),
                    step_context={
                        **_session_ctx(),
                        "approval_id": approval.approval_id,
                        "step_id": approval.step_id,
                        "tool_name": approval.tool_name,
                    },
                    approval_id=approval.approval_id,
                    step_id=approval.step_id,
                    tool_name=approval.tool_name,
                    status=approval.status,
                    details={
                        "args": approval.args,
                        "side_effect_level": approval.side_effect_level,
                        "expires_at": approval.expires_at.isoformat(),
                        "tool": {
                            "name": tool.name if tool else approval.tool_name,
                            "description": tool.description if tool else None,
                            "method": tool.method if tool else None,
                            "endpoint": tool.endpoint if tool else None,
                        },
                        "input_schema": tool_schema,
                        "missing_required": missing_required,
                    },
                )
            )
            if approval.decided_at:
                decision_text = "approved" if approval.status == "APPROVED" else "rejected"
                reason = approval.rejection_reason
                content = (
                    f"{approval.tool_name} {decision_text}."
                    if not reason
                    else f"{approval.tool_name} {decision_text}: {reason}"
                )
                events.append(
                    _timeline_event(
                        event_id=f"approval-decided:{approval.approval_id}",
                        event_type="approval_decided",
                        content=content,
                        created_at=approval.decided_at,
                        turn_id=_turn_id_for_time(approval.decided_at),
                        step_context={
                            **_session_ctx(),
                            "approval_id": approval.approval_id,
                            "step_id": approval.step_id,
                            "tool_name": approval.tool_name,
                        },
                        approval_id=approval.approval_id,
                        step_id=approval.step_id,
                        tool_name=approval.tool_name,
                        status=approval.status,
                        details={"decided_by": approval.decided_by, "rejection_reason": approval.rejection_reason},
                    )
                )

        ambiguous_step = next((step for step in step_rows if step.status == "AMBIGUOUS" and (step.completed_at or step.started_at)), None)
        if sess.status == "BLOCKED":
            blocked_at = (ambiguous_step.completed_at if ambiguous_step and ambiguous_step.completed_at else sess.updated_at)
            events.append(
                _timeline_event(
                    event_id=f"blocked:{session_id}",
                    event_type="session_blocked",
                    content=sess.error or "Execution blocked.",
                    created_at=blocked_at,
                    status=sess.status,
                    turn_id=_turn_id_for_time(blocked_at),
                    step_context=_session_ctx(),
                )
            )
        if sess.status == "FAILED":
            events.append(
                _timeline_event(
                    event_id=f"failed:{session_id}",
                    event_type="session_failed",
                    content=sess.error or "Session failed.",
                    created_at=sess.updated_at,
                    status=sess.status,
                    turn_id=_turn_id_for_time(sess.updated_at),
                    step_context=_session_ctx(),
                )
            )
        if sess.completed_at:
            completion_message = next((msg for msg in reversed(assistant_messages) if "Execution completed successfully" in msg.content), None)
            events.append(
                _timeline_event(
                    event_id=f"completed:{session_id}",
                    event_type="session_completed",
                    content=(
                        completion_message.content
                        if completion_message and completion_message.content
                        else "Execution completed successfully."
                    ),
                    created_at=sess.completed_at,
                    status="COMPLETED",
                    turn_id=_turn_id_for_time(sess.completed_at),
                    step_context=_session_ctx(),
                )
            )

        events.sort(
            key=lambda event: (
                event.created_at,
                _TIMELINE_EVENT_PRIORITY.get(event.event_type, 99),
                event.event_id,
            )
        )
        return SessionSnapshotResponse(
            session=_session_to_response(sess),
            plan=_plan_to_response(current_plan) if current_plan else None,
            steps=[_step_to_response(step) for step in step_rows],
            pending_approval=_approval_to_response(pending_approval) if pending_approval else None,
            timeline=events,
        )

    @router.post("/sessions", response_model=SessionResponse)
    async def create_session(
        req: SessionCreateRequest,
        _: dict[str, Any] = Depends(require_jwt),
        db: AsyncSession = Depends(get_db),
    ):
        sess = await session_mgr.create_session(
            db,
            user_id=req.user_id,
            name=_normalize_session_name(req.name) or "New chat",
        )
        return _session_to_response(sess)

    @router.get("/sessions", response_model=list[SessionResponse])
    async def list_sessions(
        user_id: str | None = Query(None),
        _: dict[str, Any] = Depends(require_jwt),
        db: AsyncSession = Depends(get_db),
    ):
        stmt = select(SessionRow).order_by(SessionRow.updated_at.desc())
        if user_id:
            stmt = stmt.where(SessionRow.user_id == user_id)
        rows = (await db.execute(stmt)).scalars().all()
        return [_session_to_response(row) for row in rows]

    @router.get("/sessions/{session_id}", response_model=SessionResponse)
    async def get_session(
        session_id: str,
        _: dict[str, Any] = Depends(require_jwt),
        db: AsyncSession = Depends(get_db),
    ):
        sess = await session_mgr.get_session(db, session_id=session_id)
        if not sess:
            raise HTTPException(status_code=404, detail="session not found")
        return _session_to_response(sess)

    @router.patch("/sessions/{session_id}", response_model=SessionResponse)
    async def update_session(
        session_id: str,
        req: SessionUpdateRequest,
        _: dict[str, Any] = Depends(require_jwt),
        db: AsyncSession = Depends(get_db),
    ):
        sess = await session_mgr.get_session(db, session_id=session_id)
        if not sess:
            raise HTTPException(status_code=404, detail="session not found")
        sess.name = _normalize_session_name(req.name)
        sess.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(sess)
        return _session_to_response(sess)

    @router.get("/sessions/{session_id}/snapshot", response_model=SessionSnapshotResponse)
    async def get_session_snapshot(
        session_id: str,
        _: dict[str, Any] = Depends(require_jwt),
        db: AsyncSession = Depends(get_db),
    ):
        snapshot = await load_session_snapshot(db=db, session_id=session_id)
        if not snapshot:
            raise HTTPException(status_code=404, detail="session not found")
        return snapshot

    @router.get("/tools", response_model=list[ToolInfo])
    async def list_tools(
        intent: str | None = Query(None, description="Optional user intent to scope tools."),
        max_tools: int = Query(30, ge=1, le=200, description="Maximum tools returned."),
        db: AsyncSession = Depends(get_db),
    ):
        tools_by_name = await tool_registry.get_tools_by_name(db)
        if intent:
            scoped = filter_tools_for_intent(intent=intent, tools_by_name=tools_by_name, max_tools=max_tools)
            return [tools_by_name[name] for name in scoped.tool_names if name in tools_by_name]
        names = sorted(tools_by_name.keys())[:max_tools]
        return [tools_by_name[name] for name in names]

    @router.post("/sessions/{session_id}/messages", response_model=MessageResponse)
    async def add_message(
        session_id: str,
        req: MessageCreateRequest,
        _: dict[str, Any] = Depends(require_jwt),
        db: AsyncSession = Depends(get_db),
    ):
        sess = await session_mgr.get_session(db, session_id=session_id)
        if not sess:
            raise HTTPException(status_code=404, detail="session not found")
        msg = await session_mgr.add_message(db, session_id=session_id, role=req.role, content=req.content)
        if req.role == "user":
            sess.current_intent = req.content[:5000]
            lowered = req.content.strip().lower()
            if any(token in lowered for token in ("stop", "cancel", "don't do this", "do not do this")):
                step_rows = (
                    await db.execute(
                        select(PlanStepRow)
                        .where(PlanStepRow.session_id == session_id)
                        .order_by(PlanStepRow.step_index.asc())
                    )
                ).scalars().all()
                for step in step_rows:
                    if step.status == "DONE":
                        continue
                    if step.status not in ("SKIPPED", "FAILED", "AMBIGUOUS"):
                        step.status = "SKIPPED"
                        step.completed_at = step.completed_at or datetime.utcnow()
                        step.last_error = step.last_error or "Cancelled by user message"
                        _log_step_status(sess, step, step.status)
                sess.status = "IDLE"
                sess.error = "Cancelled by user message"
                sess.pending_user_message = None
                sess.version += 1
                await event_bus.publish(
                    AgentEvent(
                        event_type="session_cancel",
                        session_id=session_id,
                        payload={},
                        published_at=datetime.utcnow(),
                    )
                )
            elif sess.status == "WAITING_APPROVAL":
                current_plan = (
                    await db.execute(select(PlanRow).where(PlanRow.plan_id == sess.plan_id))
                ).scalars().first()
                steps = (
                    await db.execute(
                        select(PlanStepRow)
                        .where(PlanStepRow.plan_id == sess.plan_id)
                        .order_by(PlanStepRow.step_index.asc())
                    )
                ).scalars().all()
                if current_plan and not current_plan.invalidated_at:
                    current_plan.invalidated_at = datetime.utcnow()
                    current_plan.invalidated_reason = "mid_execution_user_message"
                completed_steps = [
                    {"step_index": s.step_index, "tool_name": s.tool_name, "args": s.args, "result": s.result}
                    for s in steps
                    if s.status == "DONE"
                ]
                sess.replan_count += 1
                sess.plan_version = (sess.plan_version or 0) + 1
                sess.replan_context = {
                    "original_intent": sess.current_intent,
                    "plan_id": sess.plan_id,
                    "plan_version": sess.plan_version,
                    "completed_steps": completed_steps,
                    "error": "mid_execution_user_message",
                    "user_message": req.content,
                }
                sess.status = "PLANNING"
                sess.error = "Replan requested from user message"
                sess.pending_user_message = None
                sess.version += 1
            elif sess.status == "EXECUTING":
                sess.pending_user_message = req.content[:5000]
                sess.version += 1
            await db.commit()
        return _message_to_response(msg)

    @router.get("/sessions/{session_id}/messages", response_model=list[MessageResponse])
    async def list_messages(
        session_id: str,
        _: dict[str, Any] = Depends(require_jwt),
        db: AsyncSession = Depends(get_db),
    ):
        sess = await session_mgr.get_session(db, session_id=session_id)
        if not sess:
            raise HTTPException(status_code=404, detail="session not found")
        rows = (
            await db.execute(
                select(MessageRow)
                .where(MessageRow.session_id == session_id)
                .order_by(MessageRow.created_at.asc())
            )
        ).scalars().all()
        return [_message_to_response(r) for r in rows]

    @router.get("/sessions/{session_id}/steps", response_model=list[PlanStepResponse])
    async def list_steps(
        session_id: str,
        _: dict[str, Any] = Depends(require_jwt),
        db: AsyncSession = Depends(get_db),
    ):
        sess = await session_mgr.get_session(db, session_id=session_id)
        if not sess:
            raise HTTPException(status_code=404, detail="session not found")
        rows = (
            await db.execute(
                select(PlanStepRow)
                .where(PlanStepRow.session_id == session_id)
                .order_by(PlanStepRow.step_index.asc())
            )
        ).scalars().all()
        return [_step_to_response(r) for r in rows]

    @router.post(
        "/sessions/{session_id}/plans",
        response_model=PlanResponse,
        responses={400: {"model": ValidationErrorResponse}},
    )
    async def create_plan(
        session_id: str,
        req: PlanCreateRequest,
        _: dict[str, Any] = Depends(require_jwt),
        db: AsyncSession = Depends(get_db),
    ):
        started = time.perf_counter()
        sess = await session_mgr.get_session(db, session_id=session_id)
        if not sess:
            raise HTTPException(status_code=404, detail="session not found")

        tools_by_name = await tool_registry.get_tools_by_name(db)
        intent = sess.current_intent or ""
        scoped = filter_tools_for_intent(intent=intent, tools_by_name=tools_by_name)
        backend_used = "legacy" if req.draft is None else "client"
        draft = req.draft

        if draft is None:
            if not intent.strip():
                raise HTTPException(status_code=400, detail={"errors": ["Cannot auto-generate plan without a current intent."]})
            scoped_tools = [tools_by_name[name] for name in scoped.tool_names if name in tools_by_name]
            try:
                generated = await planner.generate_plan(
                    intent=intent,
                    scoped_tools=scoped_tools,
                    context=sess.replan_context,
                )
            except PlannerClarificationError as e:
                raise HTTPException(status_code=400, detail={"errors": [str(e)]}) from e
            except PlannerBackendError as e:
                raise HTTPException(status_code=503, detail={"errors": [str(e)]}) from e
            draft = generated.draft
            backend_used = generated.backend_used
            sess.llm_call_count += generated.llm_calls
            sess.version += 1
            await db.commit()
            metrics.inc("plan_backend_used_total", labels={"backend_used": backend_used})
            log_event(
                "planner_generation_succeeded",
                session_id=session_id,
                backend_used=backend_used,
                llm_calls=generated.llm_calls,
                scoped_tool_count=len(scoped_tools),
            )

        # Validate plan against full registry (schema correctness), but ensure steps use only scoped tools.
        invalid_scoped = [s.tool_name for s in draft.steps if s.tool_name not in scoped.tool_names]
        if invalid_scoped:
            raise HTTPException(status_code=400, detail={"errors": [f"Tool not allowed by scope: {t}" for t in invalid_scoped]})

        validation = validate_plan(draft, tools_by_name, max_steps=settings.max_plan_steps)
        if not validation.ok:
            if (
                req.draft is None
                and backend_used == "langchain"
                and settings.planner_fallback_to_legacy
            ):
                scoped_tools = [tools_by_name[name] for name in scoped.tool_names if name in tools_by_name]
                fallback = await planner.generate_plan(
                    intent=intent,
                    scoped_tools=scoped_tools,
                    context=sess.replan_context,
                    force_backend="legacy",
                )
                draft = fallback.draft
                backend_used = fallback.backend_used
                validation = validate_plan(draft, tools_by_name, max_steps=settings.max_plan_steps)
                metrics.inc("plan_backend_used_total", labels={"backend_used": "legacy_fallback"})
                log_event("planner_fallback_used", session_id=session_id, fallback_backend="legacy")
            if validation.ok:
                pass
            else:
                metrics.inc("plan_validation_failure_total")
                metrics.inc("plan_validation_failure_rate")
                if sess.status == "PLANNING":
                    context = dict(sess.replan_context or {})
                    failures = int(context.get("validation_failure_count", 0)) + 1
                    context["validation_failure_count"] = failures
                    context["last_validation_errors"] = validation.errors
                    sess.replan_context = context
                    sess.error = "Plan validation failed"
                    sess.version += 1
                    if failures >= 3:
                        sess.status = "BLOCKED"
                        dlq = DeadLetterRow(
                            dlq_id=generate_uuid(),
                            session_id=session_id,
                            step_id=None,
                            failure_type="replan_limit_reached",
                            reason="Plan validation failed 3 consecutive times",
                            payload={"errors": validation.errors, "validation_failure_count": failures},
                            status="PENDING",
                        )
                        db.add(dlq)
                    await db.commit()
                raise HTTPException(status_code=400, detail={"errors": validation.errors})

        # Invalidate existing plan if any
        if sess.plan_id:
            existing = (
                await db.execute(select(PlanRow).where(PlanRow.plan_id == sess.plan_id))
            ).scalars().first()
            if existing and not existing.invalidated_at:
                existing.invalidated_at = datetime.utcnow()
                existing.invalidated_reason = "Replanned"
                sess.replan_count += 1

        if sess.replan_context:
            plan_version = max(1, sess.plan_version or 1)
        else:
            plan_version = (sess.plan_version or 0) + 1
        plan_row = PlanRow(
            plan_id=generate_uuid(),
            session_id=session_id,
            version=plan_version,
            dependency_graph=validation.normalized_dependency_graph,
            parallel_groups=validation.normalized_parallel_groups,
            plan_hash=validation.plan_hash,
            plan_explanation=draft.plan_explanation,
            risk_summary=draft.risk_summary,
            created_at=datetime.utcnow(),
            created_by=backend_used,
        )
        db.add(plan_row)
        await db.commit()
        await db.refresh(plan_row)

        # Store steps
        for step in draft.steps:
            tool = tools_by_name.get(step.tool_name)
            step_row = PlanStepRow(
                step_id=generate_uuid(),
                plan_id=plan_row.plan_id,
                session_id=session_id,
                step_index=step.step_index,
                tool_name=step.tool_name,
                args=step.args,
                status="NOT_STARTED",
                idempotency_key=compute_idempotency_key(
                    session_id=session_id,
                    step_index=step.step_index,
                    plan_version=plan_version,
                    args=step.args,
                ),
                requires_approval=bool(tool.requires_approval) if tool else False,
                retry_count=0,
                max_retries=3,
            )
            db.add(step_row)
        await db.commit()

        # Attach plan to session
        sess.plan_id = plan_row.plan_id
        sess.plan_version = plan_version
        sess.plan_hash = plan_row.plan_hash
        sess.current_step_index = 0
        sess.status = "PLANNING"
        sess.replan_context = None
        sess.pending_user_message = None
        sess.error = None
        sess.version += 1
        if not sess.name:
            sess.name = "New chat"
        await db.commit()
        metrics.observe("plan_generation_latency_ms", (time.perf_counter() - started) * 1000.0)

        summary_text = draft.plan_explanation or "Execution plan created."
        try:
            summary = await summary_adapter.summarize_plan(intent=intent, draft=draft)
            summary_text = summary.text
            sess.llm_call_count += summary.llm_calls
            sess.version += 1
        except SummaryBackendError:
            pass
        db.add(
            MessageRow(
                message_id=generate_uuid(),
                session_id=session_id,
                role="assistant",
                content=summary_text,
                tool_name="__plan__",
            )
        )
        await db.commit()

        return _plan_to_response(plan_row)

    @router.post("/sessions/{session_id}/execute", response_model=SessionResponse)
    async def execute(
        session_id: str,
        background: bool = Query(False, description="If true, enqueue execution to the worker pool (when enabled)."),
        expected_version: int | None = Query(None, ge=1, description="Optional optimistic-lock expected session version."),
        _: dict[str, Any] = Depends(require_jwt),
        db: AsyncSession = Depends(get_db),
    ):
        sess = await session_mgr.get_session(db, session_id=session_id)
        if not sess:
            raise HTTPException(status_code=404, detail="session not found")
        if expected_version is not None and sess.version != expected_version:
            raise HTTPException(status_code=409, detail=f"version_conflict expected={expected_version} actual={sess.version}")
        try:
            session_mgr.enforce_limits(sess)
        except TransitionError as e:
            raise HTTPException(status_code=429, detail=str(e))
        # Background execution only works when the worker pool is enabled.
        if background and settings.worker_count <= 0:
            background = False

        if background and enqueue_session is not None:
            # Mark as executing and enqueue.
            try:
                sess = await session_mgr.update_with_version(
                    db,
                    session_id=sess.session_id,
                    expected_version=sess.version,
                    values={"status": "EXECUTING", "error": None},
                )
            except VersionConflictError as e:
                raise HTTPException(status_code=409, detail=str(e))
            try:
                await enqueue_session(session_id)
            except Exception as e:
                raise HTTPException(status_code=429, detail=f"queue full or enqueue failed: {e}")
            return _session_to_response(sess)

        tools_by_name = await tool_registry.get_tools_by_name(db)
        await executor.execute_until_blocked(db, session=sess, tools_by_name=tools_by_name)
        sess = await session_mgr.get_session(db, session_id=session_id)
        return _session_to_response(sess)

    @router.post("/sessions/{session_id}/cancel", response_model=SessionResponse)
    async def cancel_session(
        session_id: str,
        _: dict[str, Any] = Depends(require_jwt),
        db: AsyncSession = Depends(get_db),
    ):
        sess = await session_mgr.get_session(db, session_id=session_id)
        if not sess:
            raise HTTPException(status_code=404, detail="session not found")
        step_rows = (
            await db.execute(
                select(PlanStepRow)
                .where(PlanStepRow.session_id == session_id)
                .order_by(PlanStepRow.step_index.asc())
            )
        ).scalars().all()
        for step in step_rows:
            if step.status == "DONE":
                continue
            if step.status not in ("SKIPPED", "FAILED", "AMBIGUOUS"):
                step.status = "SKIPPED"
                step.completed_at = step.completed_at or datetime.utcnow()
                step.last_error = step.last_error or "Cancelled"
                _log_step_status(sess, step, step.status)
        sess.status = "IDLE"
        sess.error = "Cancelled"
        sess.updated_at = datetime.utcnow()
        await db.commit()
        await event_bus.publish(
            AgentEvent(
                event_type="session_cancel",
                session_id=session_id,
                payload={},
                published_at=datetime.utcnow(),
            )
        )
        sess = await session_mgr.get_session(db, session_id=session_id)
        return _session_to_response(sess)

    @router.get("/approvals/pending", response_model=list[ApprovalResponse])
    async def list_pending_approvals(
        session_id: str | None = Query(None),
        _: dict[str, Any] = Depends(require_jwt),
        db: AsyncSession = Depends(get_db),
    ):
        stmt = select(ApprovalRow).where(ApprovalRow.status == "PENDING")
        if session_id:
            stmt = stmt.where(ApprovalRow.session_id == session_id)
        rows = (
            await db.execute(stmt.order_by(ApprovalRow.created_at.asc()))
        ).scalars().all()
        return [_approval_to_response(r) for r in rows]

    @router.get("/approvals/{approval_id}", response_model=ApprovalResponse)
    async def get_approval(
        approval_id: str,
        _: dict[str, Any] = Depends(require_jwt),
        db: AsyncSession = Depends(get_db),
    ):
        row = (await db.execute(select(ApprovalRow).where(ApprovalRow.approval_id == approval_id))).scalars().first()
        if not row:
            raise HTTPException(status_code=404, detail="approval not found")
        return _approval_to_response(row)

    @router.post("/approvals/{approval_id}/approve", response_model=ApprovalResponse)
    async def approve_approval(
        approval_id: str,
        req: ApprovalDecisionRequest,
        _: dict[str, Any] = Depends(require_jwt),
        db: AsyncSession = Depends(get_db),
    ):
        row = (await db.execute(select(ApprovalRow).where(ApprovalRow.approval_id == approval_id))).scalars().first()
        if not row:
            raise HTTPException(status_code=404, detail="approval not found")

        if req.args is not None:
            if not isinstance(req.args, dict):
                raise HTTPException(status_code=400, detail="args must be an object")
            tools_by_name = await tool_registry.get_tools_by_name(db)
            tool = tools_by_name.get(row.tool_name)
            if not tool:
                raise HTTPException(status_code=400, detail=f"unknown tool: {row.tool_name}")
            try:
                Draft202012Validator(tool.input_schema).validate(req.args)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"invalid args: {e}")

            row.args = req.args
            step = (await db.execute(select(PlanStepRow).where(PlanStepRow.step_id == row.step_id))).scalars().first()
            if step:
                step.args = req.args
                sess = await session_mgr.get_session(db, session_id=row.session_id)
                plan_version = (sess.plan_version or 0) if sess else 0
                step.idempotency_key = compute_idempotency_key(
                    session_id=row.session_id,
                    step_index=step.step_index,
                    plan_version=plan_version,
                    args=req.args,
                )

        row.status = "APPROVED"
        row.decided_by = req.decided_by
        row.decided_at = datetime.utcnow()
        await db.commit()
        await event_bus.publish(
            AgentEvent(
                event_type="approval_decided",
                session_id=row.session_id,
                payload={"approval_id": row.approval_id, "status": "APPROVED"},
                published_at=datetime.utcnow(),
            )
        )
        return _approval_to_response(row)

    @router.post("/approvals/{approval_id}/reject", response_model=ApprovalResponse)
    async def reject_approval(
        approval_id: str,
        req: ApprovalDecisionRequest,
        _: dict[str, Any] = Depends(require_jwt),
        db: AsyncSession = Depends(get_db),
    ):
        row = (await db.execute(select(ApprovalRow).where(ApprovalRow.approval_id == approval_id))).scalars().first()
        if not row:
            raise HTTPException(status_code=404, detail="approval not found")
        sess = await session_mgr.get_session(db, session_id=row.session_id)
        row.status = "REJECTED"
        row.decided_by = req.decided_by
        row.decided_at = datetime.utcnow()
        row.rejection_reason = req.rejection_reason
        step = (await db.execute(select(PlanStepRow).where(PlanStepRow.step_id == row.step_id))).scalars().first()
        if step and step.status not in ("DONE", "SKIPPED", "FAILED", "AMBIGUOUS"):
            step.status = "SKIPPED"
            step.completed_at = datetime.utcnow()
            reason = req.rejection_reason or f"Approval {row.approval_id} rejected"
            step.last_error = reason
            if sess:
                _log_step_status(sess, step, step.status)
        if sess:
            sess.status = "IDLE"
            sess.error = req.rejection_reason or f"Approval {row.approval_id} rejected"
            sess.updated_at = datetime.utcnow()
        await db.commit()
        await event_bus.publish(
            AgentEvent(
                event_type="approval_decided",
                session_id=row.session_id,
                payload={"approval_id": row.approval_id, "status": "REJECTED"},
                published_at=datetime.utcnow(),
            )
        )
        return _approval_to_response(row)

    @router.get("/dlq", response_model=list[DeadLetterResponse])
    async def list_dlq(
        status: str | None = Query(None),
        session_id: str | None = Query(None),
        db: AsyncSession = Depends(get_db),
    ):
        stmt = select(DeadLetterRow)
        if status:
            stmt = stmt.where(DeadLetterRow.status == status)
        if session_id:
            stmt = stmt.where(DeadLetterRow.session_id == session_id)
        rows = (
            await db.execute(stmt.order_by(DeadLetterRow.created_at.desc()))
        ).scalars().all()
        return [
            DeadLetterResponse(
                dlq_id=r.dlq_id,
                session_id=r.session_id,
                step_id=r.step_id,
                failure_type=r.failure_type,
                reason=r.reason,
                payload=r.payload,
                status=r.status,
                replayed_at=r.replayed_at,
                replayed_by=r.replayed_by,
                dismissed_at=r.dismissed_at,
                dismissed_reason=r.dismissed_reason,
                created_at=r.created_at,
            )
            for r in rows
        ]

    @router.post("/dlq/push", response_model=DeadLetterResponse)
    async def push_dlq(
        req: DeadLetterPushRequest,
        _: dict[str, Any] = Depends(require_jwt),
        db: AsyncSession = Depends(get_db),
    ):
        row = DeadLetterRow(
            dlq_id=generate_uuid(),
            session_id=req.session_id,
            step_id=req.step_id,
            failure_type=req.failure_type,
            reason=req.reason,
            payload=req.payload,
            status="PENDING",
        )
        db.add(row)
        await db.commit()
        await db.refresh(row)
        metrics.inc("dlq_push_total", labels={"failure_type": req.failure_type})
        metrics.inc("dlq_push_rate", labels={"failure_type": req.failure_type})
        return DeadLetterResponse(
            dlq_id=row.dlq_id,
            session_id=row.session_id,
            step_id=row.step_id,
            failure_type=row.failure_type,
            reason=row.reason,
            payload=row.payload,
            status=row.status,
            replayed_at=row.replayed_at,
            replayed_by=row.replayed_by,
            dismissed_at=row.dismissed_at,
            dismissed_reason=row.dismissed_reason,
            created_at=row.created_at,
        )

    @router.post("/dlq/{dlq_id}/replay")
    async def replay_dlq(
        dlq_id: str,
        req: DeadLetterReplayRequest,
        _: dict[str, Any] = Depends(require_jwt),
        db: AsyncSession = Depends(get_db),
    ):
        row = (await db.execute(select(DeadLetterRow).where(DeadLetterRow.dlq_id == dlq_id))).scalars().first()
        if not row:
            raise HTTPException(status_code=404, detail="dlq entry not found")
        sess = await session_mgr.get_session(db, session_id=row.session_id)
        if row.step_id:
            step = (await db.execute(select(PlanStepRow).where(PlanStepRow.step_id == row.step_id))).scalars().first()
            if step:
                step.status = "NOT_STARTED"
                step.last_error = None
                step.started_at = None
                step.completed_at = None
                step.retry_count = 0
                if sess:
                    _log_step_status(sess, step, step.status)
        if sess:
            if row.step_id:
                step = (await db.execute(select(PlanStepRow).where(PlanStepRow.step_id == row.step_id))).scalars().first()
                if step is not None:
                    sess.current_step_index = min(sess.current_step_index or 0, step.step_index)
            sess.status = "EXECUTING"
            sess.error = None
            sess.version += 1
        row.status = "REPLAYED"
        row.replayed_at = datetime.utcnow()
        row.replayed_by = req.replayed_by
        row.dismissed_at = None
        row.dismissed_reason = None
        await db.commit()
        metrics.inc("dlq_replay_total")
        metrics.inc("dlq_replay_success_total")
        metrics.inc("dlq_replay_success_rate")
        await event_bus.publish(
            AgentEvent(
                event_type="dlq_replay_requested",
                session_id=row.session_id,
                payload={"dlq_id": dlq_id},
                published_at=datetime.utcnow(),
            )
        )
        return {"ok": True}

    @router.post("/dlq/{dlq_id}/replay-request")
    async def request_dlq_replay(
        dlq_id: str,
        _: dict[str, Any] = Depends(require_jwt),
        db: AsyncSession = Depends(get_db),
    ):
        return await replay_dlq(dlq_id, DeadLetterReplayRequest(), {}, db)

    @router.post("/dlq/{dlq_id}/dismiss")
    async def dismiss_dlq(
        dlq_id: str,
        req: DeadLetterDismissRequest,
        _: dict[str, Any] = Depends(require_jwt),
        db: AsyncSession = Depends(get_db),
    ):
        row = (await db.execute(select(DeadLetterRow).where(DeadLetterRow.dlq_id == dlq_id))).scalars().first()
        if not row:
            raise HTTPException(status_code=404, detail="dlq entry not found")
        row.status = "DISMISSED"
        row.dismissed_at = datetime.utcnow()
        who = req.dismissed_by or "ops"
        row.dismissed_reason = f"{who}: {req.dismissed_reason}"
        await db.commit()
        return {"ok": True}

    @router.post("/admin/regenerate-tools")
    async def regenerate_tools(
        _: None = Depends(require_admin),
        db: AsyncSession = Depends(get_db),
    ):
        # Best-effort regeneration: fetch spec (HTTP then local fallback) and store tools.md hash in DB.
        from agent.toolgen import fetch_openapi_spec, tools_from_openapi, write_tools_md_and_meta
        import os

        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        local_swagger = os.path.join(repo_root, "emas", "docs", "swagger.json")
        tools_md_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tools.md"))
        openapi_url = os.environ.get("OPENAPI_URL", "http://localhost:8080/swagger/doc.json")
        force_local = os.environ.get("OPENAPI_LOCAL", "").strip() == "1"

        spec = fetch_openapi_spec(openapi_url=openapi_url, local_swagger_json_path=local_swagger, force_local=force_local)
        tools = tools_from_openapi(spec)
        result = await write_tools_md_and_meta(db, tools=tools, tools_md_path=tools_md_path, replace_db=True)
        await event_bus.publish(
            AgentEvent(
                event_type="tool_registry_updated",
                session_id="",
                payload={"tool_count": result.tool_count, "tools_md_hash": result.tools_md_hash},
                published_at=datetime.utcnow(),
            )
        )
        log_event("tool_registry_regenerated", tool_count=result.tool_count, tools_md_hash=result.tools_md_hash)
        return {"ok": True, "tool_count": result.tool_count, "tools_md_hash": result.tools_md_hash}

    @router.get("/metrics", response_class=PlainTextResponse)
    async def get_metrics():
        return PlainTextResponse(metrics.render_prometheus(), media_type="text/plain; version=0.0.4")

    @router.get("/admin/sessions", dependencies=[Depends(require_admin)])
    async def admin_list_sessions(
        status: str | None = Query(None),
        limit: int = Query(100, ge=1, le=500),
        db: AsyncSession = Depends(get_db),
    ):
        stmt = select(SessionRow).order_by(SessionRow.updated_at.desc()).limit(limit)
        if status:
            stmt = stmt.where(SessionRow.status == status)
        rows = (await db.execute(stmt)).scalars().all()
        return [_session_to_response(s) for s in rows]

    @router.get("/admin/approvals/pending", dependencies=[Depends(require_admin)], response_model=list[ApprovalResponse])
    async def admin_pending_approvals(db: AsyncSession = Depends(get_db)):
        rows = (
            await db.execute(select(ApprovalRow).where(ApprovalRow.status == "PENDING").order_by(ApprovalRow.created_at.asc()))
        ).scalars().all()
        return [_approval_to_response(r) for r in rows]

    @router.get("/admin/dlq", dependencies=[Depends(require_admin)], response_model=list[DeadLetterResponse])
    async def admin_list_dlq(
        status: str | None = Query(None),
        session_id: str | None = Query(None),
        db: AsyncSession = Depends(get_db),
    ):
        stmt = select(DeadLetterRow)
        if status:
            stmt = stmt.where(DeadLetterRow.status == status)
        if session_id:
            stmt = stmt.where(DeadLetterRow.session_id == session_id)
        rows = (
            await db.execute(stmt.order_by(DeadLetterRow.created_at.desc()))
        ).scalars().all()
        return [
            DeadLetterResponse(
                dlq_id=r.dlq_id,
                session_id=r.session_id,
                step_id=r.step_id,
                failure_type=r.failure_type,
                reason=r.reason,
                payload=r.payload,
                status=r.status,
                replayed_at=r.replayed_at,
                replayed_by=r.replayed_by,
                dismissed_at=r.dismissed_at,
                dismissed_reason=r.dismissed_reason,
                created_at=r.created_at,
            )
            for r in rows
        ]

    @router.get("/admin/tools", dependencies=[Depends(require_admin)])
    async def admin_list_tools(db: AsyncSession = Depends(get_db)):
        tools_by_name = await tool_registry.get_tools_by_name(db)
        return [tools_by_name[name] for name in sorted(tools_by_name.keys())]

    @router.post("/admin/faults/redis/down", dependencies=[Depends(require_admin)])
    async def admin_fault_redis_down():
        # Fault injection hook for chaos testing (E4.3).
        setattr(event_bus, "_fault_injected", True)
        setattr(event_bus, "_healthy", False)
        return {"ok": True, "redis_fault": "down"}

    @router.post("/admin/faults/redis/up", dependencies=[Depends(require_admin)])
    async def admin_fault_redis_up():
        setattr(event_bus, "_fault_injected", False)
        with contextlib.suppress(Exception):
            await event_bus.reconnect()
        return {"ok": True, "redis_fault": "up"}

    @router.get("/admin/dashboard", dependencies=[Depends(require_admin)], response_class=HTMLResponse)
    async def admin_dashboard(db: AsyncSession = Depends(get_db)):
        sessions = (
            await db.execute(select(SessionRow).order_by(SessionRow.updated_at.desc()).limit(200))
        ).scalars().all()
        approvals = (
            await db.execute(select(ApprovalRow).where(ApprovalRow.status == "PENDING").order_by(ApprovalRow.created_at.asc()))
        ).scalars().all()
        dlq_rows = (
            await db.execute(select(DeadLetterRow).where(DeadLetterRow.status == "PENDING").order_by(DeadLetterRow.created_at.desc()))
        ).scalars().all()
        tools_by_name = await tool_registry.get_tools_by_name(db)

        session_rows = "".join(
            f"<tr><td>{s.session_id}</td><td>{s.user_id}</td><td>{s.status}</td><td>{s.current_step_index}</td><td>{s.error or ''}</td></tr>"
            for s in sessions
        )
        approval_rows = "".join(
            f"<tr><td>{a.approval_id}</td><td>{a.session_id}</td><td>{a.tool_name}</td><td>{a.status}</td></tr>"
            for a in approvals
        )
        dlq_html_rows = "".join(
            f"<tr><td>{d.dlq_id}</td><td>{d.session_id}</td><td>{d.failure_type}</td><td>{d.reason}</td></tr>"
            for d in dlq_rows
        )
        tool_rows = "".join(
            f"<tr><td>{t.name}</td><td>{t.method}</td><td>{t.endpoint}</td><td>{'yes' if t.requires_approval else 'no'}</td></tr>"
            for t in sorted(tools_by_name.values(), key=lambda x: x.name)
        )

        html = f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Factory Agent Admin Dashboard</title>
  <style>
    body {{ font-family: 'Segoe UI', Tahoma, sans-serif; margin: 24px; background: #f2f7fb; color: #112; }}
    h1 {{ margin: 0 0 8px 0; }}
    .grid {{ display: grid; grid-template-columns: 1fr; gap: 16px; }}
    section {{ background: #fff; border-radius: 12px; padding: 14px; box-shadow: 0 2px 8px rgba(0,0,0,.06); }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th, td {{ text-align: left; padding: 8px; border-bottom: 1px solid #e7edf4; }}
    th {{ background: #eef5ff; }}
  </style>
</head>
<body>
  <h1>Factory Agent Dashboard</h1>
  <p>Sessions: {len(sessions)} | Pending approvals: {len(approvals)} | Pending DLQ: {len(dlq_rows)} | Tools: {len(tools_by_name)}</p>
  <div class="grid">
    <section>
      <h2>Sessions</h2>
      <table><thead><tr><th>Session</th><th>User</th><th>Status</th><th>Step</th><th>Error</th></tr></thead><tbody>{session_rows}</tbody></table>
    </section>
    <section>
      <h2>Approval Queue</h2>
      <table><thead><tr><th>Approval</th><th>Session</th><th>Tool</th><th>Status</th></tr></thead><tbody>{approval_rows}</tbody></table>
    </section>
    <section>
      <h2>DLQ Viewer</h2>
      <table><thead><tr><th>DLQ</th><th>Session</th><th>Failure Type</th><th>Reason</th></tr></thead><tbody>{dlq_html_rows}</tbody></table>
    </section>
    <section>
      <h2>Tool Registry</h2>
      <table><thead><tr><th>Name</th><th>Method</th><th>Endpoint</th><th>Approval</th></tr></thead><tbody>{tool_rows}</tbody></table>
    </section>
  </div>
</body>
</html>
"""
        return HTMLResponse(content=html)

    return router
