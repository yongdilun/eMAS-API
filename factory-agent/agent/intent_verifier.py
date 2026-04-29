from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any

from jsonschema import Draft202012Validator

from .schemas import ToolInfo


import json
import os

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "ai_domain_config.json")
try:
    with open(_CONFIG_PATH, "r") as f:
        _AI_CONFIG = json.load(f).get("python", {})
except Exception:
    _AI_CONFIG = {}

_TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")
_STOPWORDS = set(_AI_CONFIG.get("stopwords", []))

@dataclass(frozen=True)
class ClauseVerificationResult:
    args: dict[str, Any]
    resolved_predicates: dict[str, Any]
    unresolved_terms: list[str]
    clarification: str | None = None
    confirmation: dict[str, Any] | None = None
    negative_bindings: list[dict[str, Any]] = field(default_factory=list)
    predicates: list[dict[str, Any]] = field(default_factory=list)
    predicate_coverage_score: float = 1.0

_CONTROL_FIELDS = set(_AI_CONFIG.get("control_fields", []))
_ACTION_VERBS_FILTER = set(_AI_CONFIG.get("action_verbs", []))
_VAGUE_FREE_TEXT = set(_AI_CONFIG.get("vague_free_text", []))
_FIELD_IMPLYING_PREPOSITIONS = {k: set(v) for k, v in _AI_CONFIG.get("field_implying_prepositions", {}).items()}


def _normalize_token(value: str) -> str:
    token = (value or "").strip().lower()
    if token.endswith("ies") and len(token) > 3:
        return token[:-3] + "y"
    if token.endswith("s") and len(token) > 3:
        return token[:-1]
    return token


