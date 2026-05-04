from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Literal


IntentKind = Literal["conversation", "unsupported", "operations"]
IntentAction = Literal["create", "update", "approval", "read", "delete"] | None


_GREETING_RE = re.compile(
    r"^\s*(?:hi|hello|hey|yo|good morning|good afternoon|good evening|thanks|thank you)\b",
    re.IGNORECASE,
)
_ACTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("approval", re.compile(r"\b(?:approve|reject|approval|approvals|pending approval|pending approvals)\b", re.IGNORECASE)),
    ("create", re.compile(r"\b(?:create|new|add|open)\b", re.IGNORECASE)),
    ("update", re.compile(r"\b(?:update|set|change|assign|record|apply|run|reschedule|move)\b", re.IGNORECASE)),
    ("delete", re.compile(r"\b(?:delete|remove)\b", re.IGNORECASE)),
    ("read", re.compile(r"\b(?:assist|candidate|check|explain|explosion|forecast|get|find|inspect|list|lookup|preview|rank|readiness|report|reports|show|status|suggestion|view)\b", re.IGNORECASE)),
]
_ENTITY_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("approval", re.compile(r"\b(?:approval|approvals)\b", re.IGNORECASE)),
    ("machine", re.compile(r"\b(?:machine|machines)\b", re.IGNORECASE)),
    ("job", re.compile(r"\b(?:job|jobs|job-step|job-steps|schedule|scheduling|slot|slots|step|steps)\b", re.IGNORECASE)),
    ("inventory", re.compile(r"\b(?:inventory|material|materials|stock|arrival|arrivals)\b", re.IGNORECASE)),
    ("product", re.compile(r"\b(?:product|products)\b", re.IGNORECASE)),
    ("proposal", re.compile(r"\b(?:proposal|proposals)\b", re.IGNORECASE)),
]


@dataclass(frozen=True)
class IntentAssessment:
    kind: IntentKind
    action: IntentAction
    entity: str | None
    confidence: float
    reply: str | None = None


def assess_intent(text: str) -> IntentAssessment:
    raw = (text or "").strip()
    lower = raw.lower()
    if not raw:
        return IntentAssessment(
            kind="conversation",
            action=None,
            entity=None,
            confidence=0.99,
            reply="Hi — I can help with machines, jobs, inventory, and approvals.",
        )

    if _GREETING_RE.search(raw):
        return IntentAssessment(
            kind="conversation",
            action=None,
            entity=None,
            confidence=0.98,
            reply="Hi — I can help with factory operations like machine status, job progress, inventory, and approvals.",
        )

    action: IntentAction = None
    for candidate, pattern in _ACTION_PATTERNS:
        if pattern.search(raw):
            action = candidate  # type: ignore[assignment]
            break

    entity = next((candidate for candidate, pattern in _ENTITY_PATTERNS if pattern.search(raw)), None)

    if action or entity:
        confidence = 0.92 if action and entity else 0.75
        return IntentAssessment(kind="operations", action=action, entity=entity, confidence=confidence, reply=None)

    token_count = len([tok for tok in re.split(r"\s+", lower) if tok])
    if token_count <= 4:
        return IntentAssessment(
            kind="conversation",
            action=None,
            entity=None,
            confidence=0.7,
            reply="I’m here to help with factory operations. Try something like `Check machine 5 status` or `Show pending approvals`.",
        )

    return IntentAssessment(
        kind="unsupported",
        action=None,
        entity=None,
        confidence=0.55,
        reply="I couldn’t map that to a factory operation yet. Try asking about machines, jobs, inventory, or approvals.",
    )
