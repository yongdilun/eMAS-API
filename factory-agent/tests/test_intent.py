from factory_agent.planning.intent import assess_intent


def test_assess_intent_treats_create_then_reject_as_create_operation():
    assessment = assess_intent("create job P-005 qty 3 but reject it")
    assert assessment.kind == "operations"
    assert assessment.action == "create"
    assert assessment.entity == "job"


def test_assess_intent_recognizes_scheduling_read_phrases():
    assessment = assess_intent("readiness for product P-001")
    assert assessment.kind == "operations"
    assert assessment.action == "read"
    assert assessment.entity == "product"
