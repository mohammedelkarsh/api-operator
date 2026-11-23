from __future__ import annotations

import pytest

from api_operator.adapters.mock import get_mock_store, reset_mock_store
from api_operator.core.config import Settings
from api_operator.core.quota import InMemoryQuotaGateway, QuotaContext
from api_operator.core.schemas import QuotaDecision
from api_operator.factory import build_agent


@pytest.fixture(autouse=True)
def clean_store():
    reset_mock_store()
    yield
    reset_mock_store()


def test_in_memory_quota_blocks_when_exceeded():
    gateway = InMemoryQuotaGateway(budget=2.0, tool_costs={"create_workspace": 1.5})
    ctx = QuotaContext(tool="create_workspace", session_id="s1")
    first = gateway.check(ctx, 1.5)
    assert first.decision == QuotaDecision.ALLOW
    gateway.commit(ctx, 1.5, first.reservation_id)
    second = gateway.check(ctx, 1.5)
    assert second.decision == QuotaDecision.DENY


def test_quota_rollback_restores_budget():
    gateway = InMemoryQuotaGateway(budget=5.0)
    ctx = QuotaContext(tool="x")
    reservation = gateway.check(ctx, 3.0)
    assert reservation.decision == QuotaDecision.ALLOW
    gateway.rollback(ctx, reservation.reservation_id)
    again = gateway.check(ctx, 3.0)
    assert again.decision == QuotaDecision.ALLOW


@pytest.mark.asyncio
async def test_agent_denies_when_quota_exceeded():
    gateway = InMemoryQuotaGateway(budget=0.5, tool_costs={"create_workspace": 1.0})
    agent = build_agent(
        "mock",
        settings=Settings(planner="mock"),
        quota=gateway,
    )
    response = await agent.chat(
        "create workspace Acme subdomain acme",
        abilities=["workspaces:write"],
        auto_confirm=True,
    )
    assert response.status == "deny"
    assert "Quota" in response.message
    assert "acme" not in get_mock_store().workspaces
    assert "quota" in response.metadata
