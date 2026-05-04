from __future__ import annotations

import re
from typing import Any


def _is_scalar(value: Any) -> bool:
    return value is None or isinstance(value, (str, int, float, bool))


def _title_from_tool_name(tool_name: str | None) -> str:
    raw = str(tool_name or "results").strip().replace("__", " ").replace("_", " ").replace("-", " ")
    words = [word for word in raw.split() if word and word.lower() not in {"get", "post", "put", "patch", "delete"}]
    if not words:
        return "Results"
    return " ".join(word.capitalize() for word in words[:4])


def _label_for_key(key: str) -> str:
    parts = [part for part in str(key).replace("-", "_").split("_") if part]
    if not parts:
        return str(key)
    return " ".join(part.upper() if part.lower() == "id" else part.capitalize() for part in parts)


def _normalize_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def _field_aliases(key: str) -> list[str]:
    raw = str(key or "")
    spaced = re.sub(r"[_-]+", " ", raw).strip()
    return [raw, spaced]


def _requested_keys_from_intent(intent: str | None, keys: list[str]) -> list[str]:
    text = str(intent or "").lower()
    if not text:
        return []

    matches: list[tuple[int, str]] = []
    compact_text = _normalize_token(text)
    for key in keys:
        positions: list[int] = []
        for alias in _field_aliases(key):
            alias_text = alias.lower()
            if not alias_text:
                continue
            direct = text.find(alias_text)
            if direct >= 0:
                positions.append(direct)
                continue
            compact_alias = _normalize_token(alias_text)
            compact_pos = compact_text.find(compact_alias) if compact_alias else -1
            if compact_pos >= 0:
                positions.append(compact_pos)
        if positions:
            matches.append((min(positions), key))

    return [key for _pos, key in sorted(matches, key=lambda item: item[0])]


def _analysis_keys(result: dict[str, Any], keys: list[str]) -> list[str]:
    available = set(keys)
    selected: list[str] = []
    analysis = result.get("_analysis")
    if not isinstance(analysis, dict):
        return selected
    for item in analysis.get("results") or []:
        if not isinstance(item, dict):
            continue
        field = str(item.get("field") or "")
        if field in available and field not in selected:
            selected.append(field)
    return selected


def _ordered_table_keys(
    rows: list[dict[str, Any]],
    *,
    result: dict[str, Any],
    intent: str | None,
    max_columns: int,
) -> list[str]:
    seen_keys: list[str] = []
    for row in rows:
        for key, value in row.items():
            if _is_scalar(value) and str(key) not in seen_keys:
                seen_keys.append(str(key))

    requested = _requested_keys_from_intent(intent, seen_keys)
    analysis_fields = _analysis_keys(result, seen_keys)
    ordered: list[str] = []
    source_keys = [*requested, *analysis_fields] if requested else [*analysis_fields, *seen_keys]
    for key in source_keys:
        if key in seen_keys and key not in ordered:
            ordered.append(key)
        if len(ordered) >= max_columns:
            break
    return ordered


def extract_table_from_result(
    *,
    tool_name: str | None,
    result: dict[str, Any] | None,
    intent: str | None = None,
    max_rows: int = 20,
    max_columns: int = 8,
) -> dict[str, Any] | None:
    if not isinstance(result, dict):
        return None

    rows_source = None
    for key in ("data", "items"):
        value = result.get(key)
        if isinstance(value, list) and value:
            rows_source = value
            break
    if not isinstance(rows_source, list) or not rows_source:
        return None

    dict_rows = [row for row in rows_source if isinstance(row, dict)]
    if len(dict_rows) < 2:
        return None

    candidate_keys = _ordered_table_keys(dict_rows, result=result, intent=intent, max_columns=max_columns)
    if not candidate_keys:
        return None

    table_rows: list[dict[str, Any]] = []
    for row in dict_rows[:max_rows]:
        table_rows.append({key: row.get(key) for key in candidate_keys})

    presentation = {
        "render_hint": "table",
        "table": {
            "title": _title_from_tool_name(tool_name),
            "columns": [{"key": key, "label": _label_for_key(key)} for key in candidate_keys],
            "rows": table_rows,
            "total_rows": len(dict_rows),
            "displayed_rows": len(table_rows),
        },
    }
    analysis = result.get("_analysis")
    if isinstance(analysis, dict) and isinstance(analysis.get("facts"), list) and analysis["facts"]:
        presentation["analysis"] = {
            "facts": [str(fact) for fact in analysis["facts"][:6]],
            "results": analysis.get("results") if isinstance(analysis.get("results"), list) else [],
        }
    return presentation
