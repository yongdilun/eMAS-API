from __future__ import annotations

import ast
import re
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from factory_agent.config import get_settings
from factory_agent.planner import PlannerApprovalRequired
from factory_agent.testing_seeded_adapters import SeededPlaywrightPlanner
from factory_agent.testing_seeded_scenarios import APPROVAL_REQUIRED_WORKFLOW
from factory_agent.testing_seeded_scenarios import EXPIRED_OR_STALE_APPROVAL
from factory_agent.testing_seeded_scenarios import LARGE_STRUCTURED_RESULT
from factory_agent.testing_seeded_scenarios import MIGRATED_SEEDED_SCENARIOS
from factory_agent.testing_seeded_scenarios import PARTIAL_FAILURE
from factory_agent.testing_seeded_scenarios import READ_ONLY_TOOL_RESULT
from factory_agent.testing_seeded_scenarios import REJECTED_APPROVAL
from factory_agent.testing_seeded_scenarios import SSE_FAULT_MARKER
from factory_agent.testing_seeded_scenarios import SUPPORTED_SCENARIO_CAPABILITIES
from factory_agent.testing_seeded_scenarios import TWO_STEP_APPROVAL_CHAIN


REPO_ROOT = Path(__file__).resolve().parents[2]
ADAPTER_PATH = REPO_ROOT / "factory-agent" / "factory_agent" / "testing_seeded_adapters.py"

ALLOWED_LEGACY_PHASE_BRANCHES = {
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
}

MIGRATED_PHASE_BRANCHES = {
    "phase 9 large structured result",
    "phase 14 cascading priority update",
}


def _settings():
    return replace(
        get_settings(),
        openai_api_key="test-key",
        planner_openai_base_url=None,
        go_api_base_url="http://seeded-go.invalid",
    )


def _seed_job_rows() -> list[dict[str, Any]]:
    return [
        {"job_id": "JOB-SEED-HIGH-001", "priority": "high"},
        {"job_id": "JOB-SEED-HIGH-002", "priority": "high"},
        {"job_id": "JOB-SEED-MED-001", "priority": "medium"},
        {"job_id": "JOB-SEED-LOW-001", "priority": "low"},
    ]


def _phase_literals_in_if_tests(source: str) -> set[str]:
    tree = ast.parse(source)
    found: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        for child in ast.walk(node.test):
            if isinstance(child, ast.Constant) and isinstance(child.value, str):
                value = child.value.lower()
                if re.search(r"\bphase\s+\d+\b", value):
                    found.add(value)
    return found


def test_seeded_scenario_schema_represents_phase5_capabilities():
    required = {
        READ_ONLY_TOOL_RESULT,
        APPROVAL_REQUIRED_WORKFLOW,
        TWO_STEP_APPROVAL_CHAIN,
        REJECTED_APPROVAL,
        EXPIRED_OR_STALE_APPROVAL,
        PARTIAL_FAILURE,
        LARGE_STRUCTURED_RESULT,
        SSE_FAULT_MARKER,
    }
    assert required <= SUPPORTED_SCENARIO_CAPABILITIES

    migrated = {capability for scenario in MIGRATED_SEEDED_SCENARIOS for capability in scenario.capabilities}
    assert {READ_ONLY_TOOL_RESULT, LARGE_STRUCTURED_RESULT} <= migrated
    assert {APPROVAL_REQUIRED_WORKFLOW, TWO_STEP_APPROVAL_CHAIN, REJECTED_APPROVAL} <= migrated


def test_seeded_planner_declares_legacy_phase_prompts_it_handles():
    planner = SeededPlaywrightPlanner(_settings())

    assert planner.handles_seeded_intent("Run Phase 14 stale approval seeded job update")
    assert planner.handles_seeded_intent("Run Phase 14 idempotent approval replay for one seeded job priority update")
    assert planner.handles_seeded_intent("List jobs for Phase 9 large structured result")
    assert not planner.handles_seeded_intent("Please update a job priority without a job id")


@pytest.mark.asyncio
async def test_large_structured_result_is_driven_by_scenario_data():
    planner = SeededPlaywrightPlanner(_settings())

    result = await planner.generate_plan(
        intent="List jobs for Phase 9 large structured result",
        scoped_tools=[],
        context={"session_id": "scenario-large"},
    )

    assert planner._scenario_by_session["scenario-large"] == "large_structured_result"
    assert result.llm_calls == 0
    assert result.tool_outputs
    output = result.tool_outputs[0]
    assert output["tool_name"] == "get__jobs"
    assert output["summary"] == "Phase 9 large structured result rendered 80 seeded rows without losing completion state."
    assert output["result"]["total"] == 80
    assert len(output["result"]["data"]) == 80


