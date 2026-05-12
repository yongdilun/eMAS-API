from __future__ import annotations


class LangGraphPlannerError(RuntimeError):
    pass


class LangGraphPlannerClarification(LangGraphPlannerError):
    pass


class LangGraphPlannerApprovalRequired(LangGraphPlannerError):
    def __init__(self, payload: dict):
        super().__init__("Approval is required to continue execution.")
        self.payload = payload
