import os

import pytest

pytestmark = pytest.mark.integration


@pytest.fixture
def tenant_kit_env():
    base_url = os.environ.get("TENANT_KIT_BASE_URL")
    token = os.environ.get("TENANT_KIT_API_TOKEN")
    if not base_url or not token:
        pytest.skip("Set TENANT_KIT_BASE_URL and TENANT_KIT_API_TOKEN for live integration")
    return {"base_url": base_url.rstrip("/"), "token": token}


@pytest.mark.asyncio
async def test_live_list_workspaces(tenant_kit_env):
    from workspace_agent.factory import build_agent
    from workspace_agent.core.config import Settings

    agent = build_agent(
        "yaml",
        config_path="examples/tenant-kit-adapter/adapter.yaml",
        token=tenant_kit_env["token"],
        base_url=tenant_kit_env["base_url"],
        settings=Settings(planner="mock"),
    )
    response = await agent.chat(
        "list workspaces",
        abilities=["workspaces:read"],
    )
    assert response.status == "ok"
    assert "list_workspaces" in response.message
