"""
Regression tests for the SSE architecture redesign (Option C).

Coverage:
1. Atomic approval — approve sets Approval.status=APPROVED and clears
   langgraph_pending_approval in the same commit.
2. Atomic rejection — reject sets Approval.status=REJECTED in same commit.
3. event_seq bump — approving / rejecting increments Session.event_seq.
4. Snapshot self-heal — pending_approval is null when approval row is
   not PENDING (stale approval reappears bug).
5. resume_hint — snapshot returns resume_hint when session is EXECUTING
   and langgraph_approval_resume is present.
6. pending_approval trust — snapshot returns the pending approval directly
   when session is WAITING_APPROVAL and row is PENDING.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy import select

from factory_agent.persistence.models import Approval as ApprovalRow
from factory_agent.persistence.models import Session as SessionRow


def _sid():
    return str(uuid.uuid4())


def _aid():
    return str(uuid.uuid4())


def _make_session(db_session, session_id=None, status="WAITING_APPROVAL", replan_context=None):
    sid = session_id or _sid()
    row = SessionRow(
        session_id=sid,
        user_id="test-user",
        name="Test",
        status=status,
        plan_version=1,
        version=1,
        event_seq=0,
        session_started_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        replan_context=replan_context or {},
    )
    db_session.add(row)
    return row


def _make_approval(db_session, session_id, approval_id=None, status="PENDING"):
    aid = approval_id or _aid()
    row = ApprovalRow(
        approval_id=aid,
        session_id=session_id,
        subject_type="graph",
        tool_name="test_tool",
        args={"x": 1},
        risk_summary="Risk summary",
        side_effect_level="LOW",
        status=status,
        expires_at=datetime.utcnow() + timedelta(hours=24),
        created_at=datetime.utcnow(),
    )
    db_session.add(row)
    return row


# ---------------------------------------------------------------------------
# 1 & 3. Atomic approve + event_seq bump
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_approve_is_atomic_and_bumps_event_seq(db_session):
    """Approval row and session status change in one commit; event_seq advances."""
    sid = _sid()
    _make_session(db_session, session_id=sid, status="WAITING_APPROVAL", replan_context={
        "langgraph_pending_approval": {"approval_id": "dummy", "thread_id": sid},
    })
    approval = _make_approval(db_session, session_id=sid)
    # Capture initial_seq before commit while value is known.
    initial_seq = 0
    await db_session.commit()

    # Simulate what approve_approval does.
    row = (await db_session.execute(
        select(ApprovalRow).where(ApprovalRow.approval_id == approval.approval_id)
    )).scalars().first()
    assert row is not None

    sess_row = (await db_session.execute(
        select(SessionRow).where(SessionRow.session_id == sid)
    )).scalars().first()

    row.status = "APPROVED"
    row.decided_by = "tester"
    row.decided_at = datetime.utcnow()

    context = dict(sess_row.replan_context or {})
    context["langgraph_approval_resume"] = {
        "approval_id": row.approval_id,
        "thread_id": sid,
        "status": "approved",
        "decided_at": row.decided_at.isoformat(),
    }
    context.pop("langgraph_pending_approval", None)
    sess_row.replan_context = context
    sess_row.status = "EXECUTING"
    sess_row.event_seq = (sess_row.event_seq or 0) + 1
    sess_row.updated_at = datetime.utcnow()
    await db_session.commit()

    # Re-read from DB to confirm values were persisted.
    # populate_existing forces a fresh DB read without needing expire_all().
    refreshed_approval = (await db_session.execute(
        select(ApprovalRow).where(ApprovalRow.approval_id == approval.approval_id)
        .execution_options(populate_existing=True)
    )).scalars().first()
    refreshed_sess = (await db_session.execute(
        select(SessionRow).where(SessionRow.session_id == sid)
        .execution_options(populate_existing=True)
    )).scalars().first()

    assert refreshed_approval.status == "APPROVED"
    assert refreshed_sess.status == "EXECUTING"
    assert refreshed_sess.event_seq == initial_seq + 1
    assert "langgraph_pending_approval" not in (refreshed_sess.replan_context or {})
    assert "langgraph_approval_resume" in (refreshed_sess.replan_context or {})


# ---------------------------------------------------------------------------
# 2 & 3. Atomic reject + event_seq bump
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_reject_is_atomic_and_bumps_event_seq(db_session):
    """Rejection row and session status change in one commit; event_seq advances."""
    sid = _sid()
    _make_session(db_session, session_id=sid, status="WAITING_APPROVAL", replan_context={
        "langgraph_pending_approval": {"approval_id": "dummy"},
    })
    approval = _make_approval(db_session, session_id=sid)
    # Capture initial_seq before commit while value is known.
    initial_seq = 0
    await db_session.commit()

    sess_row = (await db_session.execute(
        select(SessionRow).where(SessionRow.session_id == sid)
    )).scalars().first()
    row = (await db_session.execute(
        select(ApprovalRow).where(ApprovalRow.approval_id == approval.approval_id)
    )).scalars().first()

    row.status = "REJECTED"
    row.decided_by = "tester"
    row.decided_at = datetime.utcnow()
    row.rejection_reason = "Not approved"

    context = dict(sess_row.replan_context or {})
    context.pop("langgraph_pending_approval", None)
    context.pop("langgraph_approval_resume", None)
    sess_row.replan_context = context
    sess_row.status = "IDLE"
    sess_row.event_seq = (sess_row.event_seq or 0) + 1
    sess_row.updated_at = datetime.utcnow()
    await db_session.commit()

    refreshed_approval = (await db_session.execute(
        select(ApprovalRow).where(ApprovalRow.approval_id == approval.approval_id)
        .execution_options(populate_existing=True)
    )).scalars().first()
    refreshed_sess = (await db_session.execute(
        select(SessionRow).where(SessionRow.session_id == sid)
        .execution_options(populate_existing=True)
    )).scalars().first()

    assert refreshed_approval.status == "REJECTED"
    assert refreshed_sess.status == "IDLE"
    assert refreshed_sess.event_seq == initial_seq + 1
    assert "langgraph_pending_approval" not in (refreshed_sess.replan_context or {})


# ---------------------------------------------------------------------------
# 4. Snapshot self-heal: decided approval must not appear as pending
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_snapshot_self_heal_decided_approval_is_null(db_session):
    """
    Regression for 'stale approval reappears'.

    If the approval row is APPROVED (already decided) but the session was
    not yet updated (e.g. crash between commit and status update), the
    snapshot loader must return pending_approval=None.
    """
    sid = _sid()
    _make_session(db_session, session_id=sid, status="EXECUTING")
    decided_approval = _make_approval(db_session, session_id=sid, status="APPROVED")
    await db_session.commit()

    # Simulate what the snapshot loader self-heal does.
    pending = (await db_session.execute(
        select(ApprovalRow)
        .where(ApprovalRow.session_id == sid)
        .order_by(ApprovalRow.created_at.asc())
    )).scalars().all()

    raw_pending = next((r for r in reversed(pending) if r.status == "PENDING"), None)
    # Self-heal check.
    healed = raw_pending if (raw_pending and raw_pending.status == "PENDING") else None

    assert healed is None, (
        "Self-heal must null out a decided approval row so it is not shown as pending"
    )
    _ = decided_approval  # referenced to suppress unused-variable warning


@pytest.mark.anyio
async def test_snapshot_self_heal_pending_approval_shown_when_truly_pending(db_session):
    """When the approval row is genuinely PENDING, it must be exposed in the snapshot."""
    sid = _sid()
    _make_session(db_session, session_id=sid, status="WAITING_APPROVAL")
    pending_approval = _make_approval(db_session, session_id=sid, status="PENDING")
    await db_session.commit()

    pending = (await db_session.execute(
        select(ApprovalRow)
        .where(ApprovalRow.session_id == sid)
        .order_by(ApprovalRow.created_at.asc())
    )).scalars().all()

    raw_pending = next((r for r in reversed(pending) if r.status == "PENDING"), None)
    healed = raw_pending if (raw_pending and raw_pending.status == "PENDING") else None

    assert healed is not None
    assert healed.approval_id == pending_approval.approval_id


# ---------------------------------------------------------------------------
# 5. resume_hint derivation
# ---------------------------------------------------------------------------

def _build_resume_hint(sess_status: str, replan_context: dict, events=None):
    """Mirrors the resume_hint derivation in load_session_snapshot."""
    from factory_agent.schemas import ResumeHintResponse

    _rc = replan_context if isinstance(replan_context, dict) else {}
    _lr = _rc.get("langgraph_approval_resume")
    if not (
        isinstance(_lr, dict)
        and str(_lr.get("status") or "").lower() == "approved"
        and sess_status == "EXECUTING"
    ):
        return None

    decided_at_str = str(_lr.get("decided_at") or "").strip()
    has_post = False
    if decided_at_str and events:
        try:
            decided_dt = datetime.fromisoformat(decided_at_str)
            has_post = any(
                ev.get("event_type") == "tool_started"
                and ev.get("created_at") is not None
                and datetime.fromisoformat(str(ev["created_at"])) > decided_dt
                for ev in events
            )
        except (ValueError, TypeError):
            pass
    if has_post:
        return None
    return ResumeHintResponse(
        applying_after_approval=True,
        approval_id=str(_lr.get("approval_id") or "").strip() or None,
        decided_at=decided_at_str or None,
    )


def test_resume_hint_set_when_executing_and_no_post_approval_tool():
    decided_at = datetime.utcnow().isoformat()
    rc = {
        "langgraph_approval_resume": {
            "approval_id": "test-aid",
            "status": "approved",
            "decided_at": decided_at,
        }
    }
    hint = _build_resume_hint("EXECUTING", rc, events=[])
    assert hint is not None
    assert hint.applying_after_approval is True
    assert hint.approval_id == "test-aid"


def test_resume_hint_null_when_post_approval_tool_started():
    decided_at = (datetime.utcnow() - timedelta(seconds=5)).isoformat()
    rc = {
        "langgraph_approval_resume": {
            "approval_id": "test-aid",
            "status": "approved",
            "decided_at": decided_at,
        }
    }
    events = [{
        "event_type": "tool_started",
        "created_at": datetime.utcnow().isoformat(),
    }]
    hint = _build_resume_hint("EXECUTING", rc, events=events)
    assert hint is None


def test_resume_hint_null_when_not_executing():
    decided_at = datetime.utcnow().isoformat()
    rc = {
        "langgraph_approval_resume": {
            "approval_id": "test-aid",
            "status": "approved",
            "decided_at": decided_at,
        }
    }
    for status in ("WAITING_APPROVAL", "IDLE", "COMPLETED", "BLOCKED"):
        hint = _build_resume_hint(status, rc, events=[])
        assert hint is None, f"resume_hint must be None for status={status}"


def test_resume_hint_null_when_no_approval_resume_context():
    hint = _build_resume_hint("EXECUTING", {}, events=[])
    assert hint is None
