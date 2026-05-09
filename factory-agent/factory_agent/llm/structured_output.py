"""Validate and coerce planner JSON into structured plan output."""

from __future__ import annotations

from typing import Any

from ..graph.planner_graph_helpers import _normalize_plan_dict
from ..graph.state import AgentPlanOutput


def parse_agent_plan_output(parsed: dict[str, Any]) -> AgentPlanOutput:
    normalized = _normalize_plan_dict(parsed)
    return AgentPlanOutput.model_validate(normalized)
