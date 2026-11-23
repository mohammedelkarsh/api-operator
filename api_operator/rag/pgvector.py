"""L2 Postgres + pgvector knowledge store (optional ``api-operator[rag]``)."""

from __future__ import annotations

from typing import Any

from api_operator.rag.embeddings import Embedder, HashingEmbedder
from api_operator.rag.knowledge import KnowledgeHit, _allowed_for_tenant, _tenant_from_source


class PgVectorKnowledge:
    """Query a pre-built ``api_operator_knowledge`` table with a vector column.

    Expected schema (create outside the agent, e.g. Laravel migration)::

        CREATE EXTENSION IF NOT EXISTS vector;
        CREATE TABLE api_operator_knowledge (
            id bigserial PRIMARY KEY,
            source text NOT NULL,
            excerpt text NOT NULL,
            tenant_id text NULL,
            embedding vector(1536) NOT NULL
        );

    This class only **retrieves**; indexing/upsert is left to the host app.
    """

    def __init__(
        self,
        dsn: str,
        *,
        embedder: Embedder | None = None,
        table: str = "api_operator_knowledge",
        embedding_column: str = "embedding",
    ) -> None:
        self.dsn = dsn
        self.embedder = embedder or HashingEmbedder()
        self.table = table
        self.embedding_column = embedding_column
        self._engine = None

    def _connect(self) -> Any:
        if self._engine is not None:
            return self._engine
        try:
            from sqlalchemy import create_engine
        except ImportError as exc:
            raise RuntimeError(
                "PgVector knowledge requires sqlalchemy. Install: pip install 'api-operator[rag]'"
            ) from exc
        self._engine = create_engine(self.dsn)
        return self._engine

    def retrieve(
        self,
        query: str,
        *,
        tenant_id: str | None = None,
        limit: int = 3,
    ) -> list[KnowledgeHit]:
        if not query.strip():
            return []
        vector = self.embedder.embed([query])[0]
        # pgvector literal: '[1,2,3]'
        literal = "[" + ",".join(f"{v:.8f}" for v in vector) + "]"
        engine = self._connect()
        try:
            from sqlalchemy import text
        except ImportError as exc:
            raise RuntimeError(
                "PgVector knowledge requires sqlalchemy. Install: pip install 'api-operator[rag]'"
            ) from exc

        # Filter tenant in SQL when possible; still re-check paths for shared docs
        sql = text(
            f"""
            SELECT source, excerpt, tenant_id,
                   1 - ({self.embedding_column} <=> CAST(:embedding AS vector)) AS score
            FROM {self.table}
            WHERE (
                :tenant_id IS NULL AND tenant_id IS NULL
            ) OR (
                :tenant_id IS NOT NULL AND (tenant_id IS NULL OR tenant_id = :tenant_id)
            )
            ORDER BY {self.embedding_column} <=> CAST(:embedding AS vector)
            LIMIT :limit
            """
        )
        with engine.connect() as conn:
            rows = conn.execute(
                sql,
                {"embedding": literal, "tenant_id": tenant_id, "limit": max(limit * 2, 6)},
            ).mappings().all()

        hits: list[KnowledgeHit] = []
        for row in rows:
            source = str(row["source"])
            # Path-based isolation still applies for filesystem-style sources
            if source and not _allowed_for_tenant(source, tenant_id):
                owned = row.get("tenant_id")
                if owned is not None and tenant_id is not None and str(owned) != tenant_id:
                    continue
                if owned is not None and tenant_id is None:
                    continue
            hits.append(
                KnowledgeHit(
                    source=source,
                    excerpt=str(row["excerpt"]),
                    score=float(row["score"] or 0),
                    tenant_id=(
                        str(row["tenant_id"])
                        if row.get("tenant_id") is not None
                        else _tenant_from_source(source)
                    ),
                )
            )
            if len(hits) >= limit:
                break
        return hits
