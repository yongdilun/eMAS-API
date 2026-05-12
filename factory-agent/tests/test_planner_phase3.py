"""Phase 3: planner loop guard and reducers."""

from __future__ import annotations

from factory_agent.graph.nodes.planner_loop import decision_guard_node
from factory_agent.graph.state import AgentState


def test_decision_guard_blocks_hard_constraint_mismatch():
    state: AgentState = {
        "original_query": "Use machine M-001",
        "intent": "Use machine M-001",
        "messages": [],
        "scoped_tools": [],
        "context": {},
        "current_intent": {
            "intent_id": "i1",
            "description": "check machine",
            "explicit_constraints": [
                {"field": "machine_id", "operator": "=", "value": "M-001", "strength": "hard"},
            ],
            "status": "in_progress",
        },
        "pending_decision": {
            "intent_id": "i1",
            "kind": "domain_tool",
            "tool_calls": [{"tool_name": "get__machines", "args": {"machine_id": "M-002"}}],
            "decision_summary": "wrong id",
        },
    }
    out = decision_guard_node(state)
    assert out["next_route"] == "continue_planner"
    pd = out.get("pending_decision")
    assert isinstance(pd, dict)
    assert pd.get("violates_constraints") is True
    assert pd.get("tool_calls") == []


def test_decision_guard_passes_matching_constraint():
    state: AgentState = {
        "original_query": "Use machine M-001",
        "intent": "Use machine M-001",
        "messages": [],
        "scoped_tools": [],
        "context": {},
        "current_intent": {
            "intent_id": "i1",
            "description": "check machine",
            "explicit_constraints": [
                {"field": "machine_id", "operator": "=", "value": "M-001", "strength": "hard"},
            ],
            "status": "in_progress",
        },
        "pending_decision": {
            "intent_id": "i1",
            "kind": "domain_tool",
            "tool_calls": [{"tool_name": "get__machines", "args": {"machine_id": "M-001"}}],
            "decision_summary": "ok",
        },
    }
    out = decision_guard_node(state)
    assert out["next_route"] == "tool_execution"
