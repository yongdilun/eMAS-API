import pytest

from agent.config import Settings
from agent.planner import LangChainPlannerBackend, PlannerAdapter, PlannerBackendError
from agent.schemas import ToolInfo
from agent.tool_registry import ToolRegistry


@pytest.mark.asyncio
async def test_planner_adapter_langchain_backend_falls_back_to_legacy_when_unavailable(monkeypatch):
    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        redis_url=None,
        go_api_base_url="http://testserver",
        worker_count=0,
        session_queue_size=10,
        max_plan_steps=10,
        max_session_steps=50,
        max_replans=5,
        max_llm_calls=20,
        max_session_duration_s=1800,
        http_timeout_s=1.0,
        planner_backend="langchain",
        planner_fallback_to_legacy=True,
    )
    adapter = PlannerAdapter(settings=settings, tool_registry=ToolRegistry())
    tool = ToolInfo(
        name="get__machines_{id}",
        description="get__machines_{id}",
        endpoint="/machines/{id}",
        method="GET",
        input_schema={"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]},
        is_read_only=True,
        requires_approval=False,
        side_effect_level="NONE",
        is_concurrency_safe=True,
        is_strongly_idempotent=False,
        capability_tags=["machine", "status"],
    )

    async def failing_generate_plan(self, *, intent, scoped_tools, context=None, tools_markdown=""):
        del self, intent, scoped_tools, context, tools_markdown
        raise PlannerBackendError("LangChain backend unavailable")

    monkeypatch.setattr(LangChainPlannerBackend, "generate_plan", failing_generate_plan)

    result = await adapter.generate_plan(
        intent="Check machine 5 status",
        scoped_tools=[tool],
        context=None,
    )

    assert result.backend_used == "legacy"
    assert len(result.draft.steps) == 1
    assert result.draft.steps[0].tool_name == "get__machines_{id}"
    assert result.draft.steps[0].args == {"id": "5"}
