import json
import shutil
from pathlib import Path

import main  # noqa: F401

from agent.prompting import get_plan_draft_json_schema
from agent.telemetry import log_llm_prompt, log_llm_prompt_skipped


def test_plan_draft_json_schema_has_expected_shape():
    schema = get_plan_draft_json_schema()
    assert isinstance(schema, dict)
    assert "properties" in schema
    assert "steps" in schema["properties"]
    assert "plan_explanation" in schema["properties"]
    assert "risk_summary" in schema["properties"]


def test_log_llm_prompt_writes_jsonl_debug_log(monkeypatch):
    temp_dir = Path("factory-agent/tests/.prompt-log-test")
    try:
        shutil.rmtree(temp_dir, ignore_errors=True)
        log_path = temp_dir / "debug" / "prompts.log"
        monkeypatch.setenv("FACTORY_AGENT_DEBUG_LOG", str(log_path))

        log_llm_prompt(
            component="planner",
            backend="langchain",
            model="test-model",
            prompt="Prompt body here",
            metadata={"attempt": "structured_output", "session_id": "sess-1"},
        )

        assert log_path.exists()
        lines = log_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        payload = json.loads(lines[0])
        assert payload["event"] == "llm_prompt"
        assert payload["component"] == "planner"
        assert payload["backend"] == "langchain"
        assert payload["model"] == "test-model"
        assert payload["prompt"] == "Prompt body here"
        assert payload["attempt"] == "structured_output"
        assert payload["session_id"] == "sess-1"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_log_llm_prompt_skipped_writes_jsonl_debug_log(monkeypatch):
    temp_dir = Path("factory-agent/tests/.prompt-log-test-skipped")
    try:
        shutil.rmtree(temp_dir, ignore_errors=True)
        log_path = temp_dir / "debug" / "prompts.log"
        monkeypatch.setenv("FACTORY_AGENT_DEBUG_LOG", str(log_path))

        log_llm_prompt_skipped(
            component="planner",
            backend="legacy",
            reason="planner_backend=legacy",
            metadata={"intent": "Check machine 5 status", "scoped_tool_count": 2},
        )

        assert log_path.exists()
        lines = log_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        payload = json.loads(lines[0])
        assert payload["event"] == "llm_prompt_skipped"
        assert payload["component"] == "planner"
        assert payload["backend"] == "legacy"
        assert payload["reason"] == "planner_backend=legacy"
        assert payload["intent"] == "Check machine 5 status"
        assert payload["scoped_tool_count"] == 2
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
