from __future__ import annotations

from langgraph.graph import END, StateGraph

from ..config import Settings
from .errors import LangGraphPlannerError
from .nodes import make_reason_node, make_validate_node, prepare_node
from .state import AgentState


def compile_planner_graph(settings: Settings):
    try:
        import langgraph.graph  # noqa: F401 — verify dependency at compile time
    except Exception as exc:
        raise LangGraphPlannerError("langgraph is required for the planner graph.") from exc

    graph = StateGraph(AgentState)
    graph.add_node("prepare", prepare_node)
    graph.add_node("reason", make_reason_node(settings))
    graph.add_node("validate", make_validate_node(settings))
    graph.set_entry_point("prepare")
    graph.add_edge("prepare", "reason")
    graph.add_edge("reason", "validate")
    graph.add_edge("validate", END)
    return graph.compile()
