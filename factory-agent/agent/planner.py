from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any, Literal

from .config import Settings
from .plan_validator import validate_plan
from .prompting import build_planner_prompt
from .schemas import PlanDraft, PlanStepDraft, ToolInfo
from .telemetry import log_event, log_llm_prompt, log_llm_prompt_skipped
from .tool_registry import ToolRegistry


PlannerBackendName = Literal["legacy", "langchain"]


class PlannerBackendError(RuntimeError):
    pass


class PlannerClarificationError(PlannerBackendError):
    pass


@dataclass(frozen=True)
class PlannerResult:
    draft: PlanDraft
    backend_used: PlannerBackendName
    llm_calls: int = 0


_NUMBER_RE = re.compile(r"\b\d+\b")
_KEYWORD_ID_RE = re.compile(r"\b(machine|job|inventory|approval|proposal|line|slot|schedule)\s+#?(\d+)\b", re.IGNORECASE)
_KEYWORD_TOKEN_ID_RE = re.compile(
    r"\b(machine|job|inventory|material|approval|proposal|line|slot|schedule|arrival|product)\s+(?:id\s+)?([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+)\b",
    re.IGNORECASE,
)
_TOKEN_ID_RE = re.compile(r"\b([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+)\b")
_SKU_RE = re.compile(r"\bsku\s*[:#-]?\s*([a-zA-Z0-9_-]+)\b", re.IGNORECASE)
_PATH_PARAM_RE = re.compile(r"\{([a-zA-Z0-9_]+)\}")
_SEED_ID_PREFIXES: list[tuple[str, str]] = [
    ("AIPROP-", "proposal"),
    ("JOB-", "job"),
    ("SLOT-", "slot"),
    ("MAT-", "inventory"),
    ("ARR-", "arrival"),
    ("APPROVAL-", "approval"),
    ("M-", "machine"),
    ("P-", "product"),
]
_INTENT_MATCH_KEYWORDS = (
    "slot",
    "slots",
    "schedule",
    "proposal",
    "proposals",
    "material",
    "materials",
    "inventory",
    "arrival",
    "arrivals",
    "approval",
    "machine",
    "job",
)

_COMPOUND_SEPARATOR_RE = re.compile(
    r"\b(?:and then|then|next|after that|afterwards|finally)\b|[;\n.]+",
    re.IGNORECASE,
)
_AND_CONNECTOR_RE = re.compile(r"\b(?:and|also)\b", re.IGNORECASE)
_ACTION_VERB_RE = re.compile(
    r"\b(?:check|show|list|get|find|view|inspect|update|set|create|delete|approve|reject|replan|assign|schedule|replenish|move|run)\b",
    re.IGNORECASE,
)


def _tool_prefers_entity_lookup(tool: ToolInfo) -> bool:
    token = f"{tool.name} {tool.endpoint}".lower()
    return "{id}" in token or "_{id}" in token


def _path_param_names(endpoint: str) -> list[str]:
    return [match.group(1) for match in _PATH_PARAM_RE.finditer(endpoint or "")]


def _normalize_entity_keyword(keyword: str) -> str:
    lowered = keyword.lower()
    return "inventory" if lowered == "material" else lowered


def _infer_entity_from_identifier(token: str) -> str | None:
    upper = token.upper()
    for prefix, entity in _SEED_ID_PREFIXES:
        if upper.startswith(prefix):
            return entity
    return None


def _infer_primary_entity(tool: ToolInfo) -> str | None:
    name = tool.name.lower()
    endpoint = (tool.endpoint or "").lower()
    token = f"{name} {endpoint} {' '.join(tool.capability_tags or [])}".lower()

    if "/jobs/{id}/slots" in endpoint or "jobs_{id}_slots" in name:
        return "job"
    if "/jobs/{id}" in endpoint or "jobs_{id}" in name:
        return "job"
    if "/proposals/{id}" in endpoint or "proposals_{id}" in name:
        return "proposal"
    if "/machines/{id}" in endpoint or "machines_{id}" in name or "machine" in token:
        return "machine"
    if "/inventory/materials/{id}" in endpoint or "materials_{id}" in name or "material" in token:
        return "inventory"
    if "approval" in token:
        return "approval"
    if "arrival" in token:
        return "arrival"
    if "product" in token:
        return "product"
    if "line" in token:
        return "line"
    if "slot" in token:
        return "slot"
    return None


