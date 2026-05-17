from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Protocol

from factory_agent.schemas import ToolInfo


READ_ONLY_TOOL_RESULT = "read_only_tool_result"
APPROVAL_REQUIRED_WORKFLOW = "approval_required_workflow"
TWO_STEP_APPROVAL_CHAIN = "two_step_approval_chain"
REJECTED_APPROVAL = "rejected_approval"
EXPIRED_OR_STALE_APPROVAL = "expired_or_stale_approval"
PARTIAL_FAILURE = "partial_failure"
LARGE_STRUCTURED_RESULT = "large_structured_result"
SSE_FAULT_MARKER = "sse_fault_marker"

SUPPORTED_SCENARIO_CAPABILITIES = frozenset(
    {
        READ_ONLY_TOOL_RESULT,
        APPROVAL_REQUIRED_WORKFLOW,
        TWO_STEP_APPROVAL_CHAIN,
        REJECTED_APPROVAL,
        EXPIRED_OR_STALE_APPROVAL,
        PARTIAL_FAILURE,
        LARGE_STRUCTURED_RESULT,
        SSE_FAULT_MARKER,
    }
)


@dataclass(frozen=True)
class PromptTrigger:
    any_phrases: tuple[str, ...] = ()
    all_phrases: tuple[str, ...] = ()
    regexes: tuple[str, ...] = ()
    exclude_phrases: tuple[str, ...] = ()

    def matches(self, intent: str) -> bool:
        normalized = normalize_prompt(intent)
        if any(phrase.lower() in normalized for phrase in self.exclude_phrases):
            return False
        if self.any_phrases and not any(phrase.lower() in normalized for phrase in self.any_phrases):
            return False
        if self.all_phrases and not all(phrase.lower() in normalized for phrase in self.all_phrases):
            return False
        return not self.regexes or any(re.search(pattern, normalized) for pattern in self.regexes)


@dataclass(frozen=True)
class SeededAction:
    handler: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SeededScenario:
    scenario_id: str
    oracle_ids: tuple[str, ...]
    internal_marker: str
    capabilities: tuple[str, ...]
    trigger: PromptTrigger
    generate: SeededAction
    description: str

    def __post_init__(self) -> None:
        unknown = set(self.capabilities) - SUPPORTED_SCENARIO_CAPABILITIES
        if unknown:
            raise ValueError(f"Unsupported seeded scenario capabilities for {self.scenario_id}: {sorted(unknown)}")


class SeededScenarioRuntime(Protocol):
    _scenario_by_session: dict[str, str]

    async def _large_structured_result(self, *, intent: str, scoped_tools: list[ToolInfo]) -> Any:
        ...

    async def _phase14_start_cascade(
        self,
        *,
        session_id: str,
        changes: list[tuple[str, str]] | None = None,
        audit_scenario: str = "86",
    ) -> Any:
        ...


def normalize_prompt(intent: str) -> str:
    text = intent.lower().replace("->", " to ")
    for ch in "-_/.,;:":
        text = text.replace(ch, " ")
    return " ".join(text.split())


MIGRATED_SEEDED_SCENARIOS: tuple[SeededScenario, ...] = (
    SeededScenario(
        scenario_id="so031_large_structured_result",
        oracle_ids=("SO-031",),
        internal_marker="large_structured_result",
        capabilities=(READ_ONLY_TOOL_RESULT, LARGE_STRUCTURED_RESULT),
        trigger=PromptTrigger(any_phrases=("phase 9 large structured result",)),
        generate=SeededAction(handler="large_structured_result"),
        description="Read-only 80-row structured job result used by SO-031 browser layout oracles.",
    ),
    SeededScenario(
        scenario_id="so005_so041_medium_high_original_high_low",
        oracle_ids=("SO-005", "SO-041"),
        internal_marker="phase14_cascade",
        capabilities=(APPROVAL_REQUIRED_WORKFLOW, TWO_STEP_APPROVAL_CHAIN, REJECTED_APPROVAL),
        trigger=PromptTrigger(
            regexes=(
                r"\bchange all medium priority jobs? to high then change all "
                r"(?:original )?high priority jobs? to low\b",
            ),
            exclude_phrases=("prompt regression", "phase 19"),
        ),
        generate=SeededAction(
            handler="phase14_cascade",
            params={"changes": (("medium", "high"), ("high", "low")), "audit_scenario": "86"},
        ),
        description=(
            "Two-approval original-state cascade shared by SO-005 rejection and SO-041 final-summary coverage."
        ),
    ),
    SeededScenario(
        scenario_id="phase14_cascade_default_high_low_low_medium",
        oracle_ids=("SO-002",),
        internal_marker="phase14_cascade",
        capabilities=(APPROVAL_REQUIRED_WORKFLOW, TWO_STEP_APPROVAL_CHAIN),
        trigger=PromptTrigger(any_phrases=("phase 14 cascading priority update",)),
        generate=SeededAction(
            handler="phase14_cascade",
            params={"changes": (("high", "low"), ("low", "medium")), "audit_scenario": "86"},
        ),
        description="Legacy Phase 14 cascade marker moved from adapter branch code into scenario data.",
    ),
)

