"""No-op vector store placeholder."""

from __future__ import annotations

from typing import Any


class NoOpVectorStore:
    async def similarity_search(self, query: str, *, k: int = 8) -> list[dict[str, Any]]:
        return []
