from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from typing import Any

import requests
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from models import Tool, ToolRegistryMeta, generate_uuid


@dataclass(frozen=True)
class ToolgenResult:
    tool_count: int
    tools_md_hash: str


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _resolve_ref(spec: dict[str, Any], ref: str) -> dict[str, Any]:
    if not ref.startswith("#/"):
        return {}
    node: Any = spec
    for token in ref[2:].split("/"):
        if not isinstance(node, dict):
            return {}
        node = node.get(token)
        if node is None:
            return {}
    return node if isinstance(node, dict) else {}


def _resolve_schema(spec: dict[str, Any], schema: dict[str, Any] | None) -> dict[str, Any]:
    if not schema:
        return {"type": "object", "properties": {}}
    if "$ref" in schema:
        resolved = _resolve_ref(spec, str(schema["$ref"]))
        return _resolve_schema(spec, resolved)
    normalized: dict[str, Any] = dict(schema)
    if "allOf" in normalized and isinstance(normalized["allOf"], list):
        merged: dict[str, Any] = {"type": "object", "properties": {}, "required": []}
        for part in normalized["allOf"]:
            resolved_part = _resolve_schema(spec, part)
            if resolved_part.get("type") == "object":
                merged["properties"].update(resolved_part.get("properties", {}))
                merged["required"].extend(resolved_part.get("required", []))
        merged["required"] = sorted(set(merged["required"]))
        return merged
    return normalized


def _merge_object_schema(
    base: dict[str, Any],
    addition: dict[str, Any],
    *,
    prefix: str | None = None,
    mark_required: bool = True,
) -> None:
    if addition.get("type") != "object":
        if prefix:
            base.setdefault("properties", {})[prefix] = addition
            if mark_required:
                base.setdefault("required", []).append(prefix)
        return

    for name, prop_schema in (addition.get("properties") or {}).items():
        key = f"{prefix}_{name}" if prefix else name
        base.setdefault("properties", {})[key] = prop_schema
    for required_name in addition.get("required") or []:
        key = f"{prefix}_{required_name}" if prefix else required_name
        base.setdefault("required", []).append(key)


