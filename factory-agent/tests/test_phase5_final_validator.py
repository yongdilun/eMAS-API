from __future__ import annotations

from factory_agent.config import get_settings
from factory_agent.graph.nodes.validate import make_final_validator_node
from factory_agent.graph.nodes.tool_pipeline import route_after_bundle, route_after_commit, route_after_validate
from factory_agent.schemas import PlanDraft, PlanStepDraft


def _validated_state(**overrides):
    state = {
        "raw_plan": None,
        "draft": PlanDraft(
            plan_explanation="Ready.",
            risk_summary="Review writes.",
            steps=[
                PlanStepDraft(
                    step_index=0,
                    tool_name="post__jobs",
                    args={"machine_id": "M-001"},
                    depends_on=[],
                )
            ],
        ),
        "status": "completed",
        "staged_writes": [
            {
                "intent_id": "i1",
                "decision_id": "d1",
                "tool_call_id": "tc1",
                "tool_name": "post__jobs",
                "args": {"machine_id": "M-001"},
                "output_ref": "$ref:job",
                "idempotency_key": "idem",
                "status": "staged",
            }
        ],
        "decisions": [{"risk_level": "high_risk"}],
        "validation_results": [],
        "tool_outputs": [],
        "repair_attempts": 0,
    }
    state.update(overrides)
    return state


def test_final_validator_commit_409_with_hard_constraint_requests_clarification():
    settings = get_settings()
    node = make_final_validator_node(settings)
    out = node(
        {
            "current_intent": {
                "intent_id": "i1",
                "explicit_constraints": [{"field": "machine_id", "value": "M-001", "strength": "hard"}],
            },
            "last_commit_result": {"ok": False, "http_status": 409, "body": {"error": "conflict"}},
            "tool_outputs": [{"x": 1}],
            "repair_attempts": 0,
        }
    )
    assert out["status"] == "awaiting_clarification"
    assert out.get("clarification")


def test_final_validator_commit_business_failure_routes_repair_with_truncation_cursor():
    settings = get_settings()
    node = make_final_validator_node(settings)
    out = node(
        {
            "current_intent": {"intent_id": "i1", "explicit_constraints": []},
            "last_commit_result": {"ok": False, "http_status": 409, "body": {"error": "conflict"}},
            "tool_outputs": [{"a": 1}, {"a": 2}, {"a": 3}],
            "repair_attempts": 0,
        }
    )
    assert out["next_route"] == "continue_planner"
    assert out["repair_attempts"] == 1
    assert out["tool_outputs_truncated_at"] == 3
    assert out["staged_writes"] == [{"__replace__": True, "value": []}]


def test_final_validator_commit_infra_failure_is_fatal():
    settings = get_settings()
    node = make_final_validator_node(settings)
    out = node(
        {
            "current_intent": {"intent_id": "i1", "explicit_constraints": []},
            "last_commit_result": {"ok": False, "infrastructure": True, "error": "timeout"},
            "repair_attempts": 0,
        }
    )
    assert out["next_route"] == "fatal_end"
    assert str(out.get("fatal_system_error") or "").startswith("FATAL_SYSTEM_ERROR")


def test_write_flow_routes_dry_run_before_commit_or_approval(monkeypatch):
    settings = get_settings()
    node = make_final_validator_node(settings)

    def fake_validate(state):
        return {
            "draft": state["draft"],
            "intent_contract": {"backend": "langgraph", "steps": []},
            "status": "completed",
            "validation_results": [{"ok": True}],
        }

    monkeypatch.setattr("factory_agent.graph.nodes.validate.make_validate_node", lambda settings: fake_validate)
    node = make_final_validator_node(settings)

    out = node(_validated_state(bundle_dry_run_result=None))
    assert out["next_route"] == "bundle_dry_run"
    assert route_after_validate(out) == "bundle_dry_run"
    assert route_after_bundle({"bundle_dry_run_result": {"ok": True}}) == "final_validator"


def test_write_flow_approves_only_after_successful_dry_run(monkeypatch):
    settings = get_settings()

    def fake_validate(state):
        return {
            "draft": state["draft"],
            "intent_contract": {"backend": "langgraph", "steps": []},
            "status": "completed",
            "validation_results": [{"ok": True}],
        }

    monkeypatch.setattr("factory_agent.graph.nodes.validate.make_validate_node", lambda settings: fake_validate)
    monkeypatch.setattr("factory_agent.graph.nodes.validate.interrupt", lambda payload: {"approved": True})
    node = make_final_validator_node(settings)

    out = node(_validated_state(bundle_dry_run_result={"ok": True, "http_status": 200, "body": {}}))
    assert out["next_route"] == "commit"
    assert out["approval_requests"][0]["status"] == "approved"
    assert route_after_validate(out) == "commit"


def test_commit_business_failure_routes_back_to_final_validator():
    assert route_after_commit({"last_commit_result": {"ok": False, "http_status": 409}}) == "final_validator"
