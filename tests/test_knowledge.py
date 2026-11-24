from __future__ import annotations

from pathlib import Path

import pytest

from api_operator.core.config import Settings
from api_operator.factory import build_agent
from api_operator.rag.knowledge import (
    KeywordKnowledge,
    build_knowledge,
    expand_knowledge_paths,
    format_knowledge_context,
)
from api_operator.adapters.mock import reset_mock_store


@pytest.fixture(autouse=True)
def clean_store():
    reset_mock_store()
    yield
    reset_mock_store()


def test_knowledge_disabled_by_default():
    assert build_knowledge(enabled=False, paths="docs/a.md") is None


def test_expand_knowledge_paths_includes_directory(tmp_path: Path):
    (tmp_path / "a.md").write_text("# Alpha doc\n\n" + ("alpha " * 20), encoding="utf-8")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "b.md").write_text("# Beta doc\n\n" + ("beta " * 20), encoding="utf-8")
    (tmp_path / "skip.bin").write_bytes(b"\x00\x01")

    paths = expand_knowledge_paths(str(tmp_path))
    assert any(p.endswith("a.md") for p in paths)
    assert any(p.replace("\\", "/").endswith("nested/b.md") for p in paths)
    assert not any(p.endswith("skip.bin") for p in paths)

    store = build_knowledge(enabled=True, paths=str(tmp_path), backend="keyword")
    assert store is not None
    hits = store.retrieve("alpha", limit=3)
    assert hits


def test_tenant_isolation(tmp_path: Path):
    shared = tmp_path / "shared.md"
    shared.write_text(
        "Workspace provisioning uses the create_workspace tool for new tenants.\n\n"
        "More detail about shared platform policies for everyone.",
        encoding="utf-8",
    )
    tenant_a = tmp_path / "tenants" / "acme" / "faq.md"
    tenant_a.parent.mkdir(parents=True)
    tenant_a.write_text(
        "Acme private policy: always invite members with role admin for acme only.\n\n"
        "Acme FAQ about workspace creation and billing quirks.",
        encoding="utf-8",
    )
    tenant_b = tmp_path / "tenants" / "beta" / "faq.md"
    tenant_b.parent.mkdir(parents=True)
    tenant_b.write_text(
        "Beta private secrets should never leak to other tenants in knowledge search.\n\n"
        "Beta FAQ unrelated to acme workspace invites.",
        encoding="utf-8",
    )

    store = KeywordKnowledge([shared, tenant_a, tenant_b])
    acme_hits = store.retrieve("workspace invite acme", tenant_id="acme", limit=5)
    sources = {h.source for h in acme_hits}
    assert str(shared) in sources or any("shared.md" in s for s in sources)
    assert any("acme" in s.replace("\\", "/") for s in sources)
    assert not any("/tenants/beta/" in s.replace("\\", "/") for s in sources)

    no_scope = store.retrieve("Beta private secrets", tenant_id=None, limit=5)
    assert all("/tenants/" not in h.source.replace("\\", "/") for h in no_scope)


def test_format_knowledge_context():
    store_hits = KeywordKnowledge([]).retrieve("x")
    assert format_knowledge_context(store_hits) == ""


@pytest.mark.asyncio
async def test_agent_injects_knowledge_metadata(tmp_path: Path):
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
        ),
    )
    response = await agent.chat("list workspaces", abilities=["workspaces:read"])
    assert response.status == "ok"
    assert response.metadata.get("knowledge", {}).get("enabled") is True
    assert response.metadata["knowledge"]["hits"] >= 1
