from __future__ import annotations

from factory_agent.persistence.models import Message as MessageRow
from factory_agent.persistence.models import Session as SessionRow
from factory_agent.schemas import MessageResponse, SessionResponse


def normalize_session_name(name: str | None) -> str | None:
    normalized = (name or "").strip()
    return normalized or None


def session_to_response(session: SessionRow) -> SessionResponse:
    return SessionResponse(
        session_id=session.session_id,
        user_id=session.user_id,
        name=normalize_session_name(getattr(session, "name", None)),
        status=session.status,
        current_intent=session.current_intent,
        plan_id=session.plan_id,
        operation_id=session.plan_id,
        plan_version=session.plan_version or 0,
        plan_hash=session.plan_hash,
        current_step_index=session.current_step_index or 0,
        step_count=session.step_count or 0,
        replan_count=session.replan_count or 0,
        llm_call_count=session.llm_call_count or 0,
        session_started_at=session.session_started_at,
        replan_context=session.replan_context,
        pending_user_message=session.pending_user_message,
        created_at=session.created_at,
        updated_at=session.updated_at,
        completed_at=session.completed_at,
        error=session.error,
    )


def message_to_response(message: MessageRow) -> MessageResponse:
    return MessageResponse(
        message_id=message.message_id,
        session_id=message.session_id,
        role=message.role,
        content=message.content,
        mode=(getattr(message, "mode", None) or "normal"),
        created_at=message.created_at,
        step_id=message.step_id,
        tool_name=message.tool_name,
    )
