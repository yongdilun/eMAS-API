from __future__ import annotations

from typing import Any

from ...planning.intent import intents_to_state_payload, split_user_intents
from ..state import AgentState, user_query_text


def input_layer_node(state: AgentState) -> dict[str, Any]:
    """Normalize canonical query fields before intent extraction (Phase 2)."""
    q = user_query_text(state)
    out: dict[str, Any] = {"status": "intent_split_pending"}
    if q and not str(state.get("original_query") or "").strip():
        out["original_query"] = q
    return out


def intent_splitter_node(state: AgentState) -> dict[str, Any]:
    """Populate ``intents`` via dumb splitter; never rejects incomplete input."""
    q = user_query_text(state)
    intents = split_user_intents(q)
    payload = intents_to_state_payload(intents)
    first: dict[str, Any] | None = payload[0] if payload else None
    return {
        "intents": payload,
        "current_intent": first,
        "status": "planning",
    }
