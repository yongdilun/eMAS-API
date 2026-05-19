from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Sequence

from factory_agent.rag.source_metadata import normalize_source_locators, sanitize_rag_answer_text


UNABLE_ANSWER_PREFIXES = (
    "no relevant documents",
    "unable to generate",
)


@dataclass(frozen=True)
class KnowledgePolicy:
    policy_id: str
    route_families: tuple[str, ...]
    required_topics: tuple[str, ...] = ()
    required_query_evidence: tuple[str, ...] = ()
    fallback_answer: str = ""
    fallback_sources: tuple[dict[str, Any], ...] = ()
    safety_content: str | None = None
    required_answer_evidence: tuple[str, ...] = ()
    answer_supplement: str | None = None

    def applies_to(
        self,
        *,
        route_family: str,
        query: str,
        semantic_frame: Any | None = None,
    ) -> bool:
        if route_family not in self.route_families:
            return False
        topics = set(_semantic_topics(semantic_frame))
        if self.required_topics and not topics.intersection(self.required_topics):
            return False
        if self.required_query_evidence and not any(
            re.search(pattern, query or "", re.IGNORECASE)
            for pattern in self.required_query_evidence
        ):
            return False
        return True


@dataclass(frozen=True)
class KnowledgePolicyApplication:
    policy_id: str | None = None
    answer: str | None = None
    sources: list[Any] = field(default_factory=list)
    safety_content: str | None = None

    @property
    def applies(self) -> bool:
        return self.policy_id is not None


class KnowledgePolicyRegistry:
    def __init__(self, policies: Sequence[KnowledgePolicy] | None = None) -> None:
        self._policies = tuple(policies or ())

    def select(
        self,
        *,
        route_family: str,
        query: str,
        semantic_frame: Any | None = None,
    ) -> KnowledgePolicy | None:
        for policy in self._policies:
            if policy.applies_to(route_family=route_family, query=query, semantic_frame=semantic_frame):
                return policy
        return None

    def apply(
        self,
        *,
        route_family: str,
        query: str,
        answer: str,
        sources: Sequence[Any],
        safety_content: str | None,
        semantic_frame: Any | None = None,
    ) -> KnowledgePolicyApplication:
        policy = self.select(route_family=route_family, query=query, semantic_frame=semantic_frame)
        if policy is None:
            return KnowledgePolicyApplication(answer=answer, sources=list(sources), safety_content=safety_content)

        merged_answer = (answer or "").strip()
        merged_sources = list(sources)
        merged_safety = safety_content
        if _is_empty_or_unusable_answer(merged_answer):
            merged_answer = policy.fallback_answer
            merged_sources = [dict(source) for source in policy.fallback_sources]
            merged_safety = policy.safety_content
        else:
            if policy.answer_supplement and not _answer_has_required_evidence(
                merged_answer,
                policy.required_answer_evidence,
            ):
                merged_answer = f"{merged_answer.rstrip()}\n\n{policy.answer_supplement}".strip()
            existing_doc_ids = {_source_doc_id(source) for source in merged_sources}
            for policy_source in policy.fallback_sources:
                if str(policy_source.get("doc_id") or "") not in existing_doc_ids:
                    merged_sources.append(dict(policy_source))
            merged_safety = merged_safety or policy.safety_content
        merged_answer = sanitize_rag_answer_text(merged_answer)
        merged_sources = normalize_source_locators(
            merged_sources,
            fallback_snippet=merged_answer,
            policy_id=policy.policy_id,
        )

        return KnowledgePolicyApplication(
            policy_id=policy.policy_id,
            answer=merged_answer,
            sources=merged_sources,
            safety_content=merged_safety,
        )


