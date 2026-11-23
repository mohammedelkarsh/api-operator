from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from api_operator.adapters.mock import get_mock_store, reset_mock_store
from api_operator.core.config import Settings
from api_operator.factory import build_agent
from api_operator.server.app import create_app


@pytest.fixture(autouse=True)
def clean_store():
    reset_mock_store()
    yield
    reset_mock_store()


@pytest.mark.asyncio
async def test_dry_run_does_not_mutate_store():
    agent = build_agent("mock", settings=Settings(planner="mock"))
    response = await agent.chat(
        "create workspace Acme subdomain acme",
        abilities=["workspaces:write"],
        auto_confirm=True,
        dry_run=True,
    )
    assert response.status == "ok"
    assert response.metadata.get("dry_run") is True
    assert response.dry_run_report is not None
    assert response.dry_run_report.tool == "create_workspace"
    assert "acme" not in get_mock_store().workspaces
    assert "[dry-run]" in response.message


@pytest.mark.asyncio
async def test_dry_run_reports_confirm_without_pending():
    agent = build_agent("mock", settings=Settings(planner="mock"))
    response = await agent.chat(
        "create workspace Acme subdomain acme",
        abilities=["workspaces:write"],
        dry_run=True,
    )
    assert response.status == "confirm"
    assert response.dry_run_report is not None
    session = agent.sessions.get(response.session_id)
    assert session is not None
    assert session.pending_confirmation is None


@pytest.mark.asyncio
async def test_dry_run_deny():
    agent = build_agent("mock", settings=Settings(planner="mock"))
    response = await agent.chat(
        "create workspace Acme subdomain acme",
        abilities=["workspaces:read"],
        auto_confirm=True,
        dry_run=True,
    )
    assert response.status == "deny"
    assert response.dry_run_report is not None
    assert response.dry_run_report.policy is not None
    assert response.dry_run_report.policy.decision.value == "deny"


@pytest.mark.asyncio
async def test_http_dry_run():
    app = create_app(Settings(planner="mock", default_adapter="mock"))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v1/chat",
            json={
                "message": "create workspace Acme subdomain acme",
                "abilities": ["workspaces:write"],
                "auto_confirm": True,
                "dry_run": True,
            },
        )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["dry_run_report"] is not None
    assert body["dry_run_report"]["dry_run"] is True
    assert "acme" not in get_mock_store().workspaces


@pytest.mark.asyncio
async def test_yaml_dry_run_includes_would_call():
    agent = build_agent(
        "yaml",
        settings=Settings(planner="mock"),
        config_path="examples/tenant-kit-adapter/adapter.yaml",
        # Avoid sibling policy.yaml confirm list for this assertion path
        policy_path=None,
        token="test-token",
    )
    # Force empty policy so dangerous still confirms unless auto_confirm
    from api_operator.core.policy import PolicyEngine

    agent.policy = PolicyEngine()
    response = await agent.chat(
        "create workspace Acme subdomain acme",
        abilities=["workspaces:write"],
        auto_confirm=True,
        dry_run=True,
    )
    assert response.status == "ok"
    assert response.dry_run_report is not None
    assert response.dry_run_report.would_call is not None
    assert response.dry_run_report.would_call.method == "POST"
    assert "/api/workspaces" in (response.dry_run_report.would_call.url or "")
