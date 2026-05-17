import json
from pathlib import Path

import pytest

from factory_agent.api.routers.messages import _CANCEL_COMMAND_RE
from factory_agent.config import Settings
from factory_agent.planning.intent import (
    assess_intent,
    intent_constraint_values,
    loto_query_with_resolved_machine_context,
    resolve_contextual_loto_machine_id,
    should_clarify_loto_machine,
    should_route_loto_to_rag,
)
from factory_agent.planning.tool_selector import ToolSelector
from factory_agent.schemas import ToolInfo
from factory_agent.testing_seeded_adapters import SeededPlaywrightPlanner, SeededPlaywrightRAGPipeline
from tests.support.stateful_oracle_harness import load_oracle


REPO_ROOT = Path(__file__).resolve().parents[2]
BANK_PATH = REPO_ROOT / "tests" / "e2e" / "scenarios" / "manual_prompt_regressions.json"


def _load_bank():
    return json.loads(BANK_PATH.read_text(encoding="utf-8"))


def _settings(**overrides):
    base = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        redis_url=None,
        go_api_base_url="http://testserver",
        worker_count=1,
        session_queue_size=10,
        max_plan_steps=10,
        max_session_steps=50,
        max_replans=5,
        max_llm_calls=20,
        max_session_duration_s=1800,
        http_timeout_s=2.0,
        tool_selector_backend="retrieval",
        tool_selector_top_k=6,
        tool_selector_candidate_pool=10,
    )
    values = base.__dict__.copy()
    values.update(overrides)
    return Settings(**values)


def _tool(name, description, endpoint, method, tags, *, read_only=True, approval=False):
    return ToolInfo(
        name=name,
        description=description,
        endpoint=endpoint,
        method=method,
        input_schema={"type": "object", "properties": {}},
        is_read_only=read_only,
        requires_approval=approval,
        capability_tags=tags,
    )


def _route_matrix_tools():
    return {
        "get__machines_{id}": _tool(
            "get__machines_{id}",
            "Get machine by id and status",
            "/machines/{id}",
            "GET",
            ["machine", "status", "lookup"],
        ),
        "get__jobs": _tool(
            "get__jobs",
            "List jobs by priority and status",
            "/jobs",
            "GET",
            ["job", "list", "priority"],
        ),
        "put__jobs_{id}": _tool(
            "put__jobs_{id}",
            "Update job priority by id",
            "/jobs/{id}",
            "PUT",
            ["job", "update", "priority"],
            read_only=False,
            approval=True,
        ),
        "get__chatbot_approval_pending": _tool(
            "get__chatbot_approval_pending",
            "List pending approvals",
            "/chatbot/approval/pending",
            "GET",
            ["approval", "pending", "list"],
        ),
        "post__sessions_{id}_cancel": _tool(
            "post__sessions_{id}_cancel",
            "Cancel the current session run",
            "/sessions/{id}/cancel",
            "POST",
            ["session", "cancel", "run"],
            read_only=False,
        ),
    }


def test_phase19_scenario_116_loto_wording_matrix_uses_same_rag_route():
    bank = _load_bank()
    loto_entries = [
        entry
        for entry in bank["prompts"]
        if (
            entry["id"] == "phase18-loto-m-cnc-01"
            or entry["id"].startswith("phase19-loto-")
            or entry.get("selected_oracle") == "SO-023"
        )
        and entry["expected"]["primary_route"] == "rag_loto"
    ]

    assert len(loto_entries) >= 5
    for entry in loto_entries:
        prompt = entry["source_prompt"]
        assert entry["expected"]["primary_route"] == "rag_loto"
        assert intent_constraint_values(prompt, "machine_id") == ["M-CNC-01"]
        assert intent_constraint_values(prompt, "job_id") == []
        assert should_clarify_loto_machine(prompt) is False
        assert should_route_loto_to_rag(prompt) is True
        assert entry["expected"]["required_source"] == {
            "machine_id": "M-CNC-01",
            "procedure_id": "LOTO-M-CNC-01",
        }


