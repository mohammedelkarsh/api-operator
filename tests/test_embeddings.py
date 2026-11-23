from __future__ import annotations

from pathlib import Path

import pytest

from api_operator.core.config import Settings
from api_operator.factory import build_agent
from api_operator.rag.embeddings import HashingEmbedder, cosine_similarity
from api_operator.rag.knowledge import build_knowledge
from api_operator.rag.vector import EmbeddingKnowledge
from api_operator.adapters.mock import reset_mock_store


@pytest.fixture(autouse=True)
def clean_store():
    reset_mock_store()
    yield
    reset_mock_store()


def test_hashing_embedder_is_deterministic():
    emb = HashingEmbedder(dimensions=32)
    a = emb.embed(["create workspace tool"])[0]
    b = emb.embed(["create workspace tool"])[0]
    assert a == b
    assert cosine_similarity(a, a) == pytest.approx(1.0)


def test_embedding_knowledge_ranks_related_docs(tmp_path: Path):
    related = tmp_path / "workspaces.md"
    related.write_text(
        "Use the create_workspace tool when the user wants a new workspace subdomain.\n\n"
        "Always confirm dangerous workspace creation before calling the API.",
        encoding="utf-8",
    )
    unrelated = tmp_path / "cooking.md"
    unrelated.write_text(
        "Pasta recipes with tomato sauce and basil are unrelated to SaaS tooling.\n\n"
        "Dessert ideas include chocolate cake and vanilla ice cream for parties.",
        encoding="utf-8",
    )
    store = EmbeddingKnowledge([related, unrelated], embedder=HashingEmbedder())
    hits = store.retrieve("create workspace subdomain", limit=2)
    assert hits
    assert "workspaces.md" in hits[0].source


def test_build_knowledge_embedding_backend(tmp_path: Path):
    doc = tmp_path / "guide.md"
    doc.write_text(
        "List workspaces with the list_workspaces tool from the operator chat flow.\n\n"
        "Guided agent buttons help users discover workspace listing commands.",
        encoding="utf-8",
    )
    store = build_knowledge(
        enabled=True,
        paths=str(doc),
        backend="embedding",
    )
    assert store is not None
    hits = store.retrieve("list workspaces tool")
    assert len(hits) >= 1


@pytest.mark.asyncio
async def test_agent_embedding_backend_metadata(tmp_path: Path):
    doc = tmp_path / "guide.md"
    doc.write_text(
        "To list workspaces use the list_workspaces tool from the operator chat.\n\n"
        "This paragraph explains workspace listing for the guided agent.",
        encoding="utf-8",
    )
    agent = build_agent(
        "mock",
        settings=Settings(
            planner="mock",
            knowledge_enabled=True,
            knowledge_paths=str(doc),
            knowledge_backend="embedding",
        ),
    )
    response = await agent.chat("list workspaces", abilities=["workspaces:read"])
    assert response.metadata["knowledge"]["backend"] == "embedding"
    assert response.metadata["knowledge"]["hits"] >= 1


def test_pgvector_requires_dsn():
    with pytest.raises(ValueError, match="knowledge_pg_dsn"):
        build_knowledge(enabled=True, paths=None, backend="pgvector", pg_dsn=None)