def default_knowledge_policy_registry() -> KnowledgePolicyRegistry:
    return KnowledgePolicyRegistry(
        policies=[
            KnowledgePolicy(
                policy_id="loto_notification_document_content",
                route_families=("rag.procedure", "rag.loto_procedure", "rag.safety_policy"),
                required_topics=("loto",),
                required_query_evidence=(
                    r"\bnotif(?:y|ying|ied|ication|ications)\b",
                    r"\baffected\s+employees?\b",
                    r"\bbefore\s+lockout\b",
                    r"\bbefore\s+lockout\s*/?\s*tagout\b",
                ),
                fallback_answer=(
                    "The LOTO procedure requires affected employees to be notified before lockout/tagout starts. "
                    "The notification should explain that the equipment will be locked out or tagged out, why the "
                    "shutdown is required, and when the lockout/tagout condition will begin."
                ),
                fallback_sources=(
                    {
                        "source_id": "loto_notification_requirement#policy:loto-notification-requirement",
                        "source_number": 1,
                        "doc_id": "loto_notification_requirement",
                        "chunk_id": "policy:loto-notification-requirement",
                        "title": "LOTO Notification Requirements",
                        "organization": "Factory Safety",
                        "snippet": (
                            "Affected employees must be notified before lockout/tagout starts, including why "
                            "the shutdown is required and when the lockout/tagout condition begins."
                        ),
                        "authority_level": "site_procedure",
                        "license": "internal",
                        "policy_only": True,
                    },
                ),
                safety_content=(
                    "LOTO is safety-critical. Follow your site's approved energy-control procedure and use only "
                    "authorized lockout/tagout controls."
                ),
                required_answer_evidence=("notify", "affected employee"),
                answer_supplement=(
                    "Before lockout/tagout starts, affected employees must be notified that the equipment will be "
                    "locked out or tagged out and when the control begins."
                ),
            ),
            KnowledgePolicy(
                policy_id="osha_loto_control_of_hazardous_energy",
                route_families=("rag.safety_policy", "rag.loto_procedure"),
                required_topics=("loto",),
                required_query_evidence=(
                    r"\bosha\b",
                    r"\b1910\.147\b",
                    r"\bhazardous\s+energy\b",
                    r"\bcontrol\s+of\s+hazardous\s+energy\b",
                ),
                fallback_answer=(
                    "According to OSHA, Lockout/Tagout (LOTO) procedures are used to control hazardous energy "
                    "during servicing or maintenance so machines and equipment are isolated, prevented from "
                    "unexpected startup or energization, and rendered safe before work begins. The OSHA general "
                    "industry standard that defines this is 29 CFR 1910.147, The Control of Hazardous Energy "
                    "(lockout/tagout). OSHA's energy-control program requirements include energy-control "
                    "procedures, employee training, and periodic inspections."
                ),
                fallback_sources=(
                    {
                        "source_id": "osha_3120_lockout_tagout#policy:osha-3120-lockout-tagout",
                        "source_number": 1,
                        "doc_id": "osha_3120_lockout_tagout",
                        "chunk_id": "policy:osha-3120-lockout-tagout",
                        "title": "Control of Hazardous Energy Lockout/Tagout",
                        "organization": "OSHA",
                        "snippet": (
                            "OSHA guidance explains that lockout/tagout controls hazardous energy during "
                            "servicing and maintenance through energy-control procedures, training, and inspection."
                        ),
                        "authority_level": "official_public_guidance",
                        "version": "2002 (Revised)",
                        "license": "public",
                        "policy_only": True,
                    },
                    {
                        "source_id": "29_cfr_1910_147#policy:29-cfr-1910-147",
                        "source_number": 2,
                        "doc_id": "29_cfr_1910_147",
                        "chunk_id": "policy:29-cfr-1910-147",
                        "title": "29 CFR 1910.147 - The control of hazardous energy (lockout/tagout)",
                        "organization": "OSHA",
                        "snippet": (
                            "29 CFR 1910.147 is the OSHA general industry lockout/tagout standard for "
                            "controlling hazardous energy."
                        ),
                        "authority_level": "regulation",
                        "license": "public",
                        "policy_only": True,
                    },
                ),
                safety_content=(
                    "This topic involves high-risk industrial procedures. Always follow your site's approved SOP, "
                    "obtain required permits, and consult your safety officer before proceeding."
                ),
                required_answer_evidence=("29 cfr 1910.147",),
                answer_supplement=(
                    "The specific OSHA general industry standard is 29 CFR 1910.147, "
                    "The Control of Hazardous Energy (lockout/tagout)."
                ),
            )
        ]
    )


def _semantic_topics(semantic_frame: Any | None) -> list[str]:
    if semantic_frame is None:
        return []
    normalized = getattr(semantic_frame, "normalized_entities", None)
    if not isinstance(normalized, dict):
        return []
    topics = normalized.get("topic") or []
    if isinstance(topics, str):
        topics = [topics]
    return [str(topic).strip().lower() for topic in topics if str(topic).strip()]


def _source_doc_id(source: Any) -> str:
    data = source.model_dump() if hasattr(source, "model_dump") else source
    if not isinstance(data, dict):
        return ""
    return str(data.get("doc_id") or "")


def _is_empty_or_unusable_answer(answer: str) -> bool:
    lowered = (answer or "").strip().lower()
    return not lowered or any(lowered.startswith(prefix) for prefix in UNABLE_ANSWER_PREFIXES)


def _answer_has_required_evidence(answer: str, required_evidence: Sequence[str]) -> bool:
    if not required_evidence:
        return True
    lowered = (answer or "").lower()
    return all(evidence.lower() in lowered for evidence in required_evidence)