def _resolve_parameter(spec: dict[str, Any], param: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(param, dict):
        return {}
    if "$ref" in param:
        resolved = _resolve_ref(spec, str(param["$ref"]))
        return _resolve_parameter(spec, resolved)
    return dict(param)


def _merge_body_schema(
    input_schema: dict[str, Any],
    param_sources: dict[str, str],
    body_schema: dict[str, Any] | None,
    *,
    body_required: bool,
) -> dict[str, Any] | None:
    if not body_schema:
        return None
    if body_schema.get("type") == "object":
        _merge_object_schema(input_schema, body_schema)
        for field_name in (body_schema.get("properties") or {}).keys():
            param_sources[str(field_name)] = "body"
    else:
        _merge_object_schema(
            input_schema,
            body_schema,
            prefix="body",
            mark_required=body_required,
        )
        param_sources["body"] = "body"
        if body_required:
            input_schema.setdefault("required", []).append("body")
    return body_schema


def _infer_input_schema(
    spec: dict[str, Any],
    operation: dict[str, Any],
    method: str,
    *,
    path_parameters: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    input_schema: dict[str, Any] = {"type": "object", "properties": {}, "required": []}
    path_params: list[str] = []
    query_params: list[str] = []
    param_sources: dict[str, str] = {}
    body_schema: dict[str, Any] | None = None

    all_parameters = [*(path_parameters or []), *(operation.get("parameters", []) or [])]
    for raw_param in all_parameters:
        param = _resolve_parameter(spec, raw_param)
        schema = param.get("schema")
        if not schema and "type" in param:
            schema = {"type": param.get("type", "string")}
            if isinstance(param.get("enum"), list):
                schema["enum"] = list(param.get("enum") or [])
        resolved = _resolve_schema(spec, schema)
        param_name = str(param.get("name", "param"))
        location = str(param.get("in", "")).lower()

        if location == "body":
            body_schema = _merge_body_schema(
                input_schema,
                param_sources,
                resolved,
                body_required=bool(param.get("required")),
            ) or body_schema
            continue

        if location == "formdata":
            if not resolved:
                resolved = {"type": str(param.get("type", "string") or "string")}
            input_schema["properties"][param_name] = resolved
            param_sources[param_name] = "body"
            if bool(param.get("required")):
                input_schema["required"].append(param_name)
            continue

        input_schema["properties"][param_name] = resolved
        param_sources[param_name] = location or "query"
        if location == "path":
            path_params.append(param_name)
        elif location == "query":
            query_params.append(param_name)
        if bool(param.get("required")) or location == "path":
            input_schema["required"].append(param_name)

    request_body = operation.get("requestBody")
    if isinstance(request_body, dict):
        request_body = _resolve_schema(spec, request_body)
    if isinstance(request_body, dict):
        content = request_body.get("content", {}) or {}
        for content_type in ("application/json", "application/*+json", "*/*"):
            maybe = content.get(content_type)
            if isinstance(maybe, dict):
                body_schema = _resolve_schema(spec, maybe.get("schema"))
                if body_schema:
                    break
        if not body_schema and isinstance(content, dict):
            for media in content.values():
                if isinstance(media, dict):
                    candidate = _resolve_schema(spec, media.get("schema"))
                    if candidate:
                        body_schema = candidate
                        break
        if body_schema:
            body_schema = _merge_body_schema(
                input_schema,
                param_sources,
                body_schema,
                body_required=bool(request_body.get("required")),
            ) or body_schema

    input_schema["required"] = sorted(set(input_schema.get("required", [])))
    if not input_schema["required"]:
        input_schema.pop("required", None)
    input_schema["x-path-params"] = path_params
    input_schema["x-query-params"] = query_params
    input_schema["x-param-sources"] = param_sources
    if body_schema:
        input_schema["x-body-schema"] = body_schema
        if body_schema.get("type") == "object":
            input_schema["x-body-fields"] = sorted((body_schema.get("properties") or {}).keys())
            input_schema["x-body-required"] = sorted(set(body_schema.get("required", []) or []))
        else:
            input_schema["x-body-fields"] = ["body"]
            input_schema["x-body-required"] = ["body"] if request_body.get("required") else []
    return input_schema


def _operation_tokens(path: str, method: str, operation: dict[str, Any]) -> list[str]:
    raw = " ".join(
        [
            path.replace("/", " ").replace("{", " ").replace("}", " "),
            str(operation.get("summary", "") or ""),
            str(operation.get("description", "") or ""),
            str(operation.get("operationId", "") or ""),
            " ".join(str(tag) for tag in (operation.get("tags") or []) if str(tag)),
        ]
    ).lower()
    tokens = [token for token in re.split(r"[^a-z0-9]+", raw) if token]
    tags: list[str] = []

    if "machine" in tokens or "machines" in tokens:
        tags.append("machine")
    if "job" in tokens or "jobs" in tokens or "schedule" in tokens or "scheduling" in tokens:
        tags.append("job")
    if "inventory" in tokens or "material" in tokens or "materials" in tokens or "stock" in tokens:
        tags.append("inventory")
    if "approval" in tokens or "approvals" in tokens:
        tags.append("approval")
    if "proposal" in tokens or "proposals" in tokens:
        tags.append("proposal")

    lowered_method = method.lower()
    if lowered_method == "get":
        tags.append("lookup" if "{id}" in path else "list")
        if any(token in tokens for token in ("status", "state")):
            tags.append("status")
        if "pending" in tokens:
            tags.append("pending")
    elif lowered_method == "post":
        tags.append("create")
    elif lowered_method in {"put", "patch"}:
        tags.append("update")
    elif lowered_method == "delete":
        tags.append("delete")

    for token in ("pending", "approve", "reject", "maintenance", "utilization", "capability", "downtime", "alerts"):
        if token in tokens:
            tags.append(token)

    seen: set[str] = set()
    return [tag for tag in tags if not (tag in seen or seen.add(tag))]


def _build_tool_markdown(tool: Tool) -> str:
    input_schema_str = json.dumps(tool.input_schema, indent=2, ensure_ascii=False)
    output_schema_str = json.dumps(tool.output_schema, indent=2, ensure_ascii=False) if tool.output_schema else "{}"

    return (
        f"## {tool.name}\n"
        f"**Description**: {tool.description}\n"
        f"**Method**: {tool.method}\n"
        f"**Endpoint**: {tool.endpoint}\n"
        f"**Capability Tags**: {tool.capability_tags}\n"
        f"**Requires Approval**: {str(tool.requires_approval).lower()}\n"
        f"**Side Effect Level**: {tool.side_effect_level}\n"
        f"**Read Only**: {str(tool.is_read_only).lower()}\n"
        f"**Input Schema**:\n"
        f"`json\n{input_schema_str}\n`\n"
        f"**Output Schema**:\n"
        f"`json\n{output_schema_str}\n`\n"
        f"---\n"
    )


def render_tools_md(tools: list[Tool]) -> str:
    return "# Available Tools\n\n" + "".join(_build_tool_markdown(t) for t in tools)


def fetch_openapi_spec(*, openapi_url: str, local_swagger_json_path: str | None = None, force_local: bool = False) -> dict[str, Any]:
    if force_local:
        if not local_swagger_json_path or not os.path.exists(local_swagger_json_path):
            raise FileNotFoundError(f"No local swagger.json found at {local_swagger_json_path}")
        with open(local_swagger_json_path, "r", encoding="utf-8") as f:
            return json.load(f)

    try:
        resp = requests.get(openapi_url, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        if local_swagger_json_path and os.path.exists(local_swagger_json_path):
            with open(local_swagger_json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        raise


def tools_from_openapi(spec: dict[str, Any]) -> list[Tool]:
    tools: list[Tool] = []
    for path, path_item in (spec.get("paths", {}) or {}).items():
        shared_parameters = [
            _resolve_parameter(spec, param)
            for param in ((path_item or {}).get("parameters", []) or [])
            if isinstance(_resolve_parameter(spec, param), dict)
        ]
        for method, operation in (path_item or {}).items():
            if method.lower() not in ["get", "post", "put", "patch", "delete"]:
                continue

            tool_name = operation.get("operationId", f"{method}_{path.replace('/', '_')}").lower()
            description = operation.get("summary", "") or operation.get("description", "")

            input_schema = _infer_input_schema(spec, operation, method, path_parameters=shared_parameters)

            capability_tags = _operation_tokens(path, method, operation)

            is_read_only = method.lower() == "get"
            requires_approval = not is_read_only
            side_effect_level = "NONE" if is_read_only else "HIGH"

            tools.append(
                Tool(
                    tool_id=generate_uuid(),
                    name=tool_name,
                    description=description,
                    endpoint=path,
                    method=method.upper(),
                    version=1,
                    schema_version=1,
                    input_schema=input_schema,
                    output_schema={"type": "object"},
                    is_read_only=is_read_only,
                    requires_approval=requires_approval,
                    side_effect_level=side_effect_level,
                    capability_tags=json.dumps(capability_tags),
                )
            )
    return tools


async def write_tools_md_and_meta(
    db: AsyncSession,
    *,
    tools: list[Tool],
    tools_md_path: str,
    replace_db: bool = True,
) -> ToolgenResult:
    # DB update (best-effort; same behavior as existing script).
    if replace_db:
        await db.execute(text("DELETE FROM tools"))
        for tool in tools:
            db.add(tool)
        await db.commit()
    else:
        for tool in tools:
            db.merge(tool)
        await db.commit()

    # tools.md
    content = render_tools_md(tools)
    with open(tools_md_path, "w", encoding="utf-8") as f:
        f.write(content)

    tools_md_hash = _sha256_hex(content.encode("utf-8"))

    meta = (await db.execute(select(ToolRegistryMeta).where(ToolRegistryMeta.meta_id == 1))).scalars().first()
    if not meta:
        meta = ToolRegistryMeta(meta_id=1, tools_md_hash=tools_md_hash)
        db.add(meta)
    else:
        meta.tools_md_hash = tools_md_hash
    await db.commit()

    return ToolgenResult(tool_count=len(tools), tools_md_hash=tools_md_hash)
