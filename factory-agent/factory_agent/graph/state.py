from __future__ import annotations

from typing import Any, TypedDict

from pydantic import BaseModel, Field

from ..schemas import PlanBinding, PlanDraft, ToolInfo


class AgentPlanStep(BaseModel):
    tool_name: str
    args: dict[str, Any] = Field(default_factory=dict)
    evidence: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.0
    missing_required: list[str] = Field(default_factory=list)
    depends_on: list[int] = Field(default_factory=list)
    execution_mode: str = "single"
    bindings: list[PlanBinding] = Field(default_factory=list)


class AgentPlanOutput(BaseModel):
    plan_explanation: str
    risk_summary: str
    steps: list[AgentPlanStep] = Field(default_factory=list)
    clarification: str | None = None


class AgentState(TypedDict, total=False):
    session_id: str | None
    intent: str
    messages: list[dict[str, Any]]
    context: dict[str, Any]
    scoped_tools: list[ToolInfo]
    tool_cards: list[dict[str, Any]]
    pending_tool_call: dict[str, Any] | None
    approved_args: dict[str, Any]
    tool_results: list[dict[str, Any]]
    raw_plan: AgentPlanOutput | None
    draft: PlanDraft | None
    intent_contract: dict[str, Any] | None
    risk_summary: str | None
    clarification: str | None
    final_response: str | None
    errors: list[str]
