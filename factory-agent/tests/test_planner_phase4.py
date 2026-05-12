"""Phase 4: transaction refs, idempotency key, relevance filter, staging."""

from __future__ import annotations

import pytest

from factory_agent.config import get_settings
from factory_agent.graph.http_tool_client import compute_planner_write_idempotency_key
from factory_agent.graph.nodes.tool_pipeline import make_relevance_filter_node, make_tool_execution_node
from factory_agent.graph.nodes.planner_loop import decision_guard_node
from factory_agent.graph.state import AgentState
from factory_agent.schemas import ToolInfo


def test_compute_planner_write_idempotency_key_stable():
    k1 = compute_planner_write_idempotency_key(
        session_id="s1",
        intent_id="i1",
        action_id="a1",
        tool_name="post__jobs",
        args={"title": "x"},
        write_generation=2,
    )
    k2 = compute_planner_write_idempotency_key(
        session_id="s1",
        intent_id="i1",
        action_id="a1",
        tool_name="post__jobs",
        args={"title": "x"},
        write_generation=2,
    )
    k3 = compute_planner_write_idempotency_key(
        session_id="s1",
        intent_id="i1",
        action_id="a1",
        tool_name="post__jobs",
        args={"title": "y"},
        write_generation=2,
    )
    assert k1 == k2
    assert k1 != k3


def test_decision_guard_rejects_forward_ref():
    write_tool = ToolInfo(
        name="post__x",
        description="w",
        endpoint="/x",
        method="POST",
        input_schema={"type": "object"},
        is_read_only=False,
    )
    state: AgentState = {
        "original_query": "q",
        "intent": "q",
        "messages": [],
        "scoped_tools": [write_tool],
        "context": {},
        "current_intent": {"intent_id": "i1", "explicit_constraints": [], "status": "in_progress"},
        "pending_decision": {
            "intent_id": "i1",
            "decision_id": "d1",
            "kind": "domain_tool",
            "tool_calls": [
                {"tool_name": "post__x", "args": {"job_id": "$ref:post__x_0"}},
            ],
        },
    }
    out = decision_guard_node(state)
    assert out["next_route"] == "continue_planner"
    pd = out.get("pending_decision")
    assert isinstance(pd, dict)
    assert pd.get("tool_calls") == []


@pytest.mark.asyncio
async def test_tool_execution_stages_writes_without_http():
    settings = get_settings()
    write_tool = ToolInfo(
        name="post__jobs",
        description="create",
        endpoint="/jobs",
        method="POST",
        input_schema={"type": "object"},
        is_read_only=False,
    )
    node = make_tool_execution_node(settings)
    state: AgentState = {
        "session_id": "sess-1",
        "original_query": "create job",
        "intent": "create job",
        "messages": [],
        "scoped_tools": [write_tool],
        "context": {},
        "write_generation": 0,
        "retrieved_info": {},
        "pending_decision": {
            "intent_id": "i1",
            "decision_id": "d1",
            "kind": "domain_tool",
            "tool_calls": [{"tool_name": "post__jobs", "args": {"title": "J1"}, "tool_call_id": "tc-aaa"}],
        },
    }
    out = await node(state)
    assert out.get("next_route") == "relevance_filter"
    assert out.get("fatal_system_error") is None
    staged = out.get("staged_writes") or []
    assert len(staged) == 1
    assert staged[0].get("tool_name") == "post__jobs"
    assert staged[0].get("idempotency_key")
    assert staged[0].get("output_ref", "").startswith("$ref:")
    assert out.get("pending_relevance_batch")


@pytest.mark.asyncio
async def test_relevance_filter_empty_and_404():
    settings = get_settings()
    rf = make_relevance_filter_node(settings)
    empty = await rf({"pending_relevance_batch": [], "retrieved_info": {}})
    assert empty["next_route"] == "continue_planner"

    state = {
        "original_query": "find machine",
        "intent": "find machine",
        "pending_relevance_batch": [
            {
                "tool_name": "get__machines",
                "tool_call_id": "t1",
                "args": {"id": "x"},
                "result": {"error": "nf"},
                "http_status": 404,
            }
        ],
        "scoped_tools": [
            ToolInfo(
                name="get__machines",
                description="m",
                endpoint="/machines/{id}",
                method="GET",
                input_schema={"type": "object"},
                path_params=["id"],
                is_read_only=True,
            )
        ],
        "retrieved_info": {},
    }
    out = await rf(state)
    assert out["next_route"] == "continue_planner"
    to = out.get("tool_outputs") or []
    assert to and to[0].get("useful") is False
