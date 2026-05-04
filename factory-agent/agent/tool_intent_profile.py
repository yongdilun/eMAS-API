from __future__ import annotations

from dataclasses import dataclass
import re

from .schemas import ToolInfo


_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")
_PATH_PARAM_RE = re.compile(r"^\{[^}]+\}$")
_ID_LIKE_RE = re.compile(r"\b[A-Z]{1,10}[-_][A-Z0-9]+(?:[-_][A-Z0-9]+)*\b|\b\d+\b", re.IGNORECASE)

_GENERIC_TOKENS = {
    "a",
    "all",
    "an",
    "and",
    "any",
    "api",
    "by",
    "create",
    "delete",
    "fetch",
    "find",
    "for",
    "get",
    "id",
    "ids",
    "inspect",
    "list",
    "lookup",
    "new",
    "of",
    "read",
    "record",
    "records",
    "show",
    "status",
    "the",
    "update",
    "view",
}

_ENTITY_TOKENS = {
    "approval",
    "approvals",
    "inventory",
    "inventories",
    "job",
    "jobs",
    "machine",
    "machines",
    "material",
    "materials",
    "product",
    "products",
    "schedule",
    "scheduling",
    "slot",
    "slots",
    "step",
    "steps",
}


@dataclass(frozen=True)
class ToolIntentProfile:
    name: str
    endpoint_root: str
    endpoint_segments: tuple[str, ...]
    action: str
    identity_tokens: frozenset[str]
    feature_tokens: frozenset[str]
    field_tokens: frozenset[str]
    has_path_id: bool
    parent_endpoint: str | None


def normalize_token(token: str) -> str:
    lowered = (token or "").strip().lower()
    if lowered.endswith("ies") and len(lowered) > 3:
        return lowered[:-3] + "y"
    if lowered.endswith("ses") and len(lowered) > 4:
        return lowered[:-2]
    if lowered.endswith("s") and len(lowered) > 3:
        return lowered[:-1]
    return lowered


def tokenize(text: str) -> set[str]:
    raw = {normalize_token(match.group(0)) for match in _TOKEN_RE.finditer(text or "")}
    return {token for token in raw if token}


def _has_identifier(text: str) -> bool:
    return bool(_ID_LIKE_RE.search(text or ""))


def _strip_identifiers(text: str) -> str:
    return _ID_LIKE_RE.sub(" ", text or "")


def _soft_token_matches(left: str, right: str) -> bool:
    if left == right:
        return True
    if len(left) < 4 or len(right) < 4:
        return False
    if left.startswith(right) or right.startswith(left):
        return True
    return len(left) >= 5 and len(right) >= 5 and left[:5] == right[:5]


def _soft_overlap(left: set[str], right: set[str]) -> set[str]:
    return {
        token
        for token in left
        if any(_soft_token_matches(token, candidate) for candidate in right)
    }


def _endpoint_segments(endpoint: str) -> tuple[str, ...]:
    parts: list[str] = []
    for raw in (endpoint or "").strip("/").split("/"):
        if not raw or _PATH_PARAM_RE.match(raw):
            continue
        parts.extend(sorted(tokenize(raw)))
    return tuple(parts)


def _endpoint_root(endpoint: str) -> str:
    for raw in (endpoint or "").strip("/").split("/"):
        if raw and not _PATH_PARAM_RE.match(raw):
            return normalize_token(raw)
    return ""


def _schema_text(schema: dict | None) -> str:
    if not isinstance(schema, dict):
        return ""
    parts: list[str] = []
    for key in ("title", "description"):
        value = schema.get(key)
        if isinstance(value, str):
            parts.append(value)
    enum_values = schema.get("enum")
    if isinstance(enum_values, list):
        parts.extend(str(value) for value in enum_values if str(value))
    properties = schema.get("properties")
    if isinstance(properties, dict):
        for name, subschema in properties.items():
            parts.append(str(name))
            parts.append(_schema_text(subschema if isinstance(subschema, dict) else {}))
    items = schema.get("items")
    if isinstance(items, dict):
        parts.append(_schema_text(items))
    return " ".join(part for part in parts if part)


def _action_for_method(method: str) -> str:
    method = (method or "").upper()
    if method == "GET":
        return "read"
    if method == "POST":
        return "create"
    if method in {"PUT", "PATCH"}:
        return "update"
    if method == "DELETE":
        return "delete"
    return ""


def _parent_endpoint(endpoint: str) -> str | None:
    parts = [part for part in (endpoint or "").strip("/").split("/") if part]
    if len(parts) <= 2:
        return None
    if not _PATH_PARAM_RE.match(parts[-1]):
        parent = parts[:-1]
    else:
        parent = parts[:-2]
    if not parent:
        return None
    return "/" + "/".join(parent)


