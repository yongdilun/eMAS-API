"""Phase 1: LangGraph AgentState reducers and graph smoke."""

from __future__ import annotations

import operator
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any, TypedDict

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from factory_agent.graph.state import AgentState, normalize_graph_messages, replace_list, replaceable_list_reducer, user_query_text
from factory_agent.schemas import ApprovalResponse, ToolInfo


class _DummyState(TypedDict, total=False):
    messages: Annotated[list[Any], add_messages]
    errors: Annotated[list[str], operator.add]
    tag: str


def _echo_node(state: _DummyState) -> _DummyState:
    return {"errors": ["step-a"], "messages": [AIMessage(content="ack")]}


def _agent_state_append_node(state: AgentState) -> dict[str, Any]:
    return {
        "messages": [AIMessage(content="ack")],
        "tool_outputs": [{"tool_name": "get__x"}],
        "completed_actions": [{"phase": "dummy"}],
        "staged_writes": [{"tool_name": "post__x"}],
        "errors": ["warning"],
        "status": "planning",
        "retrieved_info": {"phase": "append"},
    }


def _agent_state_clear_node(state: AgentState) -> dict[str, Any]:
    return {
        "staged_writes": replace_list(),
        "status": "completed",
        "retrieved_info": {"phase": "clear"},
    }


def test_normalize_graph_messages_coerces_roles():
    raw = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    ]
    msgs = normalize_graph_messages(raw)
    assert [m.type for m in msgs] == ["system", "human", "ai"]
    assert msgs[1].content == "hi"


def test_user_query_text_prefers_original_query():
    assert user_query_text({"original_query": "  q  ", "intent": "legacy"}) == "q"
    assert user_query_text({"intent": "only"}) == "only"
    assert user_query_text({}) == ""


def test_replaceable_list_reducer_can_clear_runtime_buffers():
    assert replaceable_list_reducer([{"old": True}], [{"new": True}]) == [{"old": True}, {"new": True}]
    assert replaceable_list_reducer([{"old": True}], replace_list()) == []


@pytest.mark.asyncio
async def test_stategraph_reducers_append_messages_and_errors():
    graph = StateGraph(_DummyState)
    graph.add_node("n", _echo_node)
    graph.set_entry_point("n")
    graph.add_edge("n", END)
    compiled = graph.compile()

    out = await compiled.ainvoke(
        {
            "messages": [HumanMessage(content="start")],
            "errors": [],
            "tag": "t",
        }
    )
    assert [m.content for m in out["messages"]] == ["start", "ack"]
    assert out["errors"] == ["step-a"]
    assert out["tag"] == "t"


@pytest.mark.asyncio
async def test_agent_state_passes_through_dummy_langgraph_and_reducers():
    graph = StateGraph(AgentState)
    graph.add_node("append", _agent_state_append_node)
    graph.add_node("clear", _agent_state_clear_node)
    graph.set_entry_point("append")
    graph.add_edge("append", "clear")
    graph.add_edge("clear", END)
    compiled = graph.compile()

    out = await compiled.ainvoke(
        {
            "session_id": "s1",
            "original_query": "show x",
            "intent": "show x",
            "messages": [HumanMessage(content="start")],
            "context": {},
            "scoped_tools": [],
            "retrieved_info": {"phase": "initial"},
            "decisions": [],
            "approval_requests": [],
            "validation_results": [],
            "intents": [],
            "working_intents": [],
            "intent_cursor": 0,
            "pending_decision": None,
            "planner_iteration": 0,
            "tool_outputs": [],
            "completed_actions": [],
            "staged_writes": [{"tool_name": "old_write"}],
            "failed_strategies": [],
            "errors": [],
            "status": "init",
            "next_route": None,
            "write_generation": 0,
            "pending_relevance_batch": None,
            "fatal_system_error": None,
            "bundle_dry_run_result": None,
            "last_commit_result": None,
            "idempotency_audit": [],
            "repair_attempts": 0,
            "tool_outputs_truncated_at": 0,
        }
    )

    assert [m.content for m in out["messages"]] == ["start", "ack"]
    assert out["tool_outputs"] == [{"tool_name": "get__x"}]
    assert out["completed_actions"] == [{"phase": "dummy"}]
    assert out["errors"] == ["warning"]
    assert out["staged_writes"] == []
    assert out["status"] == "completed"
    assert out["retrieved_info"] == {"phase": "clear"}


def test_agent_state_type_aliases_with_toolinfo():
    tool = ToolInfo(
        name="get__x",
        description="x",
        endpoint="/x",
        method="GET",
        input_schema={"type": "object", "properties": {}},
        is_read_only=True,
        requires_approval=False,
        side_effect_level="NONE",
        is_concurrency_safe=True,
        is_strongly_idempotent=False,
    )
    sample: AgentState = {
        "original_query": "show x",
        "intent": "show x",
        "messages": [],
        "scoped_tools": [tool],
        "context": {},
        "retrieved_info": {},
        "decisions": [],
        "approval_requests": [],
        "validation_results": [],
        "intents": [],
        "tool_outputs": [],
        "completed_actions": [],
        "staged_writes": [],
        "failed_strategies": [],
        "errors": [],
        "status": "init",
    }
    assert sample["scoped_tools"][0].name == "get__x"


def test_approval_response_accepts_graph_native_approval_subject():
    approval = ApprovalResponse(
        approval_id="a1",
        session_id="s1",
        subject_type="graph",
        plan_id=None,
        step_id=None,
        tool_name="__langgraph_commit__",
        args={"kind": "approval_required", "preview": [{"tool_name": "post__jobs"}]},
        risk_summary="High-risk write bundle requires approval before commit.",
        side_effect_level="HIGH",
        status="PENDING",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        created_at=datetime.now(UTC),
    )
    assert approval.subject_type == "graph"
    assert approval.args["kind"] == "approval_required"
