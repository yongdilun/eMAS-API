from agent.toolgen import tools_from_openapi


def test_tools_from_openapi_infers_request_body_schema():
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/machines/{id}": {
                "patch": {
                    "operationId": "patch_machine",
                    "summary": "Update machine",
                    "parameters": [
                        {"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {"status": {"type": "string"}, "reason": {"type": "string"}},
                                    "required": ["status"],
                                }
                            }
                        },
                    },
                }
            }
        },
    }

    tools = tools_from_openapi(spec)
    assert len(tools) == 1
    schema = tools[0].input_schema
    assert schema["type"] == "object"
    assert set(schema["properties"].keys()) == {"id", "status", "reason"}
    assert set(schema["required"]) == {"id", "status"}


def test_tools_from_openapi_resolves_body_schema_refs():
    spec = {
        "openapi": "3.0.0",
        "components": {
            "schemas": {
                "CreateJobRequest": {
                    "type": "object",
                    "properties": {"machine_id": {"type": "integer"}, "priority": {"type": "string"}},
                    "required": ["machine_id"],
                }
            }
        },
        "paths": {
            "/jobs": {
                "post": {
                    "operationId": "create_job",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {"schema": {"$ref": "#/components/schemas/CreateJobRequest"}}
                        },
                    },
                }
            }
        },
    }

    tools = tools_from_openapi(spec)
    schema = tools[0].input_schema
    assert "machine_id" in schema["properties"]
    assert "priority" in schema["properties"]
    assert "machine_id" in schema["required"]


def test_tools_from_openapi_marks_path_params_required_even_if_flag_missing():
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/machines/{id}": {
                "get": {
                    "operationId": "get_machine",
                    "summary": "Get machine",
                    "parameters": [
                        {"name": "id", "in": "path", "schema": {"type": "string"}}
                    ],
                }
            }
        },
    }

    tools = tools_from_openapi(spec)
    assert len(tools) == 1
    schema = tools[0].input_schema
    assert schema["properties"]["id"]["type"] == "string"
    assert "id" in schema["required"]
