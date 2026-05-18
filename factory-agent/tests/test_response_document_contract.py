from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import pytest
from pydantic import ValidationError

from factory_agent.config import Settings
from factory_agent.orchestration.memory_manager import MemoryManager
from factory_agent.orchestration.session_manager import SessionManager
from factory_agent.persistence.models import Approval, Message, Plan, Session
from factory_agent.registry.tool_registry import ToolRegistry
from factory_agent.schemas import ResponseDocument
from factory_agent.services.session_snapshot_service import SessionSnapshotService


def _settings() -> Settings:
    return Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        redis_url=None,
        go_api_base_url="http://testserver",
        worker_count=0,
        session_queue_size=10,
        max_plan_steps=10,
        max_session_steps=50,
        max_replans=5,
        max_llm_calls=20,
        max_session_duration_s=1800,
        http_timeout_s=1.0,
        checkpoint_enabled=False,
        memory_enabled=False,
        jwt_required=False,
        enforce_tool_registry_health=False,
        auto_repair_tool_registry=False,
        min_healthy_tool_count=0,
    )


async def _snapshot(db_session, session_id: str) -> dict[str, Any]:
    service = SessionSnapshotService(
        session_mgr=SessionManager(_settings()),
        memory_manager=MemoryManager(_settings()),
        tool_registry=ToolRegistry(),
    )
    snapshot = await service.load_session_snapshot(db=db_session, session_id=session_id)
    assert snapshot is not None
    return snapshot.model_dump(mode="json")


def _session(
    *,
    session_id: str,
    plan_id: str,
    created_at: datetime,
    event_seq: int,
) -> Session:
    return Session(
        session_id=session_id,
        user_id="u1",
        status="WAITING_APPROVAL",
        current_intent=f"response document contract for {session_id}",
        plan_id=plan_id,
        plan_version=1,
        plan_hash=f"{plan_id}-hash",
        current_step_index=0,
        step_count=1,
        llm_call_count=0,
        event_seq=event_seq,
        session_started_at=created_at,
        created_at=created_at,
        updated_at=created_at + timedelta(seconds=3),
    )


def _plan(*, session_id: str, plan_id: str, created_at: datetime) -> Plan:
    return Plan(
        plan_id=plan_id,
        session_id=session_id,
        version=1,
        kind="execution",
        status="PENDING_APPROVAL",
        dependency_graph={"0": []},
        parallel_groups=[],
        plan_hash=f"{plan_id}-hash",
        plan_explanation="Stage the requested change.",
        risk_summary="High-risk write requires approval.",
        created_at=created_at,
        created_by="test",
    )


def _user_message(*, session_id: str, created_at: datetime) -> Message:
    return Message(
        message_id=f"{session_id}-user",
        session_id=session_id,
        role="user",
        content="Change one job priority",
        created_at=created_at,
    )


def _approval(
    *,
    session_id: str,
    plan_id: str,
    created_at: datetime,
    approval_id: str = "approval-rd-1",
) -> Approval:
    return Approval(
        approval_id=approval_id,
        session_id=session_id,
        subject_type="graph",
        plan_id=plan_id,
        tool_name="__langgraph_commit__",
        args={
            "risk_summary": "One job will be changed from medium to high priority.",
            "bundle_ui": {
                "rows": [{"job_id": "JOB-RD-001", "from_priority": "medium", "new_priority": "high"}],
                "write_set": "rd-write-set",
            },
        },
        risk_summary="One job will be changed from medium to high priority.",
        side_effect_level="HIGH",
        status="PENDING",
        expires_at=created_at + timedelta(hours=1),
        created_at=created_at + timedelta(seconds=2),
    )


