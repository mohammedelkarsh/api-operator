from __future__ import annotations

from pathlib import Path
from typing import Any

class DocsIndex:
    """Lightweight keyword RAG over markdown/text docs (no embeddings required)."""

    def __init__(self, paths: list[str | Path]) -> None:
        self.chunks: list[tuple[str, str]] = []
        for path in paths:
            file_path = Path(path)
            if not file_path.exists():
                continue
            text = file_path.read_text(encoding="utf-8", errors="ignore")
            source = str(file_path)
            for idx, paragraph in enumerate(text.split("\n\n")):
                cleaned = paragraph.strip()
                if len(cleaned) < 40:
                    continue
                self.chunks.append((source, cleaned))

    def search(self, query: str, limit: int = 3) -> list[dict[str, Any]]:
        terms = [t for t in query.lower().split() if len(t) > 2]
        if not terms:
            return []
        scored: list[tuple[int, str, str]] = []
        for source, chunk in self.chunks:
            lower = chunk.lower()
            score = sum(lower.count(term) for term in terms)
            if score:
                scored.append((score, source, chunk))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            {"source": source, "excerpt": chunk[:500]}
            for _, source, chunk in scored[:limit]
        ]