def _tool_matches_entity(tool: ToolInfo, entity: str | None) -> bool:
    return bool(entity) and _infer_primary_entity(tool) == entity


def _tool_intent_match_score(intent: str, tool: ToolInfo) -> int:
    intent_lower = intent.lower()
    token = f"{tool.name} {tool.description} {tool.endpoint} {' '.join(tool.capability_tags or [])}".lower()
    score = 0
    for keyword in _INTENT_MATCH_KEYWORDS:
        if keyword in intent_lower and keyword in token:
            score += 1
    return score


def _extract_intent_entities(intent: str) -> dict[str, Any]:
    numbers = [int(match.group(0)) for match in _NUMBER_RE.finditer(intent or "")]
    ids_by_keyword: dict[str, Any] = {}
    for match in _KEYWORD_ID_RE.finditer(intent or ""):
        ids_by_keyword[match.group(1).lower()] = int(match.group(2))
    explicit_ids: list[str] = []
    for match in _KEYWORD_TOKEN_ID_RE.finditer(intent or ""):
        keyword = _normalize_entity_keyword(match.group(1))
        value = match.group(2)
        ids_by_keyword[keyword] = value
        explicit_ids.append(value)
    for match in _TOKEN_ID_RE.finditer(intent or ""):
        value = match.group(1)
        explicit_ids.append(value)
        inferred = _infer_entity_from_identifier(value)
        if inferred and inferred not in ids_by_keyword:
            ids_by_keyword[inferred] = value

    sku_match = _SKU_RE.search(intent or "")
    sku_value = sku_match.group(1) if sku_match else None

    return {
        "numbers": numbers,
        "ids_by_keyword": ids_by_keyword,
        "explicit_ids": list(dict.fromkeys(explicit_ids)),
        "sku": sku_value,
    }


def _extract_required_args(intent: str, tool: ToolInfo) -> tuple[dict[str, Any], list[str]]:
    schema = tool.input_schema or {}
    properties = schema.get("properties", {})
    required = list(dict.fromkeys(list(schema.get("required", [])) + _path_param_names(tool.endpoint)))
    entities = _extract_intent_entities(intent)
    primary_entity = _infer_primary_entity(tool)
    args: dict[str, Any] = {}
    missing: list[str] = []

    for field in required:
        raw = properties.get(field, {})
        field_type = raw.get("type")
        if isinstance(field_type, list):
            field_type = next((t for t in field_type if t != "null"), "string")
        field_name = field.lower()

        value: Any | None = None
        if field_name == "sku":
            value = entities["sku"]
        elif field_name == "id":
            value = entities["ids_by_keyword"].get(primary_entity) if primary_entity else None
        elif field_name == "job_id":
            value = entities["ids_by_keyword"].get("job")
        elif field_name in ("machine_id",):
            value = entities["ids_by_keyword"].get("machine")
        elif field_name in ("inventory_id", "item_id"):
            value = entities["ids_by_keyword"].get("inventory")
        elif field_name == "material_id":
            value = entities["ids_by_keyword"].get("inventory")
        elif field_name == "approval_id":
            value = entities["ids_by_keyword"].get("approval")
        elif field_name == "proposal_id":
            value = entities["ids_by_keyword"].get("proposal")
        elif field_name == "line_id":
            value = entities["ids_by_keyword"].get("line")

        if value is None and field_name.endswith("_id"):
            keyword = field_name[:-3]
            keyword = "inventory" if keyword == "material" else keyword
            value = entities["ids_by_keyword"].get(keyword)

        if value is None and field_name == "id" and len(entities["explicit_ids"]) == 1:
            value = entities["explicit_ids"][0]

        if value is None and field_type in ("integer", "number") and len(entities["numbers"]) == 1:
            value = entities["numbers"][0]

        if value is None:
            missing.append(field)
            continue

        if field_type == "string":
            args[field] = str(value)
        elif field_type == "integer":
            args[field] = int(value)
        elif field_type == "number":
            args[field] = float(value)
        else:
            args[field] = value

    return args, missing


