"""L1 in-memory / local vector knowledge store."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from api_operator.rag.embeddings import Embedder, HashingEmbedder, cosine_similarity
from api_operator.rag.indexer import DocsIndex
from api_operator.rag.knowledge import KnowledgeHit, _allowed_for_tenant, _tenant_from_source


@dataclass(slots=True)
class _VectorChunk:
    source: str
    excerpt: str
    vector: list[float]


class EmbeddingKnowledge:
    """L1 semantic search over doc chunks with an inject Embedder."""

    def __init__(
        self,
        paths: list[str | Path],
        *,
        embedder: Embedder | None = None,
    ) -> None:
        self.embedder = embedder or HashingEmbedder()
        index = DocsIndex(list(paths))
        texts = [chunk for _, chunk in index.chunks]
        vectors = self.embedder.embed(texts) if texts else []
        self._chunks: list[_VectorChunk] = [
            _VectorChunk(source=source, excerpt=chunk[:500], vector=vector)
            for (source, chunk), vector in zip(index.chunks, vectors, strict=True)
        ]

    def retrieve(
        self,
        query: str,
        *,
        tenant_id: str | None = None,
        limit: int = 3,
    ) -> list[KnowledgeHit]:
        if not self._chunks or not query.strip():
            return []
        query_vec = self.embedder.embed([query])[0]
        scored: list[tuple[float, _VectorChunk]] = []
        for chunk in self._chunks:
            if not _allowed_for_tenant(chunk.source, tenant_id):
                continue
            score = cosine_similarity(query_vec, chunk.vector)
            if score > 0:
                scored.append((score, chunk))
        scored.sort(key=lambda item: item[0], reverse=True)
        hits: list[KnowledgeHit] = []
        for score, chunk in scored[:limit]:
            hits.append(
                KnowledgeHit(
                    source=chunk.source,
                    excerpt=chunk.excerpt,
                    score=score,
                    tenant_id=_tenant_from_source(chunk.source),
                )
            )
        return hits
