from __future__ import annotations

import pytest

from factory_agent.config import get_settings
from factory_agent.services.planner_service import PlannerApprovalRequired, PlannerService


class _FakeRegistry:
    def load_tools_markdown(self):
        return None


class _FakePlanner:
    def __init__(self, _settings):
        pass

    async def generate(self, *, intent, scoped_tools, context=None):
        from factory_agent.graph.errors import LangGraphPlannerApprovalRequired

        raise LangGraphPlannerApprovalRequired({"kind": "approval_required", "summary": "approve me"})

    async def resume_after_approval(self, *, session_id: str, approved: bool):
        from factory_agent.schemas import PlanDraft

        return (
            PlanDraft(plan_explanation="ok", risk_summary="ok", steps=[]),
            {"intent": "x", "backend": "langgraph", "steps": []},
        )


@pytest.mark.asyncio
async def test_generate_plan_maps_langgraph_approval_required():
    settings = get_settings()
    svc = PlannerService(settings=settings, tool_registry=_FakeRegistry())  # type: ignore[arg-type]
    PlannerService._langgraph_planner_cls = _FakePlanner
    with pytest.raises(PlannerApprovalRequired):
        await svc.generate_plan(intent="x", scoped_tools=[], context={})


@pytest.mark.asyncio
async def test_resume_after_approval_returns_result():
    settings = get_settings()
    svc = PlannerService(settings=settings, tool_registry=_FakeRegistry())  # type: ignore[arg-type]
    PlannerService._langgraph_planner_cls = _FakePlanner
    out = await svc.resume_after_approval(session_id="s1", approved=True)
    assert out.backend_used == "langgraph"
    assert out.draft.plan_explanation == "ok"
