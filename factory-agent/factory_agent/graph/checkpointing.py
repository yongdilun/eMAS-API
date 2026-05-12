from __future__ import annotations

from typing import Any

from ..config import Settings


def build_graph_checkpointer(settings: Settings) -> Any | None:
    """Best-effort native LangGraph checkpointer factory.

    Preference:
    1) Postgres saver when explicitly configured and importable
    2) In-memory saver as local/dev fallback
    3) None when disabled
    """
    backend = (settings.graph_checkpoint_backend or "auto").strip().lower()
    if backend == "off":
        return None

    postgres_dsn = settings.graph_checkpoint_postgres_dsn
    if backend in {"auto", "postgres"} and postgres_dsn:
        try:
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver  # type: ignore

            return AsyncPostgresSaver.from_conn_string(postgres_dsn)
        except Exception:
            if backend == "postgres":
                return None

    if backend in {"auto", "memory"}:
        try:
            from langgraph.checkpoint.memory import MemorySaver

            return MemorySaver()
        except Exception:
            return None
    return None
