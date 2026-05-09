from __future__ import annotations

import math
import re
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from factory_agent.persistence.models import VectorMemory as VectorMemoryRow
from factory_agent.persistence.models import generate_uuid


_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall((text or "").lower())


def _hash_embedding(text: str, *, dims: int = 128) -> list[float]:
    vec = [0.0] * dims
    for token in _tokenize(text):
        bucket = hash(token) % dims
        vec[bucket] += 1.0
    norm = math.sqrt(sum(v * v for v in vec))
    if norm <= 0.0:
        return vec
    return [v / norm for v in vec]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    n = min(len(a), len(b))
    if n <= 0:
        return 0.0
    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for idx in range(n):
        x = float(a[idx])
        y = float(b[idx])
        dot += x * y
        norm_a += x * x
        norm_b += y * y
    if norm_a <= 0.0 or norm_b <= 0.0:
        return 0.0
    return dot / (math.sqrt(norm_a) * math.sqrt(norm_b))


class NoOpVectorStore:
    async def similarity_search(self, query: str, *, k: int = 8) -> list[dict[str, Any]]:
        del query, k
        return []


class SqlVectorStore:
    """Simple SQL vector store with hashed embeddings."""

    def __init__(
        self,
        db: AsyncSession,
        *,
        retention_days: int = 30,
        dims: int = 128,
    ) -> None:
        self._db = db
        self._retention_days = max(1, int(retention_days))
        self._dims = max(16, int(dims))

    async def add(
        self,
        *,
        session_id: str | None,
        user_id: str | None,
        text: str,
        memory_type: str = "conversation",
        source_message_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        reusable_scope: str = "session",
        pii_redacted: bool = False,
    ) -> str:
        now = datetime.utcnow()
        row = VectorMemoryRow(
            memory_id=generate_uuid(),
            session_id=session_id,
            user_id=user_id,
            memory_type=memory_type,
            content=text,
            embedding=_hash_embedding(text, dims=self._dims),
            source_message_id=source_message_id,
            memory_metadata=metadata or {},
            reusable_scope=reusable_scope,
            pii_redacted=bool(pii_redacted),
            created_at=now,
            expires_at=now + timedelta(days=self._retention_days),
        )
        self._db.add(row)
        return row.memory_id

    async def similarity_search(
        self,
        query: str,
        *,
        k: int = 8,
        session_id: str | None = None,
        user_id: str | None = None,
        min_score: float = 0.12,
    ) -> list[dict[str, Any]]:
        if not (query or "").strip():
            return []
        now = datetime.utcnow()
        stmt = select(VectorMemoryRow).where((VectorMemoryRow.expires_at.is_(None)) | (VectorMemoryRow.expires_at > now))
        if user_id:
            stmt = stmt.where((VectorMemoryRow.user_id == user_id) | (VectorMemoryRow.reusable_scope == "global"))
        if session_id:
            stmt = stmt.where(
                (VectorMemoryRow.session_id == session_id)
                | ((VectorMemoryRow.user_id == user_id) & (VectorMemoryRow.reusable_scope == "user"))
                | (VectorMemoryRow.reusable_scope == "global")
            )
        rows = (await self._db.execute(stmt.order_by(VectorMemoryRow.created_at.desc()).limit(500))).scalars().all()
        if not rows:
            return []

        query_vec = _hash_embedding(query, dims=self._dims)
        scored: list[tuple[float, VectorMemoryRow]] = []
        for row in rows:
            emb = row.embedding if isinstance(row.embedding, list) else []
            score = _cosine_similarity(query_vec, [float(x) for x in emb if isinstance(x, (int, float))])
            if score >= float(min_score):
                scored.append((score, row))
        scored.sort(key=lambda item: item[0], reverse=True)
        top = scored[: max(1, int(k))]
        return [
            {
                "memory_id": row.memory_id,
                "session_id": row.session_id,
                "user_id": row.user_id,
                "memory_type": row.memory_type,
                "content": row.content,
                "source_message_id": row.source_message_id,
                "metadata": row.memory_metadata if isinstance(row.memory_metadata, dict) else {},
                "score": round(float(score), 6),
                "created_at": row.created_at.isoformat() + "Z" if row.created_at else None,
            }
            for score, row in top
        ]

    async def prune_expired(self) -> int:
        now = datetime.utcnow()
        rows = (
            await self._db.execute(
                select(VectorMemoryRow).where(VectorMemoryRow.expires_at.is_not(None)).where(VectorMemoryRow.expires_at <= now)
            )
        ).scalars().all()
        for row in rows:
            await self._db.delete(row)
        return len(rows)

