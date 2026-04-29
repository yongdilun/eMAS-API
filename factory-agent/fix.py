import sys
path = 'agent/reasoning_pipeline.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old_block = """        for tool in tools:
            out.append(
                {
                    "name": tool.name,
                    "method": tool.method,
                    "endpoint": tool.endpoint,
                    "read_only": tool.is_read_only,
                    "requires_approval": tool.requires_approval,
                    "required_fields": list((tool.input_schema or {}).get("required", [])),
                    "prefilled_args": prefilled_by_tool.get(tool.name, {}),
                    "missing_required": missing_by_tool.get(tool.name, []),
                    "capability_tags": tool.capability_tags,
                }
            )"""

new_block = """        for tool in tools:
            required_fields = list((tool.input_schema or {}).get("required", []))
            optional_args = {}
            for field, field_schema in (tool.input_schema or {}).get("properties", {}).items():
                if field not in required_fields:
                    opt_meta = {}
                    if "type" in field_schema:
                        opt_meta["type"] = field_schema["type"]
                    if "enum" in field_schema:
                        opt_meta["enum"] = field_schema["enum"]
                    if "description" in field_schema:
                        opt_meta["description"] = field_schema["description"]
                    if opt_meta:
                        optional_args[field] = opt_meta

            out.append(
                {
                    "name": tool.name,
                    "method": tool.method,
                    "endpoint": tool.endpoint,
                    "read_only": tool.is_read_only,
                    "requires_approval": tool.requires_approval,
                    "required_fields": required_fields,
                    "optional_args": optional_args,
                    "prefilled_args": prefilled_by_tool.get(tool.name, {}),
                    "missing_required": missing_by_tool.get(tool.name, []),
                    "capability_tags": tool.capability_tags,
                }
            )"""

if old_block in content:
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content.replace(old_block, new_block))
    print('Replaced successfully')
else:
    print('Block not found')
