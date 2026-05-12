"""LangGraph / AgentState test fixtures (not a pytest module — name does not use ``test_`` prefix)."""

from __future__ import annotations

from typing import Any

from factory_agent.graph.state import AgentPlanOutput
from factory_agent.schemas import ToolInfo


def stub_agent_state(
    *,
    query: str,
    scoped_tools: list[ToolInfo],
    context: dict[str, Any] | None = None,
    raw_plan: AgentPlanOutput | None = None,
    tool_cards: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Minimal state dict for validate/reason nodes: canonical ``original_query`` + legacy ``intent``."""
    out: dict[str, Any] = {
        "original_query": query,
        "intent": query,
        "context": context or {},
        "scoped_tools": scoped_tools,
    }
    if raw_plan is not None:
        out["raw_plan"] = raw_plan
    if tool_cards is not None:
        out["tool_cards"] = tool_cards
    return out
