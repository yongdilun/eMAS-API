from factory_agent.planning.intent import semantic_frame_for_text
from factory_agent.rag.knowledge_policy import default_knowledge_policy_registry


OSHA_LOTO_PROMPT = (
    "What is the purpose of Lockout/Tagout (LOTO) procedures according to OSHA? "
    "Is there any specific OSHA regulation or standard that defines this?"
)

MINIMUM_SOURCE_LOCATOR_FIELDS = {
    "source_id",
    "source_number",
    "doc_id",
    "chunk_id",
    "title",
    "organization",
    "snippet",
}


def assert_minimum_locator(source):
    missing = [key for key in MINIMUM_SOURCE_LOCATOR_FIELDS if not source.get(key)]
    assert not missing, f"missing source locator fields: {missing}"
    assert "file_path" not in source


def test_osha_loto_policy_provides_fallback_when_rag_is_empty():
    registry = default_knowledge_policy_registry()
    frame = semantic_frame_for_text(OSHA_LOTO_PROMPT)

    result = registry.apply(
        route_family=frame.route,
        query=OSHA_LOTO_PROMPT,
        answer="No relevant documents or data found for this query.",
        sources=[],
        safety_content=None,
        semantic_frame=frame,
    )

    assert result.policy_id == "osha_loto_control_of_hazardous_energy"
    assert "29 CFR 1910.147" in result.answer
    assert {source["doc_id"] for source in result.sources} == {
        "osha_3120_lockout_tagout",
        "29_cfr_1910_147",
    }
    for source in result.sources:
        assert_minimum_locator(source)
        assert source["policy_only"] is True
    assert "approved SOP" in result.safety_content


def test_osha_loto_policy_supplements_answer_missing_source_and_safety_evidence():
    registry = default_knowledge_policy_registry()
    frame = semantic_frame_for_text(OSHA_LOTO_PROMPT)

    result = registry.apply(
        route_family=frame.route,
        query=OSHA_LOTO_PROMPT,
        answer="Lockout/Tagout controls hazardous energy during servicing.",
        sources=[
            {
                "source_number": 1,
                "doc_id": "osha_3120_lockout_tagout",
                "title": "Control of Hazardous Energy Lockout/Tagout",
            }
        ],
        safety_content=None,
        semantic_frame=frame,
    )

    assert "29 CFR 1910.147" in result.answer
    assert [source["doc_id"] for source in result.sources] == [
        "osha_3120_lockout_tagout",
        "29_cfr_1910_147",
    ]
    for source in result.sources:
        assert_minimum_locator(source)
    assert result.sources[1]["policy_only"] is True
    assert "consult your safety officer" in result.safety_content


def test_unknown_non_loto_procedure_prompt_has_no_osha_loto_policy():
    registry = default_knowledge_policy_registry()
    prompt = "What SOP applies before cleaning Line 2?"
    frame = semantic_frame_for_text(prompt)

    result = registry.apply(
        route_family=frame.route,
        query=prompt,
        answer="No relevant documents or data found for this query.",
        sources=[],
        safety_content=None,
        semantic_frame=frame,
    )

    assert frame.route == "rag.procedure"
    assert result.policy_id is None
    assert "29 CFR 1910.147" not in result.answer
    assert result.sources == []
    assert result.safety_content is None


def test_osha_loto_policy_is_route_scoped_not_keyword_only():
    registry = default_knowledge_policy_registry()
    prompt = "Use OSHA LOTO guidance and show machine M-CNC-01 status"
    frame = semantic_frame_for_text(prompt)

    result = registry.apply(
        route_family=frame.route,
        query=prompt,
        answer="",
        sources=[],
        safety_content=None,
        semantic_frame=frame,
    )

    assert frame.route == "tool.read.machine_status"
    assert result.policy_id is None
    assert result.answer == ""
    assert result.sources == []