@pytest.mark.parametrize(
    ("prompt", "expected_machine_ids", "expected_job_ids"),
    [
        ("Status for M-CNC-01, please; job JOB-SEED-001.", ["M-CNC-01"], ["JOB-SEED-001"]),
        ("check m-cnc-01 and job-seed-001", ["M-CNC-01"], ["JOB-SEED-001"]),
        ('Use "M-CNC-01" with "JOB-SEED-001" for this check.', ["M-CNC-01"], ["JOB-SEED-001"]),
        ("machine (M-CNC-01) for work order (JOB-SEED-001)", ["M-CNC-01"], ["JOB-SEED-001"]),
        ("### IDs\n- machine: `m-cnc-01`\n- job: **job-seed-001**", ["M-CNC-01"], ["JOB-SEED-001"]),
        ("Machine:\nM-CNC-01\nJob:\nJOB-SEED-001", ["M-CNC-01"], ["JOB-SEED-001"]),
        ("need lockout tagout for m-cnc-01 before service", ["M-CNC-01"], []),
    ],
)
def test_phase19_scenario_117_machine_and_job_id_extraction_matrix(prompt, expected_machine_ids, expected_job_ids):
    assert intent_constraint_values(prompt, "machine_id") == expected_machine_ids
    assert intent_constraint_values(prompt, "job_id") == expected_job_ids


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("label", "prompt", "expected_action", "expected_entity", "expected_tools"),
    [
        ("machine_status", "show status for machine M-CNC-01", "read", "machine", ["get__machines_{id}"]),
        ("job_listing", "list high priority jobs", "read", "job", ["get__jobs"]),
        ("priority_mutation", "change all low priority jobs to high", "update", "job", ["put__jobs_{id}"]),
        ("approval", "show pending approvals", "approval", None, ["get__chatbot_approval_pending"]),
        ("cancel", "cancel the current run", "update", None, ["post__sessions_{id}_cancel"]),
    ],
)
async def test_phase19_scenario_118_route_selection_matrix(label, prompt, expected_action, expected_entity, expected_tools):
    del label
    assessment = assess_intent(prompt)
    assert assessment.kind == "operations"
    assert assessment.action == expected_action
    assert assessment.entity == expected_entity

    selector = ToolSelector(_settings())
    selected = await selector.select_tools(
        intent=prompt,
        tools_by_name=_route_matrix_tools(),
        mode="normal",
        max_tools=10,
    )
    for tool_name in expected_tools:
        assert tool_name in selected.tool_names


def test_phase19_scenario_118_loto_route_selection_short_circuits_to_rag():
    prompt = "Before servicing M-CNC-01, which LOTO procedure applies?"
    assessment = assess_intent(prompt)

    assert should_route_loto_to_rag(prompt) is True
    assert should_clarify_loto_machine(prompt) is False
    assert assessment.kind == "operations"
    assert assessment.entity == "machine"


@pytest.mark.parametrize("oracle_id", ["SO-021", "SO-023", "SO-025"])
def test_so021_so023_so025_prompt_oracles_route_loto_to_rag_with_machine_id(oracle_id):
    oracle = load_oracle(oracle_id)
    prompt = oracle["prompt"]
    route = oracle["expected_route"]

    assert intent_constraint_values(prompt, "machine_id") == [route["machine_id"]]
    assert intent_constraint_values(prompt, "job_id") == []
    assert should_clarify_loto_machine(prompt) is False
    assert should_route_loto_to_rag(prompt) is True

    assessment = assess_intent(prompt)
    assert assessment.kind == "operations"
    assert assessment.entity == "machine"
    assert route["route"] == "rag.loto_procedure"
    forbidden_routes = route.get("must_not_route_to") or route.get("negative_route_assertions") or []
    assert "tool.read.machine_status" in forbidden_routes


def test_so022_prompt_oracle_clarifies_missing_loto_machine_without_default_id():
    oracle = load_oracle("SO-022")
    prompt = oracle["prompt"]

    assert intent_constraint_values(prompt, "machine_id") == []
    assert should_clarify_loto_machine(prompt) is True
    assert should_route_loto_to_rag(prompt) is False

    assessment = assess_intent(prompt)
    assert assessment.kind == "operations"
    assert assessment.entity == "machine"
    assert oracle["expected_route"]["route"] == "clarification.machine_id_missing"
    assert "M-CNC-01" in oracle["expected_route"]["must_not_invent"]
    assert "M-CNC-01" in oracle["expected_final_response"]["must_not_include"]


