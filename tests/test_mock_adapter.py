import pytest

from workspace_agent.adapters.mock import MockAdapter, get_mock_store, reset_mock_store
from workspace_agent.adapters.registry import available_adapters, load_adapter, register_adapter
from workspace_agent.adapters.base import Adapter
from workspace_agent.tools.base import ToolRegistry


@pytest.fixture(autouse=True)
def clean():
    reset_mock_store()
    yield
    reset_mock_store()


def test_available_adapters_includes_mock_and_yaml():
    names = available_adapters()
    assert "mock" in names
    assert "yaml" in names


def test_load_mock_adapter():
    adapter = load_adapter("mock")
    assert adapter.name == "mock"
    assert len(adapter.build_registry().list_tools()) == 5


def test_load_yaml_requires_config():
    with pytest.raises(ValueError, match="config_path"):
        load_adapter("yaml")


def test_load_unknown_adapter():
    with pytest.raises(ValueError, match="Unknown adapter"):
        load_adapter("nonexistent")


def test_register_custom_adapter():
    class DemoAdapter(Adapter):
        name = "demo"
        description = "demo"

        def build_registry(self) -> ToolRegistry:
            return ToolRegistry()

        def system_prompt(self) -> str:
            return "demo"

    register_adapter("demo", DemoAdapter)
    adapter = load_adapter("demo")
    assert adapter.name == "demo"


@pytest.mark.asyncio
async def test_mock_create_duplicate_workspace():
    adapter = MockAdapter()
    tool = adapter.build_registry().get("create_workspace")
    r1 = await tool.run(name="Acme", subdomain="acme")
    r2 = await tool.run(name="Acme2", subdomain="acme")
    assert r1.ok is True
    assert r2.ok is False
    assert "already exists" in r2.error


@pytest.mark.asyncio
async def test_mock_invite_missing_workspace():
    adapter = MockAdapter()
    tool = adapter.build_registry().get("invite_member")
    result = await tool.run(subdomain="missing", email="a@b.com")
    assert result.ok is False
    assert "not found" in result.error


@pytest.mark.asyncio
async def test_mock_provision_duplicate_link():
    adapter = MockAdapter()
    tool = adapter.build_registry().get("provision_link")
    await tool.run(site_a="Riyadh", site_b="Jeddah", bandwidth_mbps=100)
    result = await tool.run(site_a="Riyadh", site_b="Jeddah", bandwidth_mbps=200)
    assert result.ok is False


@pytest.mark.asyncio
async def test_mock_full_store_state():
    adapter = MockAdapter()
    reg = adapter.build_registry()
    await reg.get("create_workspace").run(name="Acme", subdomain="acme")
    await reg.get("invite_member").run(subdomain="acme", email="x@y.com", role="admin")
    await reg.get("provision_link").run(site_a="A", site_b="B")
    store = get_mock_store()
    assert len(store.workspaces) == 1
    assert len(store.invitations) == 1
    assert len(store.connections) == 1