def _select_legacy_tool(intent: str, scoped_tools: list[ToolInfo]) -> ToolInfo:
    entities = _extract_intent_entities(intent)
    preferred_entity = next(iter(entities["ids_by_keyword"]), None)
    has_explicit_id = bool(entities["ids_by_keyword"]) or len(entities["numbers"]) == 1 or len(entities["explicit_ids"]) == 1

    ranked = sorted(
        scoped_tools,
        key=lambda t: (
            not t.is_read_only,
            not _tool_matches_entity(t, preferred_entity),
            not (has_explicit_id and _tool_prefers_entity_lookup(t)),
            -_tool_intent_match_score(intent, t),
            len((t.input_schema or {}).get("required", [])),
            t.name,
        ),
    )
    return ranked[0]


def _split_compound_intent(intent: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", intent or "").strip()
    if not normalized:
        return [""]

    parts = [part.strip(" ,") for part in _COMPOUND_SEPARATOR_RE.split(normalized) if part and part.strip(" ,")]
    if len(parts) > 1:
        return parts

    # Fall back to a conservative "and"/"also" split only when the request
    # looks genuinely multi-action, so we do not split ordinary noun phrases.
    if " and " in normalized.lower() or " also " in normalized.lower():
        parts = [part.strip(" ,") for part in _AND_CONNECTOR_RE.split(normalized) if part and part.strip(" ,")]
        actionful_parts = sum(1 for part in parts if _ACTION_VERB_RE.search(part))
        if len(parts) > 1 and actionful_parts >= 2:
            return parts

    return [normalized]


def _build_legacy_plan_explanation(intent: str, steps: list[PlanStepDraft]) -> str:
    stripped_intent = intent.strip() or "user request"
    if len(steps) == 1:
        return f"Use `{steps[0].tool_name}` to address intent: {stripped_intent}."

    parts = [f"First use `{steps[0].tool_name}`."]
    for step in steps[1:]:
        parts.append(f"Then use `{step.tool_name}`.")
    return f"{' '.join(parts)} Intent: {stripped_intent}."


def _build_legacy_risk_summary(scoped_tools: list[ToolInfo], steps: list[PlanStepDraft]) -> str:
    tools_by_name = {tool.name: tool for tool in scoped_tools}
    write_steps = [
        step
        for step in steps
        if (tool := tools_by_name.get(step.tool_name)) and not tool.is_read_only
    ]
    if not steps:
        return "No executable steps were generated."
    if write_steps:
        return "This plan includes write operations, so any configured approval gates must be respected before execution."
    return "This plan is read-only and should only retrieve information."


def build_planner_visible_tools(scoped_tools: list[ToolInfo]) -> list[dict[str, Any]]:
    wrappers: list[dict[str, Any]] = []
    for tool in scoped_tools:
        wrappers.append(
            {
                "name": tool.name,
                "description": tool.description,
                "method": tool.method,
                "endpoint": tool.endpoint,
                "input_schema": tool.input_schema,
                "requires_approval": tool.requires_approval,
            }
        )
    return wrappers


class LegacyPlannerBackend:
    async def generate_plan(
        self,
        *,
        intent: str,
        scoped_tools: list[ToolInfo],
        context: dict[str, Any] | None = None,
        tools_markdown: str = "",
    ) -> PlannerResult:
        del context, tools_markdown
        log_llm_prompt_skipped(
            component="planner",
            backend="legacy",
            reason="planner_backend=legacy",
            metadata={"intent": intent, "scoped_tool_count": len(scoped_tools)},
        )
        if not scoped_tools:
            raise PlannerBackendError("No scoped tools available to generate a plan.")

        clauses = _split_compound_intent(intent)
        step_drafts: list[PlanStepDraft] = []
        for idx, clause in enumerate(clauses):
            selected = _select_legacy_tool(clause, scoped_tools)
            args, missing = _extract_required_args(clause, selected)
            if missing:
                # If the clause lost an identifier during splitting, retry with
                # the full intent before asking the user for clarification.
                fallback_args, fallback_missing = _extract_required_args(intent, selected)
                if not fallback_missing:
                    args = fallback_args
                    missing = []

            if missing:
                # For approval-gated tools (typically write operations), allow
                # partial args so the UI can present a schema-driven form for the
                # user to fill/confirm at approval time.
                if not selected.requires_approval:
                    pretty = ", ".join(missing)
                    raise PlannerClarificationError(
                        f"Need {pretty} before I can use `{selected.name}` for: {clause.strip() or intent.strip() or 'user request'}."
                    )

            step_drafts.append(
                PlanStepDraft(
                    step_index=idx,
                    tool_name=selected.name,
                    args=args,
                    depends_on=[idx - 1] if idx > 0 else [],
                )
            )

        draft = PlanDraft(
            plan_explanation=_build_legacy_plan_explanation(intent, step_drafts),
            risk_summary=_build_legacy_risk_summary(scoped_tools, step_drafts),
            steps=step_drafts,
        )
        return PlannerResult(draft=draft, backend_used="legacy", llm_calls=0)


class LangChainPlannerBackend:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._legacy = LegacyPlannerBackend()

    def _build_chat_model(self):
        from langchain_openai import ChatOpenAI

        kwargs: dict[str, Any] = {
            "model": self._settings.planner_model,
            "temperature": 0,
            "timeout": 60,
            "max_retries": 0,
        }
        if self._settings.openai_base_url:
            kwargs["base_url"] = self._settings.openai_base_url
            # llama.cpp OpenAI-compatible servers usually ignore api_key but client may require one.
            kwargs["api_key"] = self._settings.openai_api_key or "local"
        elif self._settings.openai_api_key:
            kwargs["api_key"] = self._settings.openai_api_key
        return ChatOpenAI(**kwargs)

    def _extract_json_obj(self, text: str) -> dict[str, Any] | None:
        candidate = text.strip()
        if not candidate:
            return None
        if candidate.startswith("```"):
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", candidate, flags=re.DOTALL | re.IGNORECASE)
            if match:
                candidate = match.group(1).strip()
        if not candidate.startswith("{"):
            start = candidate.find("{")
            end = candidate.rfind("}")
            if start >= 0 and end > start:
                candidate = candidate[start : end + 1]
        try:
            parsed = json.loads(candidate)
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            return None

    def _is_candidate_valid(self, draft: PlanDraft, scoped_tools: list[ToolInfo]) -> bool:
        tool_map = {t.name: t for t in scoped_tools}
        result = validate_plan(draft, tool_map, max_steps=self._settings.max_plan_steps)
        return result.ok

    async def generate_plan(
        self,
        *,
        intent: str,
        scoped_tools: list[ToolInfo],
        context: dict[str, Any] | None = None,
        tools_markdown: str = "",
    ) -> PlannerResult:
        try:
            from langchain_openai import ChatOpenAI
        except Exception as e:
            raise PlannerBackendError(
                "LangChain planner backend unavailable; install langchain-openai and configure API credentials."
            ) from e

        scoped_names = [t.name for t in scoped_tools]
        prompt = build_planner_prompt(
            user_goal=intent,
            tools_markdown=tools_markdown,
            scoped_tool_names=scoped_names,
        )
        wrappers = build_planner_visible_tools(scoped_tools)
        context_payload = context or {}
        combined_prompt = (
            f"{prompt}\n\n"
            f"Planner-visible tool wrappers (for planning only; do not execute):\n{wrappers}\n\n"
            f"Planner context:\n{context_payload}\n"
        )

        llm_calls = 0
        model = self._build_chat_model()

        # Attempt 1: provider-native structured output.
        try:
            log_llm_prompt(
                component="planner",
                backend="langchain",
                model=self._settings.planner_model,
                prompt=combined_prompt,
                metadata={
                    "attempt": "structured_output",
                    "intent": intent,
                    "scoped_tool_count": len(scoped_tools),
                    "scoped_tools": scoped_names,
                },
            )
            structured = model.with_structured_output(PlanDraft)
            raw = await structured.ainvoke(combined_prompt)
            llm_calls += 1
            draft = raw if isinstance(raw, PlanDraft) else PlanDraft.model_validate(raw)
            if self._is_candidate_valid(draft, scoped_tools):
                return PlannerResult(draft=draft, backend_used="langchain", llm_calls=llm_calls)
        except Exception:
            pass

        # Attempt 2: ask for plain JSON text and parse manually.
        repair_prompt = (
            f"{combined_prompt}\n\n"
            "Return only a JSON object matching PlanDraft. "
            "No markdown, no explanation, no surrounding text."
        )
        try:
            log_llm_prompt(
                component="planner",
                backend="langchain",
                model=self._settings.planner_model,
                prompt=repair_prompt,
                metadata={
                    "attempt": "json_repair",
                    "intent": intent,
                    "scoped_tool_count": len(scoped_tools),
                    "scoped_tools": scoped_names,
                },
            )
            raw_resp = await model.ainvoke(repair_prompt)
            llm_calls += 1
            content = (getattr(raw_resp, "content", "") or "").strip()
            parsed = self._extract_json_obj(content)
            if parsed is not None:
                draft = PlanDraft.model_validate(parsed)
                if self._is_candidate_valid(draft, scoped_tools):
                    return PlannerResult(draft=draft, backend_used="langchain", llm_calls=llm_calls)
        except Exception:
            pass

        # Last resort: deterministic safe draft so runtime can continue through existing validator and safety gates.
        fallback = await self._legacy.generate_plan(
            intent=intent,
            scoped_tools=scoped_tools,
            context=context,
            tools_markdown=tools_markdown,
        )
        return PlannerResult(draft=fallback.draft, backend_used="legacy", llm_calls=max(1, llm_calls))


class PlannerAdapter:
    def __init__(self, *, settings: Settings, tool_registry: ToolRegistry):
        self._settings = settings
        self._tool_registry = tool_registry
        self._legacy = LegacyPlannerBackend()
        self._langchain = LangChainPlannerBackend(settings)

    async def generate_plan(
        self,
        *,
        intent: str,
        scoped_tools: list[ToolInfo],
        context: dict[str, Any] | None = None,
        force_backend: PlannerBackendName | None = None,
    ) -> PlannerResult:
        backend = (force_backend or self._settings.planner_backend or "legacy").strip().lower()
        tools_markdown = self._tool_registry.load_tools_markdown()
        if backend == "langchain":
            try:
                return await self._langchain.generate_plan(
                    intent=intent,
                    scoped_tools=scoped_tools,
                    context=context,
                    tools_markdown=tools_markdown,
                )
            except PlannerBackendError as exc:
                if not self._settings.planner_fallback_to_legacy:
                    raise
                log_event(
                    "planner_backend_fallback",
                    level="WARNING",
                    requested_backend="langchain",
                    fallback_backend="legacy",
                    intent=intent,
                    scoped_tool_count=len(scoped_tools),
                    error=str(exc),
                )
                return await self._legacy.generate_plan(
                    intent=intent,
                    scoped_tools=scoped_tools,
                    context=context,
                    tools_markdown=tools_markdown,
                )
        return await self._legacy.generate_plan(
            intent=intent,
            scoped_tools=scoped_tools,
            context=context,
            tools_markdown=tools_markdown,
        )
