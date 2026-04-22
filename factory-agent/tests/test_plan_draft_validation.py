import pytest
from pydantic import ValidationError

from agent.schemas import PlanDraft, PlanStepDraft


def test_plan_draft_requires_non_empty_plan_explanation():
    with pytest.raises(ValidationError):
        PlanDraft(
            plan_explanation="   ",
            risk_summary="safe",
            steps=[PlanStepDraft(step_index=0, tool_name="get__machines", args={})],
        )


def test_plan_draft_requires_non_empty_risk_summary():
    with pytest.raises(ValidationError):
        PlanDraft(
            plan_explanation="Collect machine data",
            risk_summary="",
            steps=[PlanStepDraft(step_index=0, tool_name="get__machines", args={})],
        )
