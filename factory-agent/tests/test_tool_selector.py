import pytest

from agent.config import Settings
from agent.schemas import ToolInfo
from agent.tool_selector import ToolSelector


def _settings(**overrides):
    base = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        redis_url=None,
        go_api_base_url="http://testserver",
        worker_count=1,
        session_queue_size=10,
        max_plan_steps=10,
        max_session_steps=50,
        max_replans=5,
        max_llm_calls=20,
        max_session_duration_s=1800,
        http_timeout_s=2.0,
    )
    values = base.__dict__.copy()
    values.update(overrides)
    return Settings(**values)


@pytest.mark.asyncio
async def test_selector_prefers_canonical_create_endpoint_for_generic_create_intent():
    selector = ToolSelector(_settings(tool_selector_backend="retrieval", tool_selector_top_k=5))
    tools = {
        "post__machines": ToolInfo(
            name="post__machines",
            description="Create a machine",
            endpoint="/machines",
            method="POST",
            input_schema={
                "type": "object",
                "properties": {
                    "machine_id": {"type": "string"},
                    "machine_name": {"type": "string"},
                    "machine_type": {"type": "string"},
                },
                "required": ["machine_id", "machine_name", "machine_type"],
            },
            body_fields=["machine_id", "machine_name", "machine_type"],
            required_body_fields=["machine_id", "machine_name", "machine_type"],
            is_read_only=False,
            requires_approval=True,
            capability_tags=["machine", "create"],
        ),
        "post__machines_downtime": ToolInfo(
            name="post__machines_downtime",
            description="Record downtime",
            endpoint="/machines/downtime",
            method="POST",
            input_schema={
                "type": "object",
                "properties": {"machine_id": {"type": "string"}},
                "required": ["machine_id"],
            },
            body_fields=["machine_id"],
            required_body_fields=["machine_id"],
            is_read_only=False,
            requires_approval=True,
            capability_tags=["machine", "create", "downtime"],
        ),
    }

    selected = await selector.select_tools(intent="create new machine", tools_by_name=tools, mode="normal", max_tools=10)
    assert selected.backend_used == "retrieval"
    assert selected.tool_names[0] == "post__machines"


@pytest.mark.asyncio
async def test_selector_plan_mode_keeps_read_only_candidates():
    selector = ToolSelector(_settings(tool_selector_backend="retrieval", tool_selector_top_k=5))
    tools = {
        "get__machines": ToolInfo(
            name="get__machines",
            description="List machines",
            endpoint="/machines",
            method="GET",
            input_schema={"type": "object", "properties": {}},
            is_read_only=True,
            requires_approval=False,
            capability_tags=["machine", "list"],
        ),
        "post__machines": ToolInfo(
            name="post__machines",
            description="Create a machine",
            endpoint="/machines",
            method="POST",
            input_schema={"type": "object", "properties": {"machine_name": {"type": "string"}}, "required": ["machine_name"]},
            body_fields=["machine_name"],
            required_body_fields=["machine_name"],
            is_read_only=False,
            requires_approval=True,
            capability_tags=["machine", "create"],
        ),
    }

    selected = await selector.select_tools(intent="create new machine", tools_by_name=tools, mode="plan", max_tools=10)
    assert selected.tool_names == ["get__machines"]


def test_selector_compact_index_contains_name_and_summary():
    selector = ToolSelector(_settings())
    tools = {
        "post__machines": ToolInfo(
            name="post__machines",
            description="Create a machine",
            endpoint="/machines",
            method="POST",
            input_schema={"type": "object", "properties": {"machine_name": {"type": "string"}}, "required": ["machine_name"]},
            body_fields=["machine_name"],
            required_body_fields=["machine_name"],
            is_read_only=False,
            requires_approval=True,
            capability_tags=["machine", "create"],
        )
    }

    compact = selector.build_compact_tool_index(tools)
    assert len(compact) == 1
    assert compact[0]["name"] == "post__machines"
    assert "required: machine_name" in compact[0]["summary"]


@pytest.mark.asyncio
async def test_selector_prefers_specialized_report_endpoint_over_entity_insight():
    selector = ToolSelector(_settings(tool_selector_backend="retrieval", tool_selector_top_k=5))
    tools = {
        "get__reports_machine-utilization": ToolInfo(
            name="get__reports_machine-utilization",
            description="Machine utilization",
            endpoint="/reports/machine-utilization",
            method="GET",
            input_schema={"type": "object", "properties": {}},
            is_read_only=True,
            requires_approval=False,
            capability_tags=["machine", "list", "utilization"],
        ),
        "get__machines_utilization": ToolInfo(
            name="get__machines_utilization",
            description="Get machine utilization",
            endpoint="/machines/utilization",
            method="GET",
            input_schema={"type": "object", "properties": {}},
            is_read_only=True,
            requires_approval=False,
            capability_tags=["machine", "list", "utilization"],
        ),
    }

    selected = await selector.select_tools(
        intent="show machine utilization report",
        tools_by_name=tools,
        mode="normal",
        max_tools=10,
    )

    assert selected.tool_names[0] == "get__reports_machine-utilization"


@pytest.mark.asyncio
async def test_selector_adds_delete_preflight_companion():
    selector = ToolSelector(_settings(tool_selector_backend="retrieval", tool_selector_top_k=1))
    tools = {
        "delete__jobs_{id}": ToolInfo(
            name="delete__jobs_{id}",
            description="Delete a job",
            endpoint="/jobs/{id}",
            method="DELETE",
            input_schema={"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]},
            is_read_only=False,
            requires_approval=True,
            capability_tags=["job", "delete"],
        ),
        "get__jobs_{id}": ToolInfo(
            name="get__jobs_{id}",
            description="Get a job",
            endpoint="/jobs/{id}",
            method="GET",
            input_schema={"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]},
            is_read_only=True,
            requires_approval=False,
            capability_tags=["job", "lookup"],
        ),
    }

    selected = await selector.select_tools(
        intent="delete job JOB-1",
        tools_by_name=tools,
        mode="normal",
        max_tools=10,
    )

    assert selected.tool_names[:2] == ["delete__jobs_{id}", "get__jobs_{id}"]