BUNDLE_KIND_SCENARIO_MARKERS = {
    "phase14_cascade_priority": "phase14_cascade",
    "phase14_partial_failure": "phase14_partial_failure",
    "phase14_idempotent_replay": "phase14_idempotent_replay",
    "phase14_refresh_active_approval": "phase14_refresh_active_approval",
    "phase14_stream_drop_commit": "phase14_stream_drop_commit",
    "phase14_go_api_500": "phase14_go_api_500",
    "phase14_stale_approval": "phase14_stale_approval",
    "phase14_expired_approval": "phase14_expired_approval",
    "phase14_agreement": "phase14_agreement",
    "phase9_approval_chain": "multi_approval_chain",
}

LEGACY_SEEDED_PROMPT_MARKERS = (
    "phase 9 multi-step ordered",
    "phase 9 multi approval chain",
    "phase 9 approval timeout",
    "phase 9 partial failure",
    "phase 9 schema mismatch",
    "phase 9 duplicate submit",
    "phase 9 out-of-order duplicate sse",
    "phase 9 last-event-id reconnect",
    "phase 9 stream drop recovery",
    "phase 10 refresh during active job",
    "phase 10 long-running stream",
    "phase 14 bulk partial failure",
    "phase 14 idempotent approval replay",
    "phase 14 refresh during active approval",
    "phase 14 stream drop commit recovery",
    "phase 14 go api 500 commit failure",
    "phase 14 stale approval",
    "phase 14 expired approval",
    "phase 14 agreement audit timeline summary",
    "phase 9 isolation alpha",
    "phase 9 isolation beta",
)


class SeededScenarioInterpreter:
    def __init__(self, scenarios: tuple[SeededScenario, ...] = MIGRATED_SEEDED_SCENARIOS):
        self._scenarios = scenarios

    @property
    def scenarios(self) -> tuple[SeededScenario, ...]:
        return self._scenarios

    def match(self, intent: str) -> SeededScenario | None:
        for scenario in self._scenarios:
            if scenario.trigger.matches(intent):
                return scenario
        return None

    def handles_intent(self, intent: str) -> bool:
        normalized = normalize_prompt(intent)
        return self.match(intent) is not None or any(marker in normalized for marker in LEGACY_SEEDED_PROMPT_MARKERS)

    def marker_for_bundle_kind(self, bundle_kind: str) -> str | None:
        return BUNDLE_KIND_SCENARIO_MARKERS.get(bundle_kind)

    async def generate(
        self,
        runtime: SeededScenarioRuntime,
        *,
        intent: str,
        scoped_tools: list[ToolInfo],
        session_id: str,
        call_index: int,
    ) -> Any | None:
        del call_index
        scenario = self.match(intent)
        if scenario is None:
            return None

        runtime._scenario_by_session[session_id] = scenario.internal_marker
        action = scenario.generate
        if action.handler == "large_structured_result":
            return await runtime._large_structured_result(intent=intent, scoped_tools=scoped_tools)
        if action.handler == "phase14_cascade":
            raw_changes = action.params.get("changes")
            changes = [tuple(item) for item in raw_changes] if raw_changes else None
            audit_scenario = str(action.params.get("audit_scenario") or "86")
            return await runtime._phase14_start_cascade(
                session_id=session_id,
                changes=changes,
                audit_scenario=audit_scenario,
            )
        raise ValueError(f"Unsupported seeded scenario generate handler: {action.handler}")
