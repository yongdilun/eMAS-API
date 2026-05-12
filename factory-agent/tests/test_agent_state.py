"""Phase 1: LangGraph AgentState reducers and graph smoke."""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from factory_agent.graph.state import AgentState, normalize_graph_messages, user_query_text
from factory_agent.schemas import ToolInfo


class _DummyState(TypedDict, total=False):
    messages: Annotated[list[Any], add_messages]
    errors: Annotated[list[str], operator.add]
    tag: str


def _echo_node(state: _DummyState) -> _DummyState:
    return {"errors": ["step-a"], "messages": [AIMessage(content="ack")]}


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
