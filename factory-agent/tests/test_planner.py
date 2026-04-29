import pytest

from agent.config import Settings
from agent.planner import (
    LangChainPlannerBackend,
    LegacyPlannerBackend,
    PlannerAdapter,
    PlannerBackendError,
    PlannerClarificationError,
    PlannerConfirmationRequired,
)
from agent.reasoning_pipeline import ToolSelectionDecision
from agent.schemas import ToolInfo
from agent.tool_registry import ToolRegistry


def _settings() -> Settings:
    return Settings(
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
        planner_backend="legacy",
        planner_fallback_to_legacy=True,
    )


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


@pytest.mark.asyncio
async def test_legacy_planner_prefills_enum_backed_optional_filters():
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
        tool_selector_backend="retrieval",
    )
    planner = LegacyPlannerBackend(settings)
    tool = ToolInfo(
        name="get__machines",
        description="List machines",
        endpoint="/machines",
        method="GET",
        input_schema={
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["idle", "running", "maintenance", "offline"]},
                "machine_type": {"type": "string"},
            },
        },
        is_read_only=True,
        requires_approval=False,
        side_effect_level="NONE",
        is_concurrency_safe=True,
        is_strongly_idempotent=False,
        capability_tags=["machine", "list"],
    )

    result = await planner.generate_plan(
        intent="find all running machine",
        scoped_tools=[tool],
    )

    assert result.draft.steps[0].tool_name == "get__machines"
    assert result.draft.steps[0].args["status"] == "running"


@pytest.mark.asyncio
async def test_legacy_planner_clarifies_invalid_llm_optional_enum_args(monkeypatch):
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
    )
    planner = LegacyPlannerBackend(settings)
    tool = ToolInfo(
        name="get__machines",
        description="List machines",
        endpoint="/machines",
        method="GET",
        input_schema={
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["idle", "running", "maintenance", "offline"]},
                "limit": {"type": "integer"},
            },
        },
        is_read_only=True,
        requires_approval=False,
        side_effect_level="NONE",
        is_concurrency_safe=True,
        is_strongly_idempotent=False,
        capability_tags=["machine", "list"],
    )

    async def _fake_select_tool(*, intent, clause, candidates):
        del intent, clause, candidates
        return ToolSelectionDecision(
            tool_name="get__machines",
            args={"status": "broke", "limit": 100},
            confidence=0.9,
            missing_args=[],
            reason="bad enum from llm",
        )

    monkeypatch.setattr(planner._reasoning, "select_tool", _fake_select_tool)

    with pytest.raises(PlannerClarificationError) as exc:
        await planner.generate_plan(
            intent="find all broke machine",
            scoped_tools=[tool],
        )

    message = str(exc.value)
    assert 'could not safely map "broke"' in message
    assert "Allowed status values are: idle, running, maintenance, offline." in message


@pytest.mark.asyncio
async def test_legacy_planner_clarifies_unknown_term_against_likely_enum_field(monkeypatch):
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
    )
    planner = LegacyPlannerBackend(settings)
    tool = ToolInfo(
        name="get__machines",
        description="List machines",
        endpoint="/machines",
        method="GET",
        input_schema={
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["idle", "running", "maintenance", "offline"]},
            },
        },
        is_read_only=True,
        requires_approval=False,
        side_effect_level="NONE",
        is_concurrency_safe=True,
        is_strongly_idempotent=False,
        capability_tags=["machine", "list"],
    )

    async def _fake_classify_unknown_term(*, clause, term, entity, tool):
        del clause, entity, tool
        assert term == "broke"
        return {"field_name": "status", "confidence": 0.91, "reason": "likely machine status"}

    monkeypatch.setattr(planner._reasoning, "classify_unknown_term", _fake_classify_unknown_term)

    with pytest.raises(PlannerClarificationError) as exc:
        await planner.generate_plan(
            intent="find all broke machine",
            scoped_tools=[tool],
        )

    message = str(exc.value)
    assert 'could not safely map "broke"' in message
    assert "Allowed status values are: idle, running, maintenance, offline." in message


@pytest.mark.asyncio
async def test_legacy_planner_clarifies_unknown_term_without_schema_match(monkeypatch):
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
    )
    planner = LegacyPlannerBackend(settings)
    tool = ToolInfo(
        name="get__machines",
        description="List machines",
        endpoint="/machines",
        method="GET",
        input_schema={
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["idle", "running", "maintenance", "offline"]},
            },
        },
        is_read_only=True,
        requires_approval=False,
        side_effect_level="NONE",
        is_concurrency_safe=True,
        is_strongly_idempotent=False,
        capability_tags=["machine", "list"],
    )

    async def _fake_classify_unknown_term(*, clause, term, entity, tool):
        del clause, entity, tool
        assert term == "bsn"
        return {"field_name": None, "confidence": 0.0, "reason": "no clear schema field"}

    monkeypatch.setattr(planner._reasoning, "classify_unknown_term", _fake_classify_unknown_term)

    with pytest.raises(PlannerClarificationError) as exc:
        await planner.generate_plan(
            intent="find all bsn machine",
            scoped_tools=[tool],
        )

    assert 'couldn\'t match "bsn" to any supported machine field or filter' in str(exc.value).lower()


