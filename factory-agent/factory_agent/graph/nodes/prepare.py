from __future__ import annotations

from ..planner_graph_helpers import _tool_cards
from ..state import AgentState


def prepare_node(state: AgentState) -> AgentState:
    scoped_tools = state.get("scoped_tools") or []
    return {"tool_cards": _tool_cards(scoped_tools)}