@pytest.mark.asyncio
async def test_so022_seeded_rag_does_not_default_missing_loto_machine_to_cnc_fixture():
    oracle = load_oracle("SO-022")
    result = await SeededPlaywrightRAGPipeline().run(query=oracle["prompt"], session_id="so022-rag-default")

    assert "M-CNC-01" not in result.answer
    assert "Seeded LOTO Procedure for M-CNC-01" not in result.answer
    assert result.sources == []


def test_so026_loto_followup_resolves_machine_id_from_immediately_previous_turn():
    oracle = load_oracle("SO-026")
    second_prompt = oracle["prompt_sequence"][1]["prompt"]
    previous_texts = [
        "Machine M-CNC-01 is RUNNING from seeded Go API data.",
        oracle["prompt_sequence"][0]["prompt"],
    ]

    resolved = resolve_contextual_loto_machine_id(second_prompt, previous_texts)
    assert resolved == "M-CNC-01"

    contextual_prompt = loto_query_with_resolved_machine_context(second_prompt, resolved)
    assert intent_constraint_values(contextual_prompt, "machine_id") == ["M-CNC-01"]
    assert should_clarify_loto_machine(contextual_prompt) is False
    assert should_route_loto_to_rag(contextual_prompt) is True
    assert resolve_contextual_loto_machine_id("What LOTO procedure applies before working on M-CNC-01?", previous_texts) is None
    assert "Machine ID:" not in contextual_prompt


def test_so028_seeded_cancel_fixture_prompt_is_not_a_cancel_command():
    assert _CANCEL_COMMAND_RE.match("cancel the current run")
    assert _CANCEL_COMMAND_RE.match("stop this operation")
    assert _CANCEL_COMMAND_RE.match("do not do this")
    assert not _CANCEL_COMMAND_RE.match("Start a seeded cancel jobs run and keep it executing")
    assert not _CANCEL_COMMAND_RE.match("Show cancellation history for job JOB-SEED-001")


@pytest.mark.parametrize(
    ("prompt", "expected"),
    [
        ("change all high priority job to low then change all low priority job to medium", [("high", "low"), ("low", "medium")]),
        ("change all medium priority job to high then change all high priority job to medium", [("medium", "high"), ("high", "medium")]),
        ("change all low priority job to high then change all high priority job to low", [("low", "high"), ("high", "low")]),
        ("change all high priority job to medium then change all medium priority job to low", [("high", "medium"), ("medium", "low")]),
    ],
)
def test_phase19_scenario_119_cascade_prompt_matrix_extracts_two_write_sets(prompt, expected):
    planner = SeededPlaywrightPlanner(_settings())

    assert planner._phase14_cascade_priority_changes(prompt.lower()) == expected


def test_phase19_scenarios_122_123_regression_bank_schema_and_triage_rule():
    bank = _load_bank()
    required = set(bank["schema"]["required_fields"])
    severities = set(bank["schema"]["severity_values"])
    allowed_coverage = set(bank["schema"]["coverage_categories"])
    triage_categories = set(bank["triage_rule"]["coverage_categories"])

    assert required == {
        "source_prompt",
        "observed_failure",
        "expected_behavior",
        "artifact_link",
        "selected_oracle",
        "proposed_oracle",
        "owner",
        "severity",
        "lowest_test_layer",
        "browser_coverage",
        "regression",
    }
    assert {"parser", "route", "seeded-workflow", "browser", "accepted-gap"} <= triage_categories
    assert bank["triage_rule"]["accepted_gap_required_fields"] == [
        "owner",
        "severity",
        "risk",
        "target_date_or_phase",
        "reason",
        "temporary_workaround",
        "blocking_status",
    ]

    for entry in bank["prompts"]:
        assert required <= set(entry)
        assert entry["prompt"] == entry["source_prompt"]
        assert entry["observed_failure"]
        assert entry["expected_behavior"]
        assert entry["owner"]
        assert entry["severity"] in severities
        assert entry["lowest_test_layer"] in {"parser", "route", "seeded-workflow", "mocked-browser", "seeded-browser"}
        assert isinstance(entry["browser_coverage"], bool)
        assert set(entry["coverage"]) <= allowed_coverage
        if entry["browser_coverage"]:
            assert {"mocked-browser", "seeded-browser"} & set(entry["coverage"])
        assert "accepted-gap" not in entry["coverage"]
