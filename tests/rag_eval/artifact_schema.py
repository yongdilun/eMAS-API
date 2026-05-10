"""Artifact schema helpers for the live RAG evaluation harness.

The harness writes one JSON file per case under
``test-artifacts/rag-eval/<run_id>/<case_id>.json`` plus a ``summary.json``
listing every case.

The schema is intentionally small and stable so it can be diffed across runs
and reviewed manually. Helpers in this module own the exact field layout so
the runner stays focused on orchestration.

Top-level per-case schema
-------------------------

```
{
  "schema_version": 1,
  "run_id": "20260510T101530Z-abcd",
  "case_id": "loto-01-overview",
  "started_at": "2026-05-10T10:15:30.123456+00:00",
  "finished_at": "2026-05-10T10:15:34.456789+00:00",
  "duration_s": 4.33,
  "env": {
    "app_mode": "development",
    "planner_model": "...",
    "rag_answer_model": "...",
    "rag_reranker_model": "...",
    "openai_base_url_host": "127.0.0.1"
  },
  "case": { ...original case entry from cases.json... },
  "query": "What is LOTO?",
  "route_decision": { ...full router dict... },
  "rag": {
    "answer": "...",
    "sources": [ ... ],
    "safety_warning": true,
    "route_used": "RAG_ONLY"
  },
  "agent_response": {
    "answer": "...",
    "sources": [ ... ],
    "route": "RAG_ONLY",
    "safety_warning": true,
    "metadata": { "route_decision": { ... } }
  },
  "retrieval_debug": {
    "queried": true,
    "top_chunks": [
      {
        "chunk_id": "...",
        "doc_id": "SOP-LOTO-001",
        "title": "LOTO Procedure Standard",
        "fusion_score": 0.123,
        "boosted_score": 0.456,
        "snippet": "first 240 chars..."
      }
    ],
    "error": null
  },
  "automated": {
    "ok": true,
    "checks": [
      { "id": "answer_non_empty", "ok": true, "severity": "fail" },
      { "id": "routing_preferred", "ok": false, "severity": "warn",
        "detail": "expected RAG_ONLY, got API_ONLY" }
    ],
    "errors": [],
    "warnings": ["routing_preferred"]
  },
  "manual_evaluation": {
    "score": null,
    "dimensions": null,
    "reviewer_notes": null
  }
}
```
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable
from urllib.parse import urlparse

SCHEMA_VERSION = 1

# Severity for automated checks. ``fail`` flips ``automated.ok`` to false;
# ``warn`` is recorded but does not fail the run.
SEVERITY_FAIL = "fail"
SEVERITY_WARN = "warn"


@dataclass
class CheckResult:
    """A single automated check outcome."""

    id: str
    ok: bool
    severity: str = SEVERITY_FAIL
    detail: str | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"id": self.id, "ok": self.ok, "severity": self.severity}
        if self.detail is not None:
            out["detail"] = self.detail
        return out


@dataclass
class AutomatedReport:
    """Aggregated structural-only checks for a single case."""

    checks: list[CheckResult] = field(default_factory=list)

    def add(self, check: CheckResult) -> None:
        self.checks.append(check)

    @property
    def errors(self) -> list[str]:
        return [c.id for c in self.checks if not c.ok and c.severity == SEVERITY_FAIL]

    @property
    def warnings(self) -> list[str]:
        return [c.id for c in self.checks if not c.ok and c.severity == SEVERITY_WARN]

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "checks": [c.to_dict() for c in self.checks],
            "errors": self.errors,
            "warnings": self.warnings,
        }


def now_iso() -> str:
    """ISO-8601 UTC timestamp with timezone, used for ``started_at``/``finished_at``."""

    return datetime.now(timezone.utc).isoformat()


def build_env_fingerprint(settings: Any) -> dict[str, Any]:
    """Capture non-secret environment fingerprint from ``Settings``.

    Only the host of the OpenAI base URL is recorded so artifacts are safe to
    commit if the user ever wants to share them.
    """

    base_url = (
        getattr(settings, "rag_answer_openai_base_url", None)
        or getattr(settings, "planner_openai_base_url", None)
        or getattr(settings, "openai_base_url", None)
    )
    host = None
    if base_url:
        try:
            host = urlparse(base_url).hostname
        except Exception:  # pragma: no cover - defensive
            host = None
    return {
        "schema_version": SCHEMA_VERSION,
        "planner_model": getattr(settings, "planner_model", None),
        "rag_answer_model": getattr(settings, "rag_answer_model", None),
        "rag_reranker_model": getattr(settings, "rag_reranker_model", None),
        "openai_base_url_host": host,
    }


def serialize_route_decision(decision: Any) -> dict[str, Any]:
    """Coerce a router decision (already a dict in practice) to a JSON-safe dict."""

    if isinstance(decision, dict):
        return _ensure_jsonable(decision)
    if hasattr(decision, "__dict__"):
        return _ensure_jsonable(dict(decision.__dict__))
    return {"raw": str(decision)}


def serialize_rag_result(result: Any) -> dict[str, Any]:
    """Serialize an ``AnswerResult`` (or duck-typed equivalent) for the artifact."""

    if result is None:
        return {}
    if hasattr(result, "model_dump"):
        try:
            return _ensure_jsonable(result.model_dump())
        except Exception:  # pragma: no cover - defensive
            pass
    return {
        "answer": getattr(result, "answer", None),
        "sources": [_serialize_source(s) for s in getattr(result, "sources", []) or []],
        "safety_warning": bool(getattr(result, "safety_warning", False)),
        "route_used": getattr(result, "route_used", None),
    }


def serialize_agent_response(response: Any) -> dict[str, Any]:
    """Serialize a ``Phase5Agent`` ``AgentResponse``."""

    if response is None:
        return {}
    if hasattr(response, "model_dump"):
        try:
            return _ensure_jsonable(response.model_dump())
        except Exception:  # pragma: no cover - defensive
            pass
    return {
        "answer": getattr(response, "answer", None),
        "sources": [_serialize_source(s) for s in getattr(response, "sources", []) or []],
        "route": getattr(response, "route", None),
        "safety_warning": bool(getattr(response, "safety_warning", False)),
        "metadata": _ensure_jsonable(getattr(response, "metadata", {}) or {}),
    }


def serialize_retrieval_debug(scored_chunks: Iterable[Any] | None, *, top_n: int = 5,
                              snippet_chars: int = 240, error: str | None = None) -> dict[str, Any]:
    """Build the ``retrieval_debug`` block from a list of ``ScoredChunk``."""

    if scored_chunks is None and error is None:
        return {"queried": False, "top_chunks": [], "error": None}

    top: list[dict[str, Any]] = []
    if scored_chunks is not None:
        for sc in list(scored_chunks)[:top_n]:
            chunk = getattr(sc, "chunk", None)
            metadata = getattr(chunk, "metadata", {}) or {}
            text = getattr(chunk, "text", "") or ""
            top.append(
                {
                    "chunk_id": getattr(chunk, "chunk_id", None),
                    "doc_id": metadata.get("doc_id"),
                    "title": metadata.get("title"),
                    "domain": metadata.get("domain"),
                    "subdomain": metadata.get("subdomain"),
                    "authority_level": metadata.get("authority_level"),
                    "risk_level": metadata.get("risk_level"),
                    "vector_score": getattr(sc, "vector_score", None),
                    "keyword_score": getattr(sc, "keyword_score", None),
                    "fusion_score": getattr(sc, "fusion_score", None),
                    "boosted_score": getattr(sc, "boosted_score", None),
                    "snippet": text[:snippet_chars],
                }
            )

    return {
        "queried": scored_chunks is not None,
        "top_chunks": top,
        "error": error,
    }


def empty_manual_evaluation() -> dict[str, Any]:
    """Placeholder block reviewers fill in after reading the final response."""

    return {
        "score": None,
        "dimensions": None,
        "reviewer_notes": None,
    }


def build_case_artifact(
    *,
    run_id: str,
    case: dict[str, Any],
    query: str,
    started_at: str,
    finished_at: str,
    duration_s: float,
    env: dict[str, Any],
    route_decision: dict[str, Any] | None,
    rag_result: dict[str, Any] | None,
    agent_response: dict[str, Any] | None,
    retrieval_debug: dict[str, Any],
    automated: AutomatedReport,
    error: str | None = None,
) -> dict[str, Any]:
    """Assemble the per-case artifact dict in canonical field order."""

    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "case_id": case.get("id"),
        "started_at": started_at,
        "finished_at": finished_at,
        "duration_s": round(duration_s, 4),
        "env": env,
        "case": case,
        "query": query,
        "route_decision": route_decision,
        "rag": rag_result,
        "agent_response": agent_response,
        "retrieval_debug": retrieval_debug,
        "automated": automated.to_dict(),
        "manual_evaluation": empty_manual_evaluation(),
        "error": error,
    }


def build_summary(
    *,
    run_id: str,
    started_at: str,
    finished_at: str,
    env: dict[str, Any],
    case_results: list[dict[str, Any]],
) -> dict[str, Any]:
    """Aggregate per-case artifacts into a ``summary.json`` payload."""

    automated_pass = sum(1 for r in case_results if r.get("automated", {}).get("ok"))
    automated_fail = len(case_results) - automated_pass
    warnings = sum(len(r.get("automated", {}).get("warnings") or []) for r in case_results)

    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "started_at": started_at,
        "finished_at": finished_at,
        "env": env,
        "totals": {
            "cases": len(case_results),
            "automated_pass": automated_pass,
            "automated_fail": automated_fail,
            "warnings": warnings,
        },
        "cases": [
            {
                "case_id": r.get("case_id"),
                "route": (r.get("route_decision") or {}).get("route"),
                "route_source": (r.get("route_decision") or {}).get("route_source"),
                "automated_ok": (r.get("automated") or {}).get("ok"),
                "warnings": (r.get("automated") or {}).get("warnings") or [],
                "errors": (r.get("automated") or {}).get("errors") or [],
                "duration_s": r.get("duration_s"),
                "artifact_path": r.get("_artifact_path"),
            }
            for r in case_results
        ],
    }


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _serialize_source(source: Any) -> dict[str, Any]:
    if source is None:
        return {}
    if hasattr(source, "model_dump"):
        try:
            return _ensure_jsonable(source.model_dump())
        except Exception:  # pragma: no cover - defensive
            pass
    if isinstance(source, dict):
        return _ensure_jsonable(source)
    return {"raw": str(source)}


def _ensure_jsonable(value: Any) -> Any:
    """Best-effort coercion to JSON-safe primitives.

    Pydantic models inside metadata are exercised through ``model_dump`` paths
    above; this is a defensive fallback for nested objects.
    """

    if isinstance(value, dict):
        return {str(k): _ensure_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_ensure_jsonable(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if hasattr(value, "model_dump"):
        try:
            return _ensure_jsonable(value.model_dump())
        except Exception:  # pragma: no cover - defensive
            return str(value)
    if hasattr(value, "__dict__"):
        return _ensure_jsonable(dict(value.__dict__))
    return str(value)