@pytest.mark.asyncio
async def test_so005_cascade_approval_chain_is_driven_by_scenario_data(monkeypatch):
    planner = SeededPlaywrightPlanner(_settings())
    prompt = "change all medium priority job to high then change all high priority job to low"

    async def fake_seed_rows() -> list[dict[str, Any]]:
        return _seed_job_rows()

    apply_calls: list[dict[str, Any]] = []

    async def fake_apply_priority_updates(**kwargs: Any) -> list[dict[str, Any]]:
        apply_calls.append(kwargs)
        return [
            {
                "job_id": job_id,
                "original_priority": kwargs["original_priorities"].get(job_id),
                "requested_priority": kwargs["requested_priority"],
                "status": "succeeded",
            }
            for job_id in kwargs["job_ids"]
        ]

    def fail_legacy_cascade_parser(lowered: str) -> list[tuple[str, str]]:
        raise AssertionError(f"migrated SO-005 prompt should not hit legacy parser: {lowered}")

    monkeypatch.setattr(planner, "_seed_job_rows", fake_seed_rows)
    monkeypatch.setattr(planner, "_phase14_apply_priority_updates", fake_apply_priority_updates)
    monkeypatch.setattr(planner, "_phase14_cascade_priority_changes", fail_legacy_cascade_parser)

    with pytest.raises(PlannerApprovalRequired) as first:
        await planner.generate_plan(
            intent=prompt,
            scoped_tools=[],
            context={"session_id": "scenario-so005"},
        )

    first_approval = first.value.approval
    assert planner._scenario_by_session["scenario-so005"] == "phase14_cascade"
    assert first_approval["bundle_ui"]["write_set"] == "original_medium_to_high"
    assert [item["args"] for item in first_approval["preview"]] == [
        {"id": "JOB-SEED-MED-001", "priority": "high"}
    ]

    planner.seed_resume_context(
        session_id="scenario-so005",
        intent=prompt,
        approval_payload={
            "approval_id": "approval-so005-first",
            "bundle_ui": first_approval["bundle_ui"],
        },
    )

    with pytest.raises(PlannerApprovalRequired) as second:
        await planner.resume_after_approval(session_id="scenario-so005", approved=True)

    second_approval = second.value.approval
    assert apply_calls[0]["scenario"] == "86"
    assert apply_calls[0]["write_set"] == "original_medium_to_high"
    assert apply_calls[0]["approval_id"] == "approval-so005-first"
    assert second_approval["bundle_ui"]["write_set"] == "original_high_to_low"
    assert second_approval["bundle_ui"]["previous_approval_id"] == "approval-so005-first"
    assert [item["args"] for item in second_approval["preview"]] == [
        {"id": "JOB-SEED-HIGH-001", "priority": "low"},
        {"id": "JOB-SEED-HIGH-002", "priority": "low"},
    ]

    rejected = await planner.resume_after_approval(session_id="scenario-so005", approved=False)

    assert rejected.tool_outputs == []
    assert "rejected" in rejected.draft.plan_explanation.lower()
    assert len(apply_calls) == 1


@pytest.mark.asyncio
async def test_legacy_unmigrated_partial_failure_branch_still_works(monkeypatch):
    planner = SeededPlaywrightPlanner(_settings())

    async def fake_seed_rows() -> list[dict[str, Any]]:
        return _seed_job_rows()

    monkeypatch.setattr(planner, "_seed_job_rows", fake_seed_rows)

    with pytest.raises(PlannerApprovalRequired) as exc:
        await planner.generate_plan(
            intent="Run Phase 14 bulk partial failure priority update with exact row outcomes",
            scoped_tools=[],
            context={"session_id": "legacy-partial-failure"},
        )

    approval = exc.value.approval
    assert planner._scenario_by_session["legacy-partial-failure"] == "phase14_partial_failure"
    assert approval["bundle_ui"]["kind"] == "phase14_partial_failure"
    assert approval["bundle_ui"]["write_set"] == "bulk_partial_failure"


def test_testing_seeded_adapter_does_not_add_untracked_phase_prompt_branches():
    source = ADAPTER_PATH.read_text(encoding="utf-8")
    found = _phase_literals_in_if_tests(source)

    assert not (found & MIGRATED_PHASE_BRANCHES), (
        "Migrated phase prompts must stay in testing_seeded_scenarios.py data, not adapter if branches."
    )
    assert found <= ALLOWED_LEGACY_PHASE_BRANCHES, (
        "New phase-prompt adapter branches must be explicitly allowed in "
        "docs/qa/HARDCODE_REDUCTION_TRACK.md before adding them here. "
        f"Unexpected: {sorted(found - ALLOWED_LEGACY_PHASE_BRANCHES)}"
    )
