import main  # noqa: F401

from agent.prompting import get_plan_draft_json_schema


def test_plan_draft_json_schema_has_expected_shape():
    schema = get_plan_draft_json_schema()
    assert isinstance(schema, dict)
    assert "properties" in schema
    assert "steps" in schema["properties"]
    assert "plan_explanation" in schema["properties"]
    assert "risk_summary" in schema["properties"]