@pytest.mark.asyncio
async def test_legacy_planner_negative_memory_blocks_repeated_bad_enum_mapping(monkeypatch):
    planner = LegacyPlannerBackend(_settings())
    tool = ToolInfo(
        name="get__machines",
        description="List machines",
        endpoint="/machines",
        method="GET",
        input_schema={
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["idle", "running", "maintenance", "offline"]},
            },
        },
        is_read_only=True,
        requires_approval=False,
        side_effect_level="NONE",
        is_concurrency_safe=True,
        is_strongly_idempotent=False,
        capability_tags=["machine", "list"],
    )

    async def _fake_classify_unknown_term(*, clause, term, entity, tool):
        del clause, entity, tool
        assert term == "asasidn"
        return {"field_name": "status", "confidence": 0.91, "reason": "looks like status"}

    monkeypatch.setattr(planner._reasoning, "classify_unknown_term", _fake_classify_unknown_term)

    with pytest.raises(PlannerClarificationError) as exc:
        await planner.generate_plan(
            intent="find all asasidn machine",
            scoped_tools=[tool],
            context={
                "intent_memory": {
                    "negative_bindings": [
                        {
                            "term": "asasidn",
                            "normalized_term": "asasidn",
                            "entity": "machine",
                            "field": "status",
                        }
                    ]
                }
            },
        )

    assert 'couldn\'t match "asasidn" to any supported machine field or filter' in str(exc.value).lower()


def _machine_list_tool_with_filters() -> ToolInfo:
    return ToolInfo(
        name="get__machines",
        description="List machines",
        endpoint="/machines",
        method="GET",
        input_schema={
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["idle", "running", "maintenance", "offline"]},
                "machine_type": {"type": "string"},
                "location": {"type": "string"},
                "limit": {"type": "integer"},
                "offset": {"type": "integer"},
                "sort_by": {"type": "string"},
                "sort_dir": {"type": "string", "enum": ["asc", "desc"]},
                "fields": {"type": "string"},
            },
        },
        query_params=["status", "machine_type", "location", "limit", "offset", "sort_by", "sort_dir", "fields"],
        param_sources={
            "status": "query",
            "machine_type": "query",
            "location": "query",
            "limit": "query",
            "offset": "query",
            "sort_by": "query",
            "sort_dir": "query",
            "fields": "query",
        },
        is_read_only=True,
        requires_approval=False,
        side_effect_level="NONE",
        is_concurrency_safe=True,
        is_strongly_idempotent=False,
        capability_tags=["machine", "list"],
    )


@pytest.mark.asyncio
async def test_legacy_planner_maps_paint_shop_location_filter():
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
        tool_selector_backend="retrieval",
    )
    planner = LegacyPlannerBackend(settings)

    with pytest.raises(PlannerConfirmationRequired) as exc:
        await planner.generate_plan(
            intent="find all Paint Shop machine",
            scoped_tools=[_machine_list_tool_with_filters()],
        )

    assert exc.value.confirmation["kind"] == "predicate_field_confirmation"
    assert exc.value.confirmation["raw_term"] == "Paint Shop"


@pytest.mark.asyncio
async def test_legacy_planner_maps_in_paint_shop_location_filter():
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
        tool_selector_backend="retrieval",
    )
    planner = LegacyPlannerBackend(settings)

    result = await planner.generate_plan(
        intent="machines in Paint Shop",
        scoped_tools=[_machine_list_tool_with_filters()],
    )

    assert result.draft.steps[0].args == {"location": "Paint Shop"}


@pytest.mark.asyncio
async def test_legacy_planner_rejects_vague_free_text_filter():
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
    )
    planner = LegacyPlannerBackend(settings)

    with pytest.raises(PlannerClarificationError) as exc:
        await planner.generate_plan(
            intent="find close machines",
            scoped_tools=[_machine_list_tool_with_filters()],
        )

    assert "couldn't match" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_legacy_planner_requests_confirmation_for_ambiguous_cnc_filter():
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
    )
    planner = LegacyPlannerBackend(settings)

    with pytest.raises(PlannerConfirmationRequired) as exc:
        await planner.generate_plan(
            intent="find all CNC machine",
            scoped_tools=[_machine_list_tool_with_filters()],
        )

    assert exc.value.confirmation["kind"] == "predicate_field_confirmation"
    assert {opt["field"] for opt in exc.value.confirmation["options"]} >= {"machine_type", "location"}
