import pytest

from api_operator.adapters.mock import reset_mock_store
from api_operator.core.config import Settings
from api_operator.factory import build_agent


@pytest.fixture(autouse=True)
def clean():
    reset_mock_store()
    yield
    reset_mock_store()


@pytest.mark.asyncio
async def test_full_onboarding_scenario():
    """Create workspace → confirm → invite → list → connections."""
    agent = build_agent("mock", settings=Settings(planner="mock"))
    abilities = ["workspaces:read", "workspaces:write", "team:invite"]
    sid = None

    r1 = await agent.chat("list workspaces", session_id=sid, abilities=abilities)
    sid = r1.session_id
    assert r1.status == "ok"

    r2 = await agent.chat("create workspace Acme subdomain acme", session_id=sid, abilities=abilities)
    assert r2.status == "confirm"
    sid = r2.session_id

    r3 = await agent.chat("yes", session_id=sid, abilities=abilities)
    assert r3.status == "ok"
    assert r3.tool_result["data"]["subdomain"] == "acme"

    r4 = await agent.chat("invite boss@acme.com to acme admin", session_id=sid, abilities=abilities)
    assert r4.status == "confirm"

    r5 = await agent.chat("نعم", session_id=r4.session_id, abilities=abilities)
    assert r5.status == "ok"

    r6 = await agent.chat("list workspaces", session_id=sid, abilities=abilities)
    assert "acme" in r6.message.lower() or "Acme" in r6.message

    r7 = await agent.chat("provision link Riyadh Jeddah 500", session_id=sid)
    r8 = await agent.chat("yes", session_id=r7.session_id)
    assert r8.status == "ok"

    r9 = await agent.chat("list connections", session_id=sid)
    assert r9.status == "ok"


@pytest.mark.asyncio
async def test_arabic_cancel():
    agent = build_agent("mock", settings=Settings(planner="mock"))
    pending = await agent.chat(
        "create workspace Test subdomain test",
        abilities=["workspaces:write"],
    )
    cancelled = await agent.chat("لا", session_id=pending.session_id)
    assert "Cancelled" in cancelled.message


@pytest.mark.asyncio
async def test_auto_confirm_skips_prompt():
    agent = build_agent("mock", settings=Settings(planner="mock"))
    response = await agent.chat(
        "create workspace Fast subdomain fast",
        abilities=["workspaces:write"],
        auto_confirm=True,
    )
    assert response.status == "ok"
    assert response.tool == "create_workspace"


@pytest.mark.asyncio
async def test_pending_confirmation_survives_unrelated_message():
    agent = build_agent("mock", settings=Settings(planner="mock"))
    pending = await agent.chat("create workspace X subdomain x", abilities=["workspaces:write"])
    assert pending.status == "confirm"

    unrelated = await agent.chat("help", session_id=pending.session_id)
    assert unrelated.status == "ok"

    confirmed = await agent.chat("yes", session_id=pending.session_id, abilities=["workspaces:write"])
    assert confirmed.status == "ok"
    assert confirmed.tool == "create_workspace"


@pytest.mark.asyncio
async def test_help_lists_tools():
    agent = build_agent("mock", settings=Settings(planner="mock"))
    response = await agent.chat("help")
    assert response.status == "ok"
    assert "workspaces" in response.message.lower()
    assert "assistant" in response.message.lower()


@pytest.mark.asyncio
async def test_create_without_subdomain_clarifies():
    agent = build_agent("mock", settings=Settings(planner="mock"))
    response = await agent.chat("create workspace Acme", abilities=["workspaces:write"])
    assert response.status == "ok"
    assert "subdomain" in response.message.lower()


@pytest.mark.asyncio
async def test_duplicate_workspace_after_confirm():
    agent = build_agent("mock", settings=Settings(planner="mock"))
    abilities = ["workspaces:write"]
    await agent.chat("create workspace Acme subdomain acme", abilities=abilities, auto_confirm=True)
    fail = await agent.chat("create workspace Acme2 subdomain acme", abilities=abilities, auto_confirm=True)
    assert fail.status == "error"
    assert "already exists" in fail.message.lower() or fail.tool_result
