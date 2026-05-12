"""Phase 2: intent splitter structured output (no rejection of incomplete queries)."""

from __future__ import annotations

import re

from factory_agent.planning.intent import split_user_intents


def test_split_multi_part_machine_then_schedule():
    q = "Find available CNC machines and schedule job 001"
    intents = split_user_intents(q)
    assert len(intents) >= 2
    cats = [i.category for i in intents]
    assert "machine" in cats
    assert "scheduling" in cats or "job" in cats
    sched_like = [i for i in intents if i.category in ("scheduling", "job")]
    machine_like = [i for i in intents if i.category == "machine"]
    assert sched_like and machine_like
    assert any(machine_like[0].intent_id in i.depends_on for i in sched_like)
    job_constraints = [c for i in intents for c in i.explicit_constraints if c.field == "job_id"]
    assert job_constraints, "expected job id constraint from 'job 001'"
    assert any(str(c.value) == "001" or c.value == "001" for c in job_constraints)


def test_incomplete_query_parsed_without_rejection():
    intents = split_user_intents("schedule something sometime")
    assert len(intents) >= 1
    assert all(i.status == "pending" for i in intents)


def test_explicit_machine_constraint_from_use_machine_phrase():
    intents = split_user_intents("Use Machine M-001 for the next step")
    flat = [c for i in intents for c in i.explicit_constraints]
    assert any(c.field == "machine_id" and re.search(r"M-001", str(c.value), re.I) for c in flat)
