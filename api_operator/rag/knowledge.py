"""Knowledge retrieval for Safe API Agent (opt-in, off by default)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from api_operator.rag.indexer import DocsIndex


@dataclass(slots=True)
class KnowledgeHit:
    source: str
    excerpt: str
    score: float = 0.0
    tenant_id: str | None = None


@runtime_checkable
class KnowledgeStore(Protocol):
    def retrieve(
        self,
        query: str,
        *,
        tenant_id: str | None = None,
        limit: int = 3,
    ) -> list[KnowledgeHit]: ...


class KeywordKnowledge:
    """L0 keyword store with optional per-tenant path isolation.

    Shared docs live at the top-level paths. Tenant-scoped docs may live under
    a subdirectory named after ``tenant_id`` (or containing ``/tenants/{id}/``).
    When ``tenant_id`` is set, shared docs remain visible and only that tenant's
    private docs are included — never other tenants'.
    """

    def __init__(
        self,
        paths: list[str | Path] | None = None,
        *,
        index: DocsIndex | None = None,
    ) -> None:
        if index is not None:
            self._index = index
        else:
            self._index = DocsIndex(list(paths or []))

    @classmethod
    def from_settings_paths(cls, raw: str | None) -> KeywordKnowledge | None:
        """Parse comma-separated paths; return None if empty."""
        paths = expand_knowledge_paths(raw)
        if not paths:
            return None
        return cls(paths)

    def retrieve(
        self,
        query: str,
        *,
        tenant_id: str | None = None,
        limit: int = 3,
    ) -> list[KnowledgeHit]:
        raw = self._index.search(query, limit=max(limit * 4, 12))
        hits: list[KnowledgeHit] = []
        for item in raw:
            source = str(item.get("source") or "")
            if not _allowed_for_tenant(source, tenant_id):
                continue
            hits.append(
                KnowledgeHit(
                    source=source,
                    excerpt=str(item.get("excerpt") or ""),
                    score=float(item.get("score") or 0),
                    tenant_id=_tenant_from_source(source),
                )
            )
            if len(hits) >= limit:
                break
        return hits


def expand_knowledge_paths(raw: str | None) -> list[str]:
    """Expand comma-separated file/dir paths into concrete markdown/text files.

    Directories include ``*.md`` and ``*.txt`` recursively (sorted).
    Missing paths are skipped so demos do not crash on optional docs.
    """
    if not raw or not str(raw).strip():
        return []

    out: list[str] = []
    seen: set[str] = set()
    for part in str(raw).split(","):
        candidate = part.strip()
        if not candidate:
            continue
        path = Path(candidate)
        files: list[Path]
        if path.is_dir():
            files = sorted(
                [
                    *path.rglob("*.md"),
                    *path.rglob("*.txt"),
                ]
            )
        elif path.is_file():
            files = [path]
        else:
            continue
        for file_path in files:
            key = str(file_path.resolve()) if file_path.exists() else str(file_path)
            if key in seen:
                continue
            seen.add(key)
            out.append(str(file_path))
    return out


def format_knowledge_context(hits: list[KnowledgeHit]) -> str:
    if not hits:
        return ""
    lines = ["Relevant documentation excerpts (use only if helpful for tool choice):"]
    for idx, hit in enumerate(hits, start=1):
        lines.append(f"[{idx}] ({hit.source})\n{hit.excerpt}")
    return "\n\n".join(lines)


def _tenant_from_source(source: str) -> str | None:
    normalized = source.replace("\\", "/")
    marker = "/tenants/"
    if marker in normalized:
        rest = normalized.split(marker, 1)[1]
        return rest.split("/", 1)[0] or None
    return None


def _allowed_for_tenant(source: str, tenant_id: str | None) -> bool:
    owned = _tenant_from_source(source)
    if owned is None:
        return True  # shared knowledge
    if tenant_id is None:
        return False  # hide all tenant-private docs without a scope
    return owned == tenant_id


def build_knowledge(
    *,
    enabled: bool,
    paths: str | None,
    adapter_docs: list[str] | None = None,
    backend: str = "keyword",
    openai_api_key: str | None = None,
    embedding_model: str = "text-embedding-3-small",
    pg_dsn: str | None = None,
) -> KnowledgeStore | None:
    if not enabled:
        return None

    mode = (backend or "keyword").strip().lower()
    if mode == "pgvector":
        if not pg_dsn:
            raise ValueError("knowledge_backend=pgvector requires knowledge_pg_dsn / API_OPERATOR_KNOWLEDGE_PG_DSN")
        from api_operator.rag.embeddings import HashingEmbedder, OpenAIEmbedder
        from api_operator.rag.pgvector import PgVectorKnowledge

        embedder = (
            OpenAIEmbedder(openai_api_key, model=embedding_model)
            if openai_api_key
            else HashingEmbedder()
        )
        return PgVectorKnowledge(pg_dsn, embedder=embedder)

    combined: list[str | Path] = []
    if paths:
        combined.extend(expand_knowledge_paths(paths))
    if adapter_docs:
        combined.extend(adapter_docs)
    if not combined:
        return None

    if mode in {"embedding", "embeddings", "vector"}:
        from api_operator.rag.embeddings import HashingEmbedder, OpenAIEmbedder
        from api_operator.rag.vector import EmbeddingKnowledge

        embedder = (
            OpenAIEmbedder(openai_api_key, model=embedding_model)
            if openai_api_key
            else HashingEmbedder()
        )
        return EmbeddingKnowledge(combined, embedder=embedder)

    return KeywordKnowledge(combined)