def normalize_predicate_value(value: str) -> str:
    normalized = (value or "").strip().lower()
    normalized = re.sub(r"[_-]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def _tokenize(text: str) -> list[str]:
    return [_normalize_token(match.group(0)) for match in _TOKEN_RE.finditer(text or "")]


def _field_aliases(field_name: str) -> list[str]:
    normalized = str(field_name or "").strip().lower()
    if not normalized:
        return []
    aliases = {normalized, normalized.replace("_", " ")}
    parts = [part for part in re.split(r"[_\W]+", normalized) if part]
    aliases.update(parts)
    if normalized.endswith("_id"):
        aliases.add("id")
    return sorted(alias for alias in aliases if alias)


def _tool_entity(tool: ToolInfo) -> str:
    token = f"{tool.name} {tool.endpoint} {' '.join(tool.capability_tags or [])}".lower()
    if "machine" in token or "/machines" in token:
        return "machine"
    if "job" in token or "/jobs" in token:
        return "job"
    if "inventory" in token or "material" in token or "/inventory" in token:
        return "inventory"
    if "approval" in token or "/approvals" in token:
        return "approval"
    if "proposal" in token or "/proposals" in token:
        return "proposal"
    return "record"


def _schema_properties(tool: ToolInfo) -> dict[str, dict[str, Any]]:
    raw = (tool.input_schema or {}).get("properties", {})
    if not isinstance(raw, dict):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for field_name, field_schema in raw.items():
        if isinstance(field_schema, dict):
            result[str(field_name)] = field_schema
    return result


def _explicitly_mentions_field(clause: str, field_name: str) -> bool:
    text = clause or ""
    for alias in _field_aliases(field_name):
        alias_pattern = re.escape(alias).replace(r"\ ", r"[ _-]+")
        if re.search(rf"\b{alias_pattern}\b", text, flags=re.IGNORECASE):
            return True
    return False


def _candidate_filter_fields(tool: ToolInfo, clause: str) -> dict[str, dict[str, Any]]:
    properties = _schema_properties(tool)
    query_names = set(tool.query_params or [])
    query_names.update(
        key for key, source in (tool.param_sources or {}).items() if source == "query"
    )
    if not query_names:
        query_names = set(properties)

    result: dict[str, dict[str, Any]] = {}
    for field_name, field_schema in properties.items():
        field_type = field_schema.get("type")
        if isinstance(field_type, list):
            field_type = next((t for t in field_type if t != "null"), "string")
        if field_type != "string":
            continue
        if field_name not in query_names and tool.method == "GET":
            continue
        if field_name in _CONTROL_FIELDS and not _explicitly_mentions_field(clause, field_name):
            continue
        result[field_name] = field_schema
    return result


def _entity_pattern(entity: str) -> str:
    if entity == "inventory":
        return r"(?:inventory|inventories|material|materials)"
    return rf"(?:{re.escape(entity)}|{re.escape(entity)}s)"


def _enum_field_schemas(tool: ToolInfo) -> dict[str, dict[str, Any]]:
    properties = _schema_properties(tool)
    result: dict[str, dict[str, Any]] = {}
    for field_name, field_schema in properties.items():
        if not isinstance(field_schema, dict):
            continue
        enum_values = field_schema.get("enum")
        if field_schema.get("type") == "string" and isinstance(enum_values, list) and enum_values:
            result[str(field_name)] = field_schema
    return result


def _explicit_enum_match(clause: str, field_name: str, field_schema: dict[str, Any]) -> tuple[str | None, str | None]:
    aliases = _field_aliases(field_name)
    enum_values = [str(value) for value in field_schema.get("enum", []) if str(value)]
    enum_by_token = {_normalize_token(value): value for value in enum_values}
    for alias in aliases:
        alias_pattern = re.escape(alias).replace(r"\ ", r"[ _-]+")
        match = re.search(
            rf"\b{alias_pattern}\b\s*(?:=|:|is|are)?\s*([A-Za-z][A-Za-z0-9_-]*)",
            clause or "",
            flags=re.IGNORECASE,
        )
        if not match:
            continue
        raw_value = match.group(1)
        mapped = enum_by_token.get(_normalize_token(raw_value))
        if mapped:
            return mapped, None
        return None, raw_value
    return None, None


def _exact_enum_mentions(clause: str, field_schema: dict[str, Any]) -> list[str]:
    clause_lower = (clause or "").lower()
    matches: list[str] = []
    for enum_value in field_schema.get("enum", []):
        value = str(enum_value).strip()
        if not value:
            continue
        if re.search(rf"\b{re.escape(value.lower())}\b", clause_lower):
            matches.append(value)
    return matches


def _extract_residual_filter_terms(
    clause: str,
    entity: str,
    consumed_tokens: set[str],
    filter_field_aliases: set[str],
) -> list[str]:
    """Fallback: extract noun phrases when the entity word is absent from the clause.

    Strips action verbs, determiners, stopwords, and the entity word itself,
    then groups remaining tokens into the longest candidate phrases.
    Used so "find all Coating Station" produces the same predicate candidate
    as "find all Coating Station machines".
    """
    text = re.sub(r"\s+", " ", clause or "").strip()
    if not text:
        return []
    skip: set[str] = _STOPWORDS | _ACTION_VERBS_FILTER
    skip.add(entity.lower())
    skip.add(entity.lower() + "s")
    if entity.lower().endswith("y"):
        skip.add(entity.lower()[:-1] + "ies")
    raw_tokens = _TOKEN_RE.findall(text)
    kept: list[str] = []
    for tok in raw_tokens:
        norm = _normalize_token(tok)
        if norm in skip or norm in consumed_tokens or norm in filter_field_aliases:
            continue
        kept.append(tok)
    if not kept:
        return []
    phrases: list[str] = []
    used = [False] * len(kept)
    for length in (3, 2, 1):
        if length > len(kept):
            continue
        for i in range(len(kept) - length + 1):
            if any(used[i: i + length]):
                continue
            phrase = " ".join(kept[i: i + length])
            norm = _normalize_token(phrase)
            if norm and norm not in _VAGUE_FREE_TEXT and len(norm) > 1:
                phrases.append(phrase)
                for j in range(i, i + length):
                    used[j] = True
    return phrases


def _entity_adjacent_term(clause: str, entity: str) -> str | None:
    entity_pattern = _entity_pattern(entity)
    match = re.search(
        rf"\b(?:check|show|list|get|find|view|inspect|lookup)\b\s+(?:all\s+)?([A-Za-z][A-Za-z0-9_-]*)\s+{entity_pattern}\b",
        clause or "",
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    term = _normalize_token(match.group(1))
    if term in _STOPWORDS:
        return None
    return term


def _entity_adjacent_phrase(clause: str, entity: str) -> str | None:
    entity_pattern = _entity_pattern(entity)
    text = re.sub(r"\s+", " ", clause or "").strip()
    if not text:
        return None
    prefix = re.search(
        rf"\b(?:check|show|list|get|find|view|inspect|lookup)\b\s+(?:all\s+|any\s+)?(?P<term>[A-Za-z][A-Za-z0-9 _-]{{1,80}}?)\s+{entity_pattern}\b",
        text,
        flags=re.IGNORECASE,
    )
    if prefix:
        raw = prefix.group("term").strip(" ,")
        if re.search(r"\bfor\b", raw, flags=re.IGNORECASE):
            return None
        tokens = [_normalize_token(t) for t in raw.split()]
        while tokens and tokens[0] in _STOPWORDS:
            tokens.pop(0)
        cleaned = " ".join(tokens).strip()
        if cleaned and cleaned not in _STOPWORDS:
            return raw.strip()

    suffix = re.search(
        rf"\b{entity_pattern}\b\s+(?:in|at|inside|within)\s+(?P<term>[A-Za-z][A-Za-z0-9 _-]{{1,80}})$",
        text,
        flags=re.IGNORECASE,
    )
    if suffix:
        return suffix.group("term").strip(" ,")
    return None


def _explicit_field_value(clause: str, field_name: str) -> str | None:
    text = re.sub(r"\s+", " ", clause or "").strip()
    for alias in _field_aliases(field_name):
        alias_pattern = re.escape(alias).replace(r"\ ", r"[ _-]+")
        match = re.search(
            rf"\b{alias_pattern}\b\s*(?:=|:|is|are)?\s*(?P<value>[A-Za-z][A-Za-z0-9 _-]{{0,80}})",
            text,
            flags=re.IGNORECASE,
        )
        if not match:
            continue
        value = match.group("value").strip(" ,")
        value = re.split(r"\b(?:and|then|with|where)\b", value, maxsplit=1, flags=re.IGNORECASE)[0].strip(" ,")
        if value and _normalize_token(value) not in _STOPWORDS:
            return value
    return None


def _preposition_implied_field(clause: str, term: str, field_name: str) -> bool:
    preps = _FIELD_IMPLYING_PREPOSITIONS.get(field_name, set())
    if not preps:
        return False
    value = re.escape(term).replace(r"\ ", r"[ _-]+")
    for prep in preps:
        if re.search(rf"\b{prep}\s+{value}\b", clause or "", flags=re.IGNORECASE):
            return True
    return False


def _candidate_score(*, clause: str, term: str, field_name: str, field_schema: dict[str, Any], source: str) -> tuple[float, str]:
    normalized_term = normalize_predicate_value(term)
    enum_values = [str(v) for v in field_schema.get("enum", []) if str(v)]
    enum_by_norm = {normalize_predicate_value(v): v for v in enum_values}
    description = str(field_schema.get("description") or "").lower()
    field = field_name.lower()

    if source == "explicit_field":
        return 0.99, "explicit field phrase"
    if enum_values and normalized_term in enum_by_norm:
        return 0.98, "exact enum value"
    if _preposition_implied_field(clause, term, field_name):
        return 0.95, "preposition implies field"
    if source == "memory":
        return 0.96, "prior session memory"

    if normalized_term in _VAGUE_FREE_TEXT:
        return 0.2, "vague free-text value"

    score = 0.0
    reason = "weak schema signal"
    if field == "location" or "location" in description:
        if re.search(r"\b(?:shop|line|area|zone|bay|cell|station|warehouse|room|floor)\b", normalized_term):
            # Deliberately conservative: these words appear in both location names AND
            # machine-type names (e.g. "Coating Station", "Assembly Line").
            # Score 0.70 keeps the term in candidate_fields without auto-resolving
            # above the 0.85 threshold, allowing the post-execution repair loop to
            # try alternative fields if this one returns empty.
            return 0.70, "term looks like a factory location"
        score = 0.45
        reason = "location is a supported filter"
    if field in {"machine_type", "type"} or "machine type" in description:
        if re.fullmatch(r"[A-Z0-9]{2,8}", term.strip()):
            return 0.78, "term looks like a machine type code"
        if re.search(r"\b(?:cnc|press|mill|lathe|assembly|paint|pack|weld)\b", normalized_term):
            score = max(score, 0.68)
            reason = "term may be a machine type"
    return score, reason


def _predicate_dict(
    *,
    raw_term: str,
    field_name: str | None,
    value: Any | None,
    confidence: float,
    source: str,
    reason: str,
    candidates: list[dict[str, Any]] | None = None,
    resolved: bool = False,
    sent: bool = False,
    verified: str | bool = "unknown",
) -> dict[str, Any]:
    return {
        "raw_term": raw_term,
        "normalized_term": normalize_predicate_value(str(raw_term)),
        "candidate_fields": candidates or [],
        "field": field_name,
        "value": value,
        "confidence": confidence,
        "source": source,
        "reason": reason,
        "requested": True,
        "resolved": resolved,
        "sent": sent,
        "verified": verified,
    }


def _coverage_score(predicates: list[dict[str, Any]]) -> float:
    if not predicates:
        return 1.0
    total = 0
    met = 0
    for pred in predicates:
        for key in ("requested", "resolved", "sent"):
            total += 1
            if pred.get(key):
                met += 1
    return round(met / total, 3) if total else 1.0


def _build_confirmation(
    *, entity: str, raw_term: str, candidates: list[dict[str, Any]], top_n: int = 3
) -> dict[str, Any]:
    """Build the confirmation payload for an ambiguous free-text predicate.

    ``options``     — top *top_n* candidates shown by default in the UI.
    ``all_options`` — the complete ranked list (never truncated) used by the
                      repair loop and exposed to the frontend via a
                      'show all fields' toggle.
    ``has_more``    — True when there are more candidates beyond *top_n*.
    """
    def _option(c: dict[str, Any]) -> dict[str, Any]:
        return {
            "field": c["field"],
            "value": raw_term,
            "label": f'{c["field"]}: {raw_term}',
            "confidence": round(float(c.get("confidence") or 0.0), 3),
            "reason": c.get("reason") or "",
        }

    all_opts = [_option(c) for c in candidates]
    return {
        "kind": "predicate_field_confirmation",
        "entity": entity,
        "raw_term": raw_term,
        "normalized_term": normalize_predicate_value(raw_term),
        "message": (
            f'I found "{raw_term}" in your {entity} request. '
            f"Which field should it filter?"
        ),
        "options": all_opts[:top_n],
        "all_options": all_opts,
        "has_more": len(all_opts) > top_n,
    }


def _memory_lookup(memory: dict[str, Any] | None, *, entity: str, term: str) -> dict[str, Any] | None:
    if not isinstance(memory, dict):
        return None
    normalized = normalize_predicate_value(term)
    positives = memory.get("positive_bindings") if isinstance(memory.get("positive_bindings"), list) else []
    for item in positives:
        if not isinstance(item, dict):
            continue
        if item.get("entity") == entity and normalize_predicate_value(str(item.get("term") or "")) == normalized:
            return item
    return None


def _negative_memory_fields(memory: dict[str, Any] | None, *, entity: str, term: str) -> set[str]:
    if not isinstance(memory, dict):
        return set()
    normalized = normalize_predicate_value(term)
    negatives = memory.get("negative_bindings") if isinstance(memory.get("negative_bindings"), list) else []
    fields: set[str] = set()
    for item in negatives:
        if not isinstance(item, dict):
            continue
        if item.get("entity") == entity and normalize_predicate_value(str(item.get("term") or "")) == normalized:
            field = item.get("field")
            if isinstance(field, str) and field:
                fields.add(field)
    return fields


def _negative_binding(*, entity: str, raw_term: str, field_name: str, reason: str) -> dict[str, Any]:
    return {
        "term": raw_term,
        "normalized_term": normalize_predicate_value(raw_term),
        "entity": entity,
        "field": field_name,
        "reason": reason,
        "source": "predicate_verifier",
    }


def _build_enum_clarification(*, entity: str, raw_value: str, field_name: str, field_schema: dict[str, Any]) -> str:
    allowed = ", ".join(str(value) for value in field_schema.get("enum", []) if str(value))
    return (
        f'I found {entity}s, but I could not safely map "{raw_value}" to a valid {field_name}. '
        f"Allowed {field_name} values are: {allowed}."
    )


def _build_unknown_term_clarification(*, entity: str, raw_value: str) -> str:
    return f'I couldn\'t match "{raw_value}" to any supported {entity} field or filter. Please check if it is a typo.'


async def verify_clause_against_tool(
    *,
    clause: str,
    tool: ToolInfo,
    args: dict[str, Any],
    reasoning: Any | None = None,
    memory: dict[str, Any] | None = None,
) -> ClauseVerificationResult:
    entity = _tool_entity(tool)
    repaired_args = dict(args or {})
    resolved_predicates: dict[str, Any] = {}
    filter_fields = _candidate_filter_fields(tool, clause)
    enum_fields = {
        name: schema
        for name, schema in filter_fields.items()
        if isinstance(schema.get("enum"), list) and schema.get("enum")
    }
    predicates: list[dict[str, Any]] = []

    for field, value in repaired_args.items():
        if field in filter_fields and field not in _CONTROL_FIELDS and value not in (None, ""):
            resolved_predicates[field] = value
            predicates.append(_predicate_dict(
                raw_term=str(value),
                field_name=field,
                value=value,
                confidence=1.0,
                source="prefilled",
                reason="resolved by tool selector or context memory",
                candidates=[],
                resolved=True,
                sent=True,
            ))

    for field_name, field_schema in enum_fields.items():
        if field_name in repaired_args:
            continue
        explicit_value, explicit_clarification = _explicit_enum_match(clause, field_name, field_schema)
        if explicit_clarification:
            return ClauseVerificationResult(
                args=repaired_args,
                resolved_predicates=resolved_predicates,
                unresolved_terms=[],
                clarification=_build_enum_clarification(
                    entity=entity,
                    raw_value=explicit_clarification,
                    field_name=field_name,
                    field_schema=field_schema,
                ),
                negative_bindings=[
                    _negative_binding(
                        entity=entity,
                        raw_term=explicit_clarification,
                        field_name=field_name,
                        reason="explicit enum value was not allowed",
                    )
                ],
                predicates=predicates,
            )
        if explicit_value:
            resolved_predicates[field_name] = explicit_value
            repaired_args[field_name] = explicit_value
            continue

        if field_name not in repaired_args:
            exact_matches = _exact_enum_mentions(clause, field_schema)
            if len(exact_matches) == 1:
                resolved_predicates[field_name] = exact_matches[0]
                repaired_args.setdefault(field_name, exact_matches[0])

    for field_name, value in list(resolved_predicates.items()):
        field_schema = enum_fields.get(field_name)
        if not field_schema:
            continue
        if not Draft202012Validator(field_schema).is_valid(value):
            return ClauseVerificationResult(
                args=dict(args or {}),
                resolved_predicates={},
                unresolved_terms=[],
                clarification=_build_enum_clarification(
                    entity=entity,
                    raw_value=str(value),
                    field_name=field_name,
                    field_schema=field_schema,
                ),
            )

    unresolved_terms: list[str] = []
    adjacent_phrase = _entity_adjacent_phrase(clause, entity)
    adjacent_term = _normalize_token(adjacent_phrase) if adjacent_phrase else _entity_adjacent_term(clause, entity)
    if adjacent_phrase:
        consumed_tokens = {
            _normalize_token(str(value))
            for value in resolved_predicates.values()
            if value not in (None, "")
        }
        for field in resolved_predicates.keys():
            consumed_tokens.update({_normalize_token(a) for a in _field_aliases(field)})
        
        adj_tokens = { _normalize_token(t) for t in _TOKEN_RE.findall(adjacent_phrase) }
        leftover = adj_tokens - consumed_tokens - {_normalize_token(alias) for field in filter_fields for alias in _field_aliases(field)} - _STOPWORDS - _ACTION_VERBS_FILTER
        leftover.discard(entity.lower())
        leftover.discard(entity.lower() + "s")
        if entity.lower().endswith("y"):
            leftover.discard(entity.lower()[:-1] + "ies")

        if leftover:
            raw_term = adjacent_phrase
            mem = _memory_lookup(memory, entity=entity, term=raw_term)
            negative_fields = _negative_memory_fields(memory, entity=entity, term=raw_term)
            candidate_scores: list[dict[str, Any]] = []
            if mem and isinstance(mem.get("field"), str) and mem.get("field") in filter_fields:
                field_name = str(mem["field"])
                if field_name not in negative_fields:
                    score, reason = _candidate_score(
                        clause=clause,
                        term=raw_term,
                        field_name=field_name,
                        field_schema=filter_fields[field_name],
                        source="memory",
                    )
                    candidate_scores.append({"field": field_name, "confidence": score, "reason": reason, "source": "memory"})
            else:
                explicit_matches: list[tuple[str, str]] = []
                for field_name, field_schema in filter_fields.items():
                    if field_name in negative_fields or field_name in repaired_args or field_name in resolved_predicates:
                        continue
                    explicit_value = _explicit_field_value(clause, field_name)
                    if explicit_value:
                        explicit_matches.append((field_name, explicit_value))
                        score, reason = _candidate_score(
                            clause=clause,
                            term=explicit_value,
                            field_name=field_name,
                            field_schema=field_schema,
                            source="explicit_field",
                        )
                        candidate_scores.append({"field": field_name, "confidence": score, "reason": reason, "source": "explicit_field"})
                if explicit_matches:
                    raw_term = explicit_matches[0][1]
                else:
                    for field_name, field_schema in filter_fields.items():
                        if field_name in negative_fields or field_name in _CONTROL_FIELDS or field_name in repaired_args or field_name in resolved_predicates:
                            continue
                        score, reason = _candidate_score(
                            clause=clause,
                            term=raw_term,
                            field_name=field_name,
                            field_schema=field_schema,
                            source="heuristic",
                        )
                        # Always include every plausible non-control string field —
                        # the threshold governs auto-map, NOT which fields appear.
                        if score == 0.0:
                            score = 0.15
                            reason = "plausible string filter field"
                        candidate_scores.append({"field": field_name, "confidence": score, "reason": reason, "source": "heuristic"})

            candidate_scores.sort(key=lambda item: item["confidence"], reverse=True)
            if not candidate_scores and reasoning is not None and normalize_predicate_value(raw_term) not in _VAGUE_FREE_TEXT:
                semantic = await reasoning.classify_unknown_term(
                    clause=clause,
                    term=raw_term,
                    entity=entity,
                    tool=tool,
                )
                if semantic and isinstance(semantic.get("field_name"), str):
                    field_name = semantic["field_name"]
                    if field_name in filter_fields and field_name not in _CONTROL_FIELDS and field_name not in negative_fields:
                        if field_name in enum_fields:
                            return ClauseVerificationResult(
                                args=repaired_args,
                                resolved_predicates=resolved_predicates,
                                unresolved_terms=[raw_term],
                                clarification=_build_enum_clarification(
                                    entity=entity,
                                    raw_value=raw_term,
                                    field_name=field_name,
                                    field_schema=filter_fields[field_name],
                                ),
                                negative_bindings=[
                                    _negative_binding(
                                        entity=entity,
                                        raw_term=raw_term,
                                        field_name=field_name,
                                        reason="semantic enum mapping was not an allowed value",
                                    )
                                ],
                                predicates=predicates,
                                predicate_coverage_score=_coverage_score(predicates),
                            )
                        try:
                            confidence = float(semantic.get("confidence") or 0.0)
                        except Exception:
                            confidence = 0.0
                        candidate_scores.append(
                            {
                                "field": field_name,
                                "confidence": confidence,
                                "reason": str(semantic.get("reason") or "semantic classifier"),
                                "source": "semantic",
                            }
                        )
            candidate_scores.sort(key=lambda item: item["confidence"], reverse=True)
            top = candidate_scores[0] if candidate_scores else None
            second = candidate_scores[1] if len(candidate_scores) > 1 else None
            pred = _predicate_dict(
                raw_term=raw_term,
                field_name=(top or {}).get("field") if top else None,
                value=raw_term if top else None,
                confidence=float((top or {}).get("confidence") or 0.0),
                source=str((top or {}).get("source") or "none"),
                reason=str((top or {}).get("reason") or "no supported field matched"),
                candidates=candidate_scores,
                resolved=False,
                sent=False,
            )
            if top and top["confidence"] >= 0.85 and not (second and (top["confidence"] - second["confidence"]) < 0.12):
                field_name = str(top["field"])
                resolved_predicates[field_name] = raw_term
                repaired_args.setdefault(field_name, raw_term)
                pred["field"] = field_name
                pred["value"] = raw_term
                pred["resolved"] = True
                pred["sent"] = field_name in repaired_args and repaired_args.get(field_name) not in (None, "")
                predicates.append(pred)
            elif top and top["confidence"] >= 0.55:
                # Pass the complete ranked list — _build_confirmation slices
                # to top 3 for display but keeps all_options intact for the
                # repair loop and the 'show all fields' UI toggle.
                confirmation = _build_confirmation(
                    entity=entity, raw_term=raw_term, candidates=candidate_scores
                )
                # candidate_fields must carry the FULL list so the repair loop
                # can iterate beyond the top-3 display options.
                pred["candidate_fields"] = candidate_scores
                predicates.append(pred)
                return ClauseVerificationResult(
                    args=repaired_args,
                    resolved_predicates=resolved_predicates,
                    unresolved_terms=[raw_term],
                    confirmation=confirmation,
                    predicates=predicates,
                    predicate_coverage_score=_coverage_score(predicates),
                )
            else:
                entity_aliases = {entity.lower(), entity.lower() + "s"}
                if entity.lower().endswith("y"):
                    entity_aliases.add(entity.lower()[:-1] + "ies")
                
                if raw_term.lower().strip() not in entity_aliases:
                    unresolved_terms.append(raw_term)
                    predicates.append(pred)

    # ------------------------------------------------------------------
    # Residual-phrase fallback
    # Runs when the entity word was absent from the clause so the
    # adjacent-phrase patterns above found nothing (e.g. "find all
    # Coating Station" with no trailing "machines").
    # Reuses the identical scoring + decision logic as the adjacent path.
    # Key difference: when confidence is 0.30-0.84, the best candidate is
    # committed into args so execution can proceed and the repair loop
    # (not a user confirmation prompt) resolves the ambiguity.
    # ------------------------------------------------------------------
    if not predicates and not unresolved_terms and filter_fields:
        residual_consumed: set[str] = {
            _normalize_token(str(v))
            for v in resolved_predicates.values()
            if v not in (None, "")
        }
        field_alias_set: set[str] = {
            _normalize_token(alias)
            for field in filter_fields
            for alias in _field_aliases(field)
        }
        for raw_term in _extract_residual_filter_terms(
            clause, entity, residual_consumed, field_alias_set
        ):
            neg_fields = _negative_memory_fields(memory, entity=entity, term=raw_term)
            mem2 = _memory_lookup(memory, entity=entity, term=raw_term)
            cand_scores: list[dict[str, Any]] = []
            if mem2 and isinstance(mem2.get("field"), str) and mem2["field"] in filter_fields:
                fn = str(mem2["field"])
                if fn not in neg_fields:
                    sc, rs = _candidate_score(
                        clause=clause, term=raw_term, field_name=fn,
                        field_schema=filter_fields[fn], source="memory",
                    )
                    cand_scores.append({"field": fn, "confidence": sc, "reason": rs, "source": "memory"})
            else:
                for fn, fs in filter_fields.items():
                    if fn in neg_fields or fn in _CONTROL_FIELDS or fn in repaired_args or fn in resolved_predicates:
                        continue
                    sc, rs = _candidate_score(
                        clause=clause, term=raw_term, field_name=fn,
                        field_schema=fs, source="heuristic",
                    )
                    # Always include every plausible non-control string field
                    # as a candidate regardless of score — the threshold only
                    # governs auto-map, not which options appear in the list.
                    # Give zero-scored fields a small baseline so they rank
                    # above fields that were explicitly excluded.
                    if sc == 0.0:
                        sc = 0.15
                        rs = "plausible string filter field"
                    cand_scores.append({"field": fn, "confidence": sc, "reason": rs, "source": "heuristic"})
            if not cand_scores and reasoning is not None and normalize_predicate_value(raw_term) not in _VAGUE_FREE_TEXT:
                semantic2 = await reasoning.classify_unknown_term(
                    clause=clause, term=raw_term, entity=entity, tool=tool,
                )
                if semantic2 and isinstance(semantic2.get("field_name"), str):
                    fn = semantic2["field_name"]
                    if fn in filter_fields and fn not in _CONTROL_FIELDS and fn not in neg_fields:
                        try:
                            sc = float(semantic2.get("confidence") or 0.0)
                        except Exception:
                            sc = 0.0
                        cand_scores.append({
                            "field": fn, "confidence": sc,
                            "reason": str(semantic2.get("reason") or "semantic classifier"),
                            "source": "semantic",
                        })
            cand_scores.sort(key=lambda c: c["confidence"], reverse=True)
            top2 = cand_scores[0] if cand_scores else None
            if not top2:
                # filter_fields was empty — nothing to try.
                continue
            pred2 = _predicate_dict(
                raw_term=raw_term,
                field_name=top2.get("field"),
                value=raw_term,
                confidence=float(top2.get("confidence") or 0.0),
                source=str(top2.get("source") or "heuristic"),
                reason=str(top2.get("reason") or ""),
                candidates=cand_scores,
                resolved=False,
                sent=False,
            )
            if top2["confidence"] >= 0.30:
                # Commit the best candidate into args so the step runs with a
                # real filter rather than {}.  The repair loop will swap the
                # field if the result is empty.
                fn = str(top2["field"])
                resolved_predicates[fn] = raw_term
                repaired_args.setdefault(fn, raw_term)
                pred2["field"] = fn
                pred2["value"] = raw_term
                pred2["resolved"] = True
                pred2["sent"] = repaired_args.get(fn) not in (None, "")
                predicates.append(pred2)
                # One residual term per clause is enough.
                break
    # ------------------------------------------------------------------

    if unresolved_terms:
        unresolved = unresolved_terms[0]
        negative_fields = _negative_memory_fields(memory, entity=entity, term=unresolved)
        if reasoning is not None and enum_fields and len(unresolved.split()) == 1 and normalize_predicate_value(unresolved) not in _VAGUE_FREE_TEXT:
            semantic = await reasoning.classify_unknown_term(
                clause=clause,
                term=unresolved,
                entity=entity,
                tool=tool,
            )
            if semantic and isinstance(semantic.get("field_name"), str):
                field_name = semantic["field_name"]
                field_schema = enum_fields.get(field_name)
                if field_schema and field_name not in negative_fields:
                    return ClauseVerificationResult(
                        args=repaired_args,
                        resolved_predicates=resolved_predicates,
                        unresolved_terms=unresolved_terms,
                        clarification=_build_enum_clarification(
                            entity=entity,
                            raw_value=unresolved,
                            field_name=field_name,
                            field_schema=field_schema,
                        ),
                        negative_bindings=[
                            _negative_binding(
                                entity=entity,
                                raw_term=unresolved,
                                field_name=field_name,
                                reason="semantic enum mapping was not an allowed value",
                            )
                        ],
                        predicates=predicates,
                        predicate_coverage_score=_coverage_score(predicates),
                    )
        return ClauseVerificationResult(
            args=repaired_args,
            resolved_predicates=resolved_predicates,
            unresolved_terms=unresolved_terms,
            clarification=_build_unknown_term_clarification(entity=entity, raw_value=unresolved),
            predicates=predicates,
            predicate_coverage_score=_coverage_score(predicates),
        )

    return ClauseVerificationResult(
        args=repaired_args,
        resolved_predicates=resolved_predicates,
        unresolved_terms=unresolved_terms,
        clarification=None,
        predicates=predicates,
        predicate_coverage_score=_coverage_score(predicates),
    )
