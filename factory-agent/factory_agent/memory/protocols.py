"""Protocols for future memory / RAG integrations (not wired yet)."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class CheckpointStore(Protocol):
    async def load(self, thread_id: str) -> dict[str, Any] | None: ...

    async def save(self, thread_id: str, state: dict[str, Any]) -> None: ...


@runtime_checkable
class VectorStore(Protocol):
    async def similarity_search(self, query: str, *, k: int = 8) -> list[dict[str, Any]]: ...
