from __future__ import annotations

from pathlib import Path

import pytest

from api_operator.adapters.mock import reset_mock_store
from api_operator.core.audit import JsonlAuditSink, MemoryAuditSink, parse_jsonl
from api_operator.core.config import Settings
from api_operator.core.redaction import REDACTED, redact
from api_operator.factory import build_agent


@pytest.fixture(autouse=True)
def clean_store():
    reset_mock_store()
    yield
    reset_mock_store()


def test_redact_sensitive_keys():
    payload = {
        "password": "secret",
        "token": "abc",
        "nested": {"authorization": "Bearer x", "name": "ok"},
        "list": [{"secret": "y"}, "plain"],
    }
    cleaned = redact(payload)
    assert cleaned["password"] == REDACTED
    assert cleaned["token"] == REDACTED
    assert cleaned["nested"]["authorization"] == REDACTED
    assert cleaned["nested"]["name"] == "ok"
    assert cleaned["list"][0]["secret"] == REDACTED
    assert cleaned["list"][1] == "plain"


@pytest.mark.asyncio
async def test_audit_events_on_execute_and_deny():
    sink = MemoryAuditSink()
    agent = build_agent("mock", settings=Settings(planner="mock"), audit=sink)

    await agent.chat(
        "list workspaces",
        abilities=["workspaces:read"],
    )
    denied = await agent.chat(
        "create workspace Acme subdomain acme",
        abilities=["workspaces:read"],
        auto_confirm=True,
    )
    assert denied.status == "deny"
    assert len(sink.events) >= 2
    statuses = {e.result_status for e in sink.events}
    assert "ok" in statuses
    assert "deny" in statuses
    assert all(e.adapter for e in sink.events)


@pytest.mark.asyncio
async def test_audit_jsonl_file(tmp_path: Path):
    path = tmp_path / "audit.jsonl"
    sink = JsonlAuditSink(path)
    agent = build_agent(
        "mock",
        settings=Settings(planner="mock", audit_enabled=True),
        audit=sink,
    )
    await agent.chat(
        "create workspace Acme subdomain acme",
        abilities=["workspaces:write"],
        auto_confirm=True,
    )
    rows = parse_jsonl(path)
    assert len(rows) == 1
    assert rows[0]["tool"] == "create_workspace"
    assert rows[0]["result_status"] == "ok"


@pytest.mark.asyncio
async def test_audit_disabled():
    sink = MemoryAuditSink()
    agent = build_agent(
        "mock",
        settings=Settings(planner="mock", audit_enabled=False),
        audit=sink,
    )
    # Even if a sink is injected, Agent skips emit when audit_enabled=False
    await agent.chat("list workspaces", abilities=["workspaces:read"])
    assert sink.events == []
