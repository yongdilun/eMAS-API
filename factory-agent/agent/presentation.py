from __future__ import annotations

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


def extract_table_from_result(
    *,
    tool_name: str | None,
    result: dict[str, Any] | None,
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

    candidate_keys: list[str] = []
    first_row = dict_rows[0]
    for key, value in first_row.items():
        if _is_scalar(value):
            candidate_keys.append(str(key))
        if len(candidate_keys) >= max_columns:
            break
    if not candidate_keys:
        return None

    table_rows: list[dict[str, Any]] = []
    for row in dict_rows[:max_rows]:
        table_rows.append({key: row.get(key) for key in candidate_keys})

    return {
        "render_hint": "table",
        "table": {
            "title": _title_from_tool_name(tool_name),
            "columns": [{"key": key, "label": _label_for_key(key)} for key in candidate_keys],
            "rows": table_rows,
            "total_rows": len(dict_rows),
            "displayed_rows": len(table_rows),
        },
    }
