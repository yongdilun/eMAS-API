from __future__ import annotations

from langgraph.graph import END, StateGraph

from ..config import Settings
from .errors import LangGraphPlannerError
from .nodes import (
    input_layer_node,
    intent_splitter_node,
    make_reason_node,
    make_validate_node,
    prepare_node,
)
from .state import AgentState


def compile_planner_graph(settings: Settings):
    try:
        import langgraph.graph  # noqa: F401 — verify dependency at compile time
    except Exception as exc:
        raise LangGraphPlannerError("langgraph is required for the planner graph.") from exc

    graph = StateGraph(AgentState)
    graph.add_node("input_layer", input_layer_node)
    graph.add_node("intent_splitter", intent_splitter_node)
    graph.add_node("prepare", prepare_node)
    graph.add_node("reason", make_reason_node(settings))
    graph.add_node("validate", make_validate_node(settings))
    graph.set_entry_point("input_layer")
    graph.add_edge("input_layer", "intent_splitter")
    graph.add_edge("intent_splitter", "prepare")
    graph.add_edge("prepare", "reason")
    graph.add_edge("reason", "validate")
    graph.add_edge("validate", END)
    return graph.compile()
