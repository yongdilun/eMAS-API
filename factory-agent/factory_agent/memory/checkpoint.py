"""No-op checkpoint store placeholder."""

from __future__ import annotations

from typing import Any


class NoOpCheckpointStore:
    async def load(self, thread_id: str) -> dict[str, Any] | None:
        return None

    async def save(self, thread_id: str, state: dict[str, Any]) -> None:
        return None
