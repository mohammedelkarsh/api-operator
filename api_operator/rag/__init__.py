"""Optional knowledge / RAG helpers (keyword L0 in core; vector extras via [rag])."""

from api_operator.rag.embeddings import Embedder, HashingEmbedder, OpenAIEmbedder
from api_operator.rag.indexer import DocsIndex
from api_operator.rag.knowledge import KeywordKnowledge, KnowledgeHit, KnowledgeStore
from api_operator.rag.vector import EmbeddingKnowledge

__all__ = [
    "DocsIndex",
    "Embedder",
    "EmbeddingKnowledge",
    "HashingEmbedder",
    "KeywordKnowledge",
    "KnowledgeHit",
    "KnowledgeStore",
    "OpenAIEmbedder",
]
