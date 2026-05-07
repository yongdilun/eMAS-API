from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"

ID_PATTERNS: dict[str, dict[str, str]] = {
    "proposal_id": {"entity": "proposal", "prefix": "AIPROP-", "pattern": r"^AIPROP-[A-Za-z0-9-]+$"},
    "approval_id": {"entity": "approval", "prefix": "CHAPPR-", "pattern": r"^CHAPPR-[A-Za-z0-9-]+$"},
    "arrival_id": {"entity": "arrival", "prefix": "ARR-", "pattern": r"^ARR-[A-Za-z0-9-]+$"},
    "formula_id": {"entity": "formula", "prefix": "F-", "pattern": r"^F-[A-Za-z0-9-]+$"},
    "material_id": {"entity": "inventory", "prefix": "MAT-", "pattern": r"^MAT-[A-Za-z0-9-]+$"},
    "job_id": {"entity": "job", "prefix": "JOB-", "pattern": r"^JOB-[A-Za-z0-9-]+$"},
    "job_step_id": {"entity": "step", "prefix": "JS-", "pattern": r"^JS-[A-Za-z0-9-]+$"},
    "machine_id": {"entity": "machine", "prefix": "M-", "pattern": r"^M-[A-Za-z0-9-]+$"},
    "process_id": {"entity": "process", "prefix": "PRC-", "pattern": r"^PRC-[A-Za-z0-9-]+$"},
    "step_id": {"entity": "step", "prefix": "STP-", "pattern": r"^STP-[A-Za-z0-9-]+$"},
    "product_id": {"entity": "product", "prefix": "P-", "pattern": r"^P-[A-Za-z0-9-]+$"},
    "slot_id": {"entity": "slot", "prefix": "SLOT-", "pattern": r"^SLOT-[A-Za-z0-9-]+$"},
}

ENTITY_TO_FIELD = {meta["entity"]: field for field, meta in ID_PATTERNS.items() if field != "step_id"}

CREATE_ID_FIELDS = {
    "dto.CreateFormulaRequest": "formula_id",
    "dto.CreateMachineRequest": "machine_id",
    "dto.CreateMaterialRequest": "material_id",
    "dto.CreateProcessRequest": "process_id",
    "dto.CreateProductRequest": "product_id",
}


def _apply_id_metadata(schema: dict[str, Any], field_name: str) -> None:
    meta = ID_PATTERNS.get(field_name)
    if not meta:
        return
    schema.setdefault("type", "string")
    schema["pattern"] = meta["pattern"]
    schema["x-ai-entity"] = meta["entity"]
    schema["x-ai-id-prefix"] = meta["prefix"]
    schema["x-ai-id-field"] = field_name


def _walk_schema(node: Any, *, field_name: str | None = None) -> None:
    if isinstance(node, dict):
        if field_name:
            _apply_id_metadata(node, field_name)
        props = node.get("properties")
        if isinstance(props, dict):
            for name, child in props.items():
                _walk_schema(child, field_name=str(name))
        items = node.get("items")
        if isinstance(items, dict):
            _walk_schema(items)
        for key in ("allOf", "oneOf", "anyOf"):
            parts = node.get(key)
            if isinstance(parts, list):
                for part in parts:
                    _walk_schema(part)
    elif isinstance(node, list):
        for child in node:
            _walk_schema(child)


def _infer_path_id_field(path: str, param: dict[str, Any]) -> str | None:
    name = str(param.get("name") or "")
    if name != "id":
        return name if name in ID_PATTERNS else None
    description = str(param.get("description") or "").lower()
    for entity, field in ENTITY_TO_FIELD.items():
        if entity in description:
            return field
    path_lower = path.lower()
    if "expected-arrivals" in path_lower:
        return "arrival_id"
    if "proposals" in path_lower:
        return "proposal_id"
    if "approvals" in path_lower:
        return "approval_id"
    for segment, field in [
        ("jobs", "job_id"),
        ("machines", "machine_id"),
        ("products", "product_id"),
        ("materials", "material_id"),
        ("processes", "process_id"),
        ("formulas", "formula_id"),
        ("job-steps", "job_step_id"),
        ("slots", "slot_id"),
    ]:
        if f"/{segment}/" in path_lower or path_lower.endswith(f"/{segment}/{{id}}"):
            return field
    return None


def enrich(spec: dict[str, Any]) -> dict[str, Any]:
    definitions = spec.get("definitions")
    if isinstance(definitions, dict):
        for schema in definitions.values():
            _walk_schema(schema)
    components = spec.get("components")
    if isinstance(components, dict):
        for group in components.values():
            if isinstance(group, dict):
                for schema in group.values():
                    _walk_schema(schema)

    if isinstance(definitions, dict):
        for definition, id_field in CREATE_ID_FIELDS.items():
            schema = definitions.get(definition)
            if not isinstance(schema, dict):
                continue
            required = schema.get("required")
            if isinstance(required, list) and id_field in required:
                schema["required"] = [field for field in required if field != id_field]
            prop = (schema.get("properties") or {}).get(id_field)
            if isinstance(prop, dict):
                prop["description"] = (prop.get("description") or "Generated when omitted.").strip()
                prop["x-ai-generated"] = True

    paths = spec.get("paths")
    if isinstance(paths, dict):
        for path, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue
            for operation in path_item.values():
                if not isinstance(operation, dict):
                    continue
                for param in operation.get("parameters") or []:
                    if not isinstance(param, dict):
                        continue
                    if param.get("in") not in {"path", "query"}:
                        continue
                    field = _infer_path_id_field(str(path), param)
                    if field:
                        _apply_id_metadata(param, field)
                    schema = param.get("schema")
                    if isinstance(schema, dict):
                        _walk_schema(schema, field_name=field)
    return spec


def update_json_and_yaml() -> dict[str, Any]:
    json_path = DOCS / "swagger.json"
    yaml_path = DOCS / "swagger.yaml"
    spec = enrich(json.loads(json_path.read_text(encoding="utf-8")))
    json_path.write_text(json.dumps(spec, indent=4, ensure_ascii=False) + "\n", encoding="utf-8")
    yaml_path.write_text(yaml.safe_dump(spec, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return spec


def update_docs_go(spec: dict[str, Any]) -> None:
    docs_go = DOCS / "docs.go"
    text = docs_go.read_text(encoding="utf-8")
    match = re.search(r"const docTemplate = `(?P<body>.*)`\s+var SwaggerInfo", text, flags=re.S)
    if not match:
        return
    body = match.group("body")
    parseable = body.replace('"schemes": {{ marshal .Schemes }}', '"schemes": []')
    try:
        parsed = json.loads(parseable)
    except json.JSONDecodeError:
        return
    enriched = enrich(parsed)
    rendered = json.dumps(enriched, indent=4, ensure_ascii=False)
    rendered = rendered.replace('"schemes": []', '"schemes": {{ marshal .Schemes }}')
    updated = text[: match.start("body")] + rendered + text[match.end("body") :]
    docs_go.write_text(updated, encoding="utf-8")


def main() -> None:
    spec = update_json_and_yaml()
    update_docs_go(spec)


if __name__ == "__main__":
    main()