def test_response_document_schema_validates_phase_1_block_types():
    document = ResponseDocument.model_validate(
        {
            "id": "rd:session-1:turn-1",
            "document_id": "rd:session-1:turn-1",
            "turn_id": "turn-1",
            "operation_id": "op-1",
            "revision": 7,
            "revision_source": "event_seq",
            "state": "waiting_approval",
            "status": "waiting_approval",
            "summary": "Waiting for approval.",
            "message": "Waiting for approval.",
            "current_step_id": "approval-step",
            "run_steps": [
                {
                    "step_id": "approval-step",
                    "kind": "approval",
                    "state": "waiting",
                    "title": "Waiting for approval",
                    "summary": "Review the write set.",
                    "approval_id": "approval-1",
                    "operation_id": "op-1",
                    "record_count": 1,
                    "current": True,
                }
            ],
            "blocks": [
                {"id": "activity:rd:session-1:turn-1", "type": "run_activity", "step_ids": ["approval-step"]},
                {
                    "id": "message:approval-1:waiting_approval",
                    "type": "short_message",
                    "message": "Waiting for approval.",
                    "status": "waiting_approval",
                },
                {
                    "id": "approval:approval-1",
                    "type": "approval_required",
                    "approval_id": "approval-1",
                    "operation_id": "op-1",
                    "summary": "Review one staged write.",
                    "rows": [{"row_id": "JOB-RD-001"}],
                },
                {
                    "id": "mutation:op-1",
                    "type": "mutation_result",
                    "operation_id": "op-1",
                    "approval_id": "approval-1",
                    "summary": "Updated one job.",
                    "rows": [{"row_id": "JOB-RD-001", "status": "succeeded"}],
                },
                {
                    "id": "table:op-1:affected-records",
                    "type": "result_table",
                    "operation_id": "op-1",
                    "approval_id": "approval-1",
                    "rows": [{"row_id": "JOB-RD-001", "status": "succeeded"}],
                },
                {
                    "id": "knowledge:op-1",
                    "type": "knowledge_answer",
                    "operation_id": "op-1",
                    "answer": "Use the controlled LOTO procedure.",
                },
                {
                    "id": "sources:op-1",
                    "type": "source_list",
                    "operation_id": "op-1",
                    "sources": [{"procedure_id": "LOTO-M-CNC-01"}],
                },
                {
                    "id": "diagnostic:op-1:planner_timeout",
                    "type": "diagnostic",
                    "severity": "error",
                    "reason": "planner_timeout",
                    "user_message": "The run was interrupted before it could continue.",
                    "technical_details": {"trace_id": "trace-1"},
                },
            ],
            "invariants": {"full_success_forbidden": True},
            "diagnostics": {"reason": "approval_pending"},
        }
    )

    assert document.version == 1
    assert document.id == "rd:session-1:turn-1"
    assert {block.type for block in document.blocks} == {
        "run_activity",
        "short_message",
        "approval_required",
        "mutation_result",
        "result_table",
        "knowledge_answer",
        "source_list",
        "diagnostic",
    }


def test_response_document_schema_rejects_missing_required_fields():
    with pytest.raises(ValidationError):
        ResponseDocument.model_validate(
            {
                "document_id": "rd:missing-id",
                "revision": 1,
                "revision_source": "event_seq",
                "state": "completed",
                "status": "completed",
            }
        )

    with pytest.raises(ValidationError):
        ResponseDocument.model_validate(
            {
                "id": "rd:bad-block",
                "document_id": "rd:bad-block",
                "revision": 1,
                "revision_source": "event_seq",
                "state": "waiting_approval",
                "status": "waiting_approval",
                "blocks": [{"id": "approval:missing-fields", "type": "approval_required"}],
            }
        )


@pytest.mark.asyncio
async def test_snapshot_includes_additive_response_document_without_changing_presentation(db_session):
    created_at = datetime(2026, 5, 18, 9, 0, 0)
    session_id = "rd-pending-snapshot"
    plan_id = "rd-pending-plan"
    db_session.add_all(
        [
            _session(session_id=session_id, plan_id=plan_id, created_at=created_at, event_seq=4),
            _user_message(session_id=session_id, created_at=created_at),
            _plan(session_id=session_id, plan_id=plan_id, created_at=created_at + timedelta(seconds=1)),
            _approval(session_id=session_id, plan_id=plan_id, created_at=created_at),
        ]
    )
    await db_session.commit()

    body = await _snapshot(db_session, session_id)

    assert body["presentation"]["kind"] == "approval_required"
    assert body["presentation"]["state"] == "pending"
    document = body["response_document"]
    assert document["version"] == 1
    assert document["id"].startswith(f"rd:{session_id}:")
    assert document["revision"] == 4
    assert document["revision_source"] == "event_seq"
    assert document["state"] == "waiting_approval"
    assert document["status"] == "waiting_approval"
    assert document["summary"] == body["presentation"]["summary"]
    assert document["diagnostics"]["reason"] == "approval_pending"
    assert {block["type"] for block in document["blocks"]} >= {
        "run_activity",
        "short_message",
        "approval_required",
        "result_table",
    }


@pytest.mark.asyncio
async def test_response_document_revision_is_monotonic_and_block_ids_are_stable(db_session):
    created_at = datetime(2026, 5, 18, 10, 0, 0)
    session_id = "rd-revision-stable"
    plan_id = "rd-revision-plan"
    session = _session(session_id=session_id, plan_id=plan_id, created_at=created_at, event_seq=11)
    db_session.add_all(
        [
            session,
            _user_message(session_id=session_id, created_at=created_at),
            _plan(session_id=session_id, plan_id=plan_id, created_at=created_at + timedelta(seconds=1)),
            _approval(
                session_id=session_id,
                plan_id=plan_id,
                created_at=created_at,
                approval_id="approval-rd-stable",
            ),
        ]
    )
    await db_session.commit()

    first = await _snapshot(db_session, session_id)
    first_document = first["response_document"]
    first_block_ids = [block["id"] for block in first_document["blocks"]]
    first_step_ids = [step["step_id"] for step in first_document["run_steps"]]

    session.event_seq = 12
    session.updated_at = created_at + timedelta(seconds=4)
    await db_session.commit()

    second = await _snapshot(db_session, session_id)
    second_document = second["response_document"]

    assert second_document["revision"] > first_document["revision"]
    assert second_document["id"] == first_document["id"]
    assert [block["id"] for block in second_document["blocks"]] == first_block_ids
    assert [step["step_id"] for step in second_document["run_steps"]] == first_step_ids
    assert "approval:approval-rd-stable" in first_block_ids