def build_tool_intent_profile(tool: ToolInfo) -> ToolIntentProfile:
    endpoint_segments = _endpoint_segments(tool.endpoint)
    field_text = " ".join(
        [
            " ".join(tool.path_params or []),
            " ".join(tool.query_params or []),
            " ".join(tool.body_fields or []),
            " ".join(tool.required_body_fields or []),
            _schema_text(tool.input_schema),
        ]
    )
    identity_tokens = frozenset(
        tokenize(
            " ".join(
                [
                    tool.name.replace("__", " ").replace("_", " "),
                    tool.description,
                    tool.endpoint.replace("/", " "),
                    " ".join(tool.capability_tags or []),
                ]
            )
        )
    )
    field_tokens = frozenset(tokenize(field_text))
    feature_tokens = frozenset(
        token
        for token in identity_tokens
        if token not in _GENERIC_TOKENS and token not in _ENTITY_TOKENS and not token.isdigit()
    )
    return ToolIntentProfile(
        name=tool.name,
        endpoint_root=_endpoint_root(tool.endpoint),
        endpoint_segments=endpoint_segments,
        action=_action_for_method(tool.method),
        identity_tokens=identity_tokens,
        feature_tokens=feature_tokens,
        field_tokens=field_tokens,
        has_path_id=bool(tool.path_params or "{" in (tool.endpoint or "")),
        parent_endpoint=_parent_endpoint(tool.endpoint),
    )


def intent_feature_tokens(intent: str) -> set[str]:
    tokens = tokenize(_strip_identifiers(intent))
    return {
        token
        for token in tokens
        if token not in _GENERIC_TOKENS and token not in _ENTITY_TOKENS and not token.isdigit()
    }


def profile_match_score(intent: str, tool: ToolInfo) -> int:
    intent_tokens = tokenize(intent)
    if not intent_tokens:
        return 0
    profile = build_tool_intent_profile(tool)
    feature_tokens = intent_feature_tokens(intent)
    score = 0

    identity_overlap = intent_tokens & set(profile.identity_tokens)
    feature_overlap = feature_tokens & set(profile.feature_tokens)
    soft_feature_overlap = _soft_overlap(feature_tokens, set(profile.feature_tokens)) - feature_overlap
    endpoint_overlap = intent_tokens & set(profile.endpoint_segments)
    field_overlap = intent_tokens & set(profile.field_tokens)
    field_feature_overlap = feature_tokens & set(profile.field_tokens)
    covered_features = feature_overlap | soft_feature_overlap | field_feature_overlap

    score += len(identity_overlap) * 3
    score += len(endpoint_overlap) * 5
    score += len(feature_overlap) * 9
    score += len(soft_feature_overlap) * 7
    score += len(field_overlap) * 2
    score += len(field_feature_overlap) * 6

    if feature_tokens and covered_features == feature_tokens:
        score += 12
    if feature_tokens and not covered_features:
        score -= 12
    elif feature_tokens and profile.feature_tokens and covered_features != feature_tokens:
        score -= min(10, 2 * len(profile.feature_tokens))

    root = profile.endpoint_root
    if root and root in intent_tokens:
        score += 8
    if root and root not in intent_tokens and feature_tokens and not feature_overlap and not soft_feature_overlap:
        score -= 3

    # A request for a root entity ID should prefer that entity's endpoint over
    # secondary endpoints that merely mention the entity in a child segment.
    if "product" in intent_tokens and root and root != "product" and "process" not in intent_tokens and not feature_overlap and not soft_feature_overlap:
        score -= 14
    if "process" in intent_tokens and "process" in profile.identity_tokens:
        score += 10

    if profile.has_path_id:
        if _has_identifier(intent):
            score += 2
        else:
            score -= 24
    elif profile.action == "read":
        if {"all", "list"} & intent_tokens:
            score += 6
        if not _has_identifier(intent):
            score += 3

    return score


def tool_covers_descriptive_terms(intent: str, tool: ToolInfo) -> bool:
    features = intent_feature_tokens(intent)
    if not features:
        return False
    profile = build_tool_intent_profile(tool)
    return _soft_overlap(features, set(profile.identity_tokens)) == features


def child_tools_for_parent(parent: ToolInfo, tools: list[ToolInfo]) -> list[ToolInfo]:
    parent_endpoint = parent.endpoint
    return [
        tool
        for tool in tools
        if tool is not parent
        and tool.method == "GET"
        and tool.endpoint.startswith(parent_endpoint.rstrip("/") + "/")
    ]
