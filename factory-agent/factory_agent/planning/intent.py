from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Literal

from .tool_intent_profile import load_generated_vocabulary


IntentKind = Literal["conversation", "unsupported", "operations"]
IntentAction = Literal["create", "update", "approval", "read", "delete"] | None


_GREETING_RE = re.compile(
    r"^\s*(?:hi|hello|hey|yo|good morning|good afternoon|good evening|thanks|thank you)\b",
    re.IGNORECASE,
)
_QUESTION_RE = re.compile(
    r"\b(?:what|how|why|when|where|which|who|meaning|definition|describe|explain|functions|framework|standard|policy|procedure|sop|loto|csf|ppe)\b",
    re.IGNORECASE,
)
_ACTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("approval", re.compile(r"\b(?:approve|reject|approval|approvals|pending approval|pending approvals)\b", re.IGNORECASE)),
    ("create", re.compile(r"\b(?:create|new|add|open)\b", re.IGNORECASE)),
    ("update", re.compile(r"\b(?:update|set|change|assign|record|apply|run|reschedule|move)\b", re.IGNORECASE)),
    ("delete", re.compile(r"\b(?:delete|remove)\b", re.IGNORECASE)),
    (
        "read",
        re.compile(
            r"\b(?:assist|candidate|check|delay|describe|explain|explosion|forecast|get|find|inspect|list|lookup|preview|rank|read|readiness|report|reports|risk|show|shortage|slots?|status|suggestion|timeout|view)\b",
            re.IGNORECASE,
        ),
    ),
]


@dataclass(frozen=True)
class IntentAssessment:
    kind: IntentKind
    action: IntentAction
    entity: str | None
    confidence: float
    reply: str | None = None


def _entity_tokens() -> set[str]:
    return set(load_generated_vocabulary().entity_tokens)


def _plural_variants(token: str) -> set[str]:
    variants = {token}
    if token.endswith("y"):
        variants.add(token[:-1] + "ies")
    elif token.endswith("ss"):
        variants.add(token + "es")
    else:
        variants.add(token + "s")
    return variants


def _detect_entity(text: str) -> str | None:
    tokens = {match.group(0).lower() for match in re.finditer(r"[a-zA-Z0-9]+", text or "")}
    for entity in sorted(_entity_tokens(), key=len, reverse=True):
        if tokens & _plural_variants(entity):
            return entity
    return None


def assess_intent(text: str) -> IntentAssessment:
    raw = (text or "").strip()
    lower = raw.lower()
    if not raw:
        return IntentAssessment(
            kind="conversation",
            action=None,
            entity=None,
            confidence=0.99,
            reply="Hi - tell me what factory operations request you want to run, and I will map it to the available tools.",
        )

    if _GREETING_RE.search(raw):
        return IntentAssessment(
            kind="conversation",
            action=None,
            entity=None,
            confidence=0.98,
            reply="Hi - tell me what factory operations request you want to run, and I will map it to the available tools.",
        )

    matched_actions = {candidate for candidate, pattern in _ACTION_PATTERNS if pattern.search(raw)}
    action: IntentAction = None
    if matched_actions:
        if {"create", "update", "delete"} & matched_actions:
            for candidate in ("create", "update", "delete", "read"):
                if candidate in matched_actions:
                    action = candidate  # type: ignore[assignment]
                    break
        else:
            for candidate in ("approval", "read"):
                if candidate in matched_actions:
                    action = candidate  # type: ignore[assignment]
                    break

    entity = _detect_entity(raw)

    if action or entity or _QUESTION_RE.search(raw):
        confidence = 0.92 if (action and entity) else 0.75
        return IntentAssessment(kind="operations", action=action, entity=entity, confidence=confidence, reply=None)

    token_count = len([tok for tok in re.split(r"\s+", lower) if tok])
    if token_count <= 4:
        return IntentAssessment(
            kind="conversation",
            action=None,
            entity=None,
            confidence=0.7,
            reply="Tell me the factory operations request you want to run, including the resource and any identifier or filter.",
        )

    return IntentAssessment(
        kind="operations",
        action=None,
        entity=None,
        confidence=0.5,
        reply=None,
    )
