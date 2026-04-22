from agent.schemas import ToolInfo
from agent.tool_scope import filter_tools_for_intent


def test_tool_scope_forces_approval_tools():
    tools = {
        "get__chatbot_approval_pending": ToolInfo(
            name="get__chatbot_approval_pending",
            description="List pending approvals",
            endpoint="/chatbot/approval/pending",
            method="GET",
            input_schema={"type": "object", "properties": {}},
            is_read_only=True,
            requires_approval=False,
            capability_tags=[],
        ),
        "get__machines": ToolInfo(
            name="get__machines",
            description="List machines",
            endpoint="/machines",
            method="GET",
            input_schema={"type": "object", "properties": {}},
            is_read_only=True,
            requires_approval=False,
            capability_tags=["machine"],
        ),
    }

    scoped = filter_tools_for_intent(intent="show me machine list", tools_by_name=tools, max_tools=5)
    assert "get__chatbot_approval_pending" in scoped.tool_names
    assert "get__machines" in scoped.tool_names


def test_tool_scope_respects_max_tools():
    tools = {}
    for i in range(100):
        tools[f"get__t{i}"] = ToolInfo(
            name=f"get__t{i}",
            description="tool",
            endpoint=f"/t{i}",
            method="GET",
            input_schema={"type": "object", "properties": {}},
            is_read_only=True,
            requires_approval=False,
            capability_tags=["machine"] if i < 50 else [],
        )
    scoped = filter_tools_for_intent(intent="machine", tools_by_name=tools, max_tools=10)
    assert len(scoped.tool_names) <= 10


def test_tool_scope_default_cap_is_30():
    tools = {}
    for i in range(80):
        tools[f"get__machine_{i}"] = ToolInfo(
            name=f"get__machine_{i}",
            description="machine tool",
            endpoint=f"/machines/{i}",
            method="GET",
            input_schema={"type": "object", "properties": {}},
            is_read_only=True,
            requires_approval=False,
            capability_tags=["machine"],
        )
    scoped = filter_tools_for_intent(intent="machine inventory report", tools_by_name=tools)
    assert len(scoped.tool_names) <= 30
