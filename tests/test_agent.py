import pytest

from operator_agent.adapters.mock import get_mock_store, reset_mock_store
from operator_agent.core.config import Settings
from operator_agent.factory import build_agent


@pytest.fixture(autouse=True)
def clean_store():
    reset_mock_store()
    yield
    reset_mock_store()


@pytest.mark.asyncio
async def test_list_workspaces_empty():
    agent = build_agent("mock", settings=Settings(planner="mock"))
    response = await agent.chat("list workspaces", abilities=["workspaces:read"])
    assert response.status == "ok"
    assert "workspaces" in response.message.lower() or "succeeded" in response.message.lower()


@pytest.mark.asyncio
async def test_create_workspace_requires_confirmation():
    agent = build_agent("mock", settings=Settings(planner="mock"))
    response = await agent.chat(
        "create workspace Acme subdomain acme",
        abilities=["workspaces:write"],
    )
    assert response.status == "confirm"
    assert response.tool == "create_workspace"

    confirm = await agent.chat("yes", session_id=response.session_id, abilities=["workspaces:write"])
    assert confirm.status == "ok"
    assert confirm.tool_result["ok"] is True
    assert get_mock_store().workspaces["acme"]["name"] == "Acme"


@pytest.mark.asyncio
async def test_invite_member_flow():
    agent = build_agent("mock", settings=Settings(planner="mock"))
    abilities = ["workspaces:write", "team:invite"]

    await agent.chat("create workspace Acme subdomain acme", abilities=abilities, auto_confirm=True)
    pending = await agent.chat(
        "invite boss@acme.com to acme admin",
        abilities=abilities,
    )
    assert pending.status == "confirm"
    done = await agent.chat("yes", session_id=pending.session_id, abilities=abilities)
    assert done.status == "ok"
    assert len(get_mock_store().invitations) == 1


@pytest.mark.asyncio
async def test_permission_denied_without_ability():
    agent = build_agent("mock", settings=Settings(planner="mock"))
    response = await agent.chat(
        "create workspace Acme subdomain acme",
        abilities=["workspaces:read"],
        auto_confirm=True,
    )
    assert response.status == "error"
    assert "Permission denied" in response.message


@pytest.mark.asyncio
async def test_provision_link():
    agent = build_agent("mock", settings=Settings(planner="mock"))
    pending = await agent.chat("provision link Riyadh Jeddah 500")
    assert pending.status == "confirm"
    done = await agent.chat("yes", session_id=pending.session_id)
    assert done.status == "ok"
    assert "riyadh-jeddah" in get_mock_store().connections


@pytest.mark.asyncio
async def test_cancel_confirmation():
    agent = build_agent("mock", settings=Settings(planner="mock"))
    pending = await agent.chat(
        "create workspace Acme subdomain acme",
        abilities=["workspaces:write"],
    )
    cancelled = await agent.chat("no", session_id=pending.session_id)
    assert cancelled.status == "ok"
    assert "Cancelled" in cancelled.message
    assert "acme" not in get_mock_store().workspaces


def test_tool_registry_schemas():
    agent = build_agent("mock")
    schemas = agent.list_tools()
    names = {item["name"] for item in schemas}
    assert "create_workspace" in names
    assert "provision_link" in names
