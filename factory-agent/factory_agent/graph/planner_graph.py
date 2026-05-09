from __future__ import annotations

from typing import Any

from ..config import Settings
from ..schemas import PlanDraft, ToolInfo
from .builder import compile_planner_graph
from .errors import LangGraphPlannerClarification, LangGraphPlannerError
from .state import AgentState


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
        state: AgentState = {
            "session_id": str((context or {}).get("session_id") or "") or None,
            "intent": intent,
            "messages": list((context or {}).get("messages") or []),
            "context": context or {},
            "scoped_tools": scoped_tools,
            "pending_tool_call": None,
            "approved_args": {},
            "tool_results": [],
            "errors": [],
        }
        result = await graph.ainvoke(state)
        clarification = result.get("clarification")
        if clarification:
            raise LangGraphPlannerClarification(str(clarification))
        draft = result.get("draft")
        if not isinstance(draft, PlanDraft):
            raise LangGraphPlannerError("LangGraph planner did not return a validated PlanDraft.")
        return draft, result.get("intent_contract") or {"intent": intent, "backend": "langgraph", "steps": []}
