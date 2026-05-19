from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Sequence

from factory_agent.rag.source_metadata import (
    insufficient_context_answer,
    normalize_source_locators,
    sanitize_rag_answer_text,
)


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
    safety_content: str | None = None
    required_answer_evidence: tuple[str, ...] = ()

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
            merged_answer = sanitize_rag_answer_text(answer)
            if route_family in {"rag.procedure", "rag.loto_procedure", "rag.safety_policy"} and _is_empty_or_unusable_answer(
                merged_answer
            ):
                merged_answer = insufficient_context_answer(has_sources=bool(sources))
            return KnowledgePolicyApplication(answer=merged_answer, sources=list(sources), safety_content=safety_content)

        merged_answer = (answer or "").strip()
        merged_sources = list(sources)
        merged_safety = safety_content
        rescued_answer = _source_backed_policy_answer(
            policy=policy,
            query=query,
            sources=merged_sources,
        )
        if rescued_answer and (
            _is_empty_or_unusable_answer(merged_answer)
            or not _policy_answer_has_required_evidence(
                policy=policy,
                query=query,
                answer=merged_answer,
                sources=merged_sources,
            )
        ):
            merged_answer = rescued_answer
        if (
            _is_empty_or_unusable_answer(merged_answer)
            or not merged_sources
            or not _policy_answer_has_required_evidence(
                policy=policy,
                query=query,
                answer=merged_answer,
                sources=merged_sources,
            )
        ):
            merged_answer = insufficient_context_answer(has_sources=bool(merged_sources))
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
                safety_content=(
                    "LOTO is safety-critical. Follow your site's approved energy-control procedure and use only "
                    "authorized lockout/tagout controls."
                ),
                required_answer_evidence=("notify", "affected employee"),
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
                safety_content=(
                    "This topic involves high-risk industrial procedures. Always follow your site's approved SOP, "
                    "obtain required permits, and consult your safety officer before proceeding."
                ),
                required_answer_evidence=("29 cfr 1910.147",),
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


def _is_empty_or_unusable_answer(answer: str) -> bool:
    lowered = (answer or "").strip().lower()
    return not lowered or any(lowered.startswith(prefix) for prefix in UNABLE_ANSWER_PREFIXES)


def _answer_has_required_evidence(answer: str, required_evidence: Sequence[str]) -> bool:
    if not required_evidence:
        return True
    lowered = (answer or "").lower()
    return all(evidence.lower() in lowered for evidence in required_evidence)


def _policy_answer_has_required_evidence(
    *,
    policy: KnowledgePolicy,
    query: str,
    answer: str,
    sources: Sequence[Any],
) -> bool:
    if policy.policy_id == "loto_notification_document_content":
        return _loto_notification_answer_is_source_supported(query=query, answer=answer, sources=sources)
    return _answer_has_required_evidence(answer, policy.required_answer_evidence)


def _source_backed_policy_answer(
    *,
    policy: KnowledgePolicy,
    query: str,
    sources: Sequence[Any],
) -> str | None:
    if policy.policy_id != "loto_notification_document_content":
        return None
    if not re.search(r"\bre-?energiz", query or "", re.IGNORECASE):
        return None
    supporting_source = _first_reenergizing_notification_source(sources)
    if supporting_source is None:
        return None
    source_number = _source_value(supporting_source, "source_number") or 1
    return (
        "Before reenergizing the machine after lockout or tagout devices are removed, the employer must assure "
        "that employees who operate or work with the machine, and employees in the service or maintenance area, "
        f"know the devices have been removed and that the machine is capable of being reenergized.[^{source_number}]"
    )


def _loto_notification_answer_is_source_supported(
    *,
    query: str,
    answer: str,
    sources: Sequence[Any],
) -> bool:
    lowered_query = (query or "").lower()
    if "osha" in lowered_query and not _has_osha_source(sources):
        return False
    if re.search(r"\bre-?energiz", lowered_query, re.IGNORECASE):
        lowered_answer = (answer or "").lower()
        answer_ok = (
            "employee" in lowered_answer
            and any(term in lowered_answer for term in ("know", "notify", "notification", "informed", "aware", "assure"))
            and any(term in lowered_answer for term in ("reenerg", "removed", "device"))
        )
        return answer_ok and _source_text_supports_reenergizing_notification(sources)
    return _answer_has_required_evidence(answer, ("notify", "affected employee"))


def _source_text_supports_reenergizing_notification(sources: Sequence[Any]) -> bool:
    return _first_reenergizing_notification_source(sources) is not None


def _first_reenergizing_notification_source(sources: Sequence[Any]) -> Any | None:
    for source in sources:
        if _source_item_supports_reenergizing_notification(source):
            return source
    return None


def _source_item_supports_reenergizing_notification(source: Any) -> bool:
    source_text = _source_item_text(source)
    return (
        "reenerg" in source_text
        and "employee" in source_text
        and any(term in source_text for term in ("know", "assure", "notify", "informed", "aware"))
        and ("remov" in source_text or "device" in source_text)
    )


def _has_osha_source(sources: Sequence[Any]) -> bool:
    for source in sources:
        identity = " ".join(
            str(_source_value(source, key) or "")
            for key in ("doc_id", "title", "organization", "source_id")
        ).lower()
        if "osha" in identity:
            return True
    return False


def _source_item_text(source: Any) -> str:
    parts: list[str] = []
    for key in ("snippet", "text_search", "title", "organization", "doc_id"):
        value = _source_value(source, key)
        if value:
            parts.append(str(value))
    return " ".join(parts).lower()


def _source_value(source: Any, key: str) -> Any:
    if isinstance(source, dict):
        return source.get(key)
    return getattr(source, key, None)
