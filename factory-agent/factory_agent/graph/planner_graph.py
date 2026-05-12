from __future__ import annotations

from typing import Any

from ..config import Settings
from ..schemas import PlanDraft, ToolInfo
from .builder import compile_planner_graph
from .errors import LangGraphPlannerClarification, LangGraphPlannerError
from .state import AgentState, normalize_graph_messages


def _initial_planner_state(
    *,
    intent: str,
    scoped_tools: list[ToolInfo],
    context: dict[str, Any] | None,
) -> AgentState:
    ctx = context or {}
    return {
        "session_id": str(ctx.get("session_id") or "") or None,
        "original_query": intent,
        "intent": intent,
        "messages": normalize_graph_messages(ctx.get("messages")),
        "context": ctx,
        "scoped_tools": scoped_tools,
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


class LangGraphPlanner:
    def __init__(self, settings: Settings):
        self._settings = settings

    async def generate(
        self,
        *,
        intent: str,
        scoped_tools: list[ToolInfo],
        context: dict[str, Any] | None = None,
    ) -> tuple[PlanDraft, dict[str, Any]]:
        graph = compile_planner_graph(self._settings)
        state: AgentState = _initial_planner_state(intent=intent, scoped_tools=scoped_tools, context=context)
        result = await graph.ainvoke(state)
        clarification = result.get("clarification")
        if clarification:
            raise LangGraphPlannerClarification(str(clarification))
        draft = result.get("draft")
        if not isinstance(draft, PlanDraft):
            raise LangGraphPlannerError("LangGraph planner did not return a validated PlanDraft.")
        return draft, result.get("intent_contract") or {
            "intent": intent,
            "backend": "langgraph",
            "steps": [],
        }
