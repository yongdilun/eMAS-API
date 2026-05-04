from agent.schemas import ToolInfo
from agent.tool_intent_profile import build_tool_intent_profile, profile_match_score, tool_covers_descriptive_terms


def _tool(name: str, description: str, endpoint: str) -> ToolInfo:
    return ToolInfo(
        name=name,
        description=description,
        endpoint=endpoint,
        method="GET",
        input_schema={"type": "object", "properties": {}},
        is_read_only=True,
        requires_approval=False,
    )


def test_profile_derives_endpoint_and_feature_tokens():
    tool = _tool("get__reports_machine-utilization", "Machine utilization", "/reports/machine-utilization")

    profile = build_tool_intent_profile(tool)

    assert profile.endpoint_root == "report"
    assert {"machine", "utilization"} <= set(profile.identity_tokens)
    assert "utilization" in profile.feature_tokens


def test_profile_scores_specialized_endpoint_above_generic_entity():
    specialized = _tool("get__reports_machine-utilization", "Machine utilization", "/reports/machine-utilization")
    generic = _tool("get__machines_utilization", "Get machine utilization", "/machines/utilization")

    assert profile_match_score("show machine utilization report", specialized) > profile_match_score(
        "show machine utilization report",
        generic,
    )


def test_profile_marks_endpoint_descriptive_terms_as_tool_evidence():
    tool = _tool("get__predictive_high-risk-jobs", "List high-risk jobs", "/predictive/high-risk-jobs")

    assert tool_covers_descriptive_terms("show predictive high risk jobs", tool)

