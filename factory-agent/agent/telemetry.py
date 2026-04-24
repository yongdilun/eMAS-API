from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any


LOGGER_NAME = "factory_agent"


def setup_logging() -> None:
    logger = logging.getLogger(LOGGER_NAME)
    if logger.handlers:
        return
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def _debug_log_path() -> str | None:
    repo_root = Path(__file__).resolve().parents[2]
    frontend_log = repo_root / "eMas Front" / ".cursor" / "debug.log"
    default_path = frontend_log if frontend_log.parent.exists() else (repo_root / ".cursor" / "debug.log")
    raw = os.getenv("FACTORY_AGENT_DEBUG_LOG", str(default_path)).strip()
    return raw or None


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat() + "Z"
    return value


def log_event(event: str, *, level: str = "INFO", **fields: Any) -> None:
    logger = logging.getLogger(LOGGER_NAME)
    payload = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "level": level,
        "event": event,
    }
    for key, value in fields.items():
        payload[key] = _to_jsonable(value)
    logger.log(getattr(logging, level.upper(), logging.INFO), json.dumps(payload, default=_to_jsonable, ensure_ascii=True))


def log_llm_prompt(
    *,
    component: str,
    backend: str,
    model: str | None,
    prompt: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    path = _debug_log_path()
    if not path:
        return

    payload: dict[str, Any] = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "event": "llm_prompt",
        "component": component,
        "backend": backend,
        "model": model,
        "prompt": prompt,
    }
    for key, value in (metadata or {}).items():
        payload[key] = _to_jsonable(value)

    try:
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, default=_to_jsonable, ensure_ascii=False))
            fh.write("\n")
    except Exception as exc:
        log_event(
            "llm_prompt_log_failed",
            level="WARNING",
            component=component,
            backend=backend,
            model=model,
            error=str(exc),
            log_path=path,
        )


def log_llm_prompt_skipped(
    *,
    component: str,
    backend: str,
    reason: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    path = _debug_log_path()
    if not path:
        return

    payload: dict[str, Any] = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "event": "llm_prompt_skipped",
        "component": component,
        "backend": backend,
        "reason": reason,
    }
    for key, value in (metadata or {}).items():
        payload[key] = _to_jsonable(value)

    try:
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, default=_to_jsonable, ensure_ascii=False))
            fh.write("\n")
    except Exception as exc:
        log_event(
            "llm_prompt_log_failed",
            level="WARNING",
            component=component,
            backend=backend,
            error=str(exc),
            log_path=path,
        )


def log_step_status_changed(
    *,
    session_id: str,
    plan_id: str | None,
    plan_version: int | None,
    step_id: str,
    step_index: int,
    tool: str,
    status: str,
    idempotency_key: str | None,
    is_strongly_idempotent: bool | None = None,
    required_approval: bool | None = None,
    session_step_count: int | None = None,
    session_llm_call_count: int | None = None,
    session_replan_count: int | None = None,
    session_duration_s: int | None = None,
    user_id: str | None = None,
    latency_ms: int | None = None,
    http_status: int | None = None,
    idempotent_replay: bool | None = None,
    approval_latency_ms: int | None = None,
) -> None:
    log_event(
        "step_status_changed",
        session_id=session_id,
        plan_id=plan_id,
        plan_version=plan_version,
        step_id=step_id,
        step_index=step_index,
        tool=tool,
        tool_version=1,
        schema_version=1,
        is_strongly_idempotent=is_strongly_idempotent,
        status=status,
        latency_ms=latency_ms,
        http_status=http_status,
        idempotency_key=idempotency_key,
        idempotent_replay=idempotent_replay,
        required_approval=required_approval,
        approval_latency_ms=approval_latency_ms,
        session_step_count=session_step_count,
        session_llm_call_count=session_llm_call_count,
        session_replan_count=session_replan_count,
        session_duration_s=session_duration_s,
        user_id=user_id,
        environment=os.getenv("ENVIRONMENT", "development"),
    )
