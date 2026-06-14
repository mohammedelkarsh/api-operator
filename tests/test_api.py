import json

import pytest
from httpx import ASGITransport, AsyncClient

from api_operator.adapters.mock import reset_mock_store
from api_operator.adapters.yaml_spec import load_adapter_spec, save_adapter_spec
from api_operator.core.config import Settings
from api_operator.factory import build_agent
from api_operator.server.app import create_app


@pytest.fixture(autouse=True)
def clean_mock():
    reset_mock_store()
    yield
    reset_mock_store()


@pytest.fixture
def app():
    return create_app(Settings(planner="mock", default_adapter="mock"))


@pytest.mark.asyncio
async def test_health(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "adapter_default" in body


@pytest.mark.asyncio
async def test_adapters_endpoint(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/v1/adapters")
    assert response.status_code == 200
    body = response.json()
    assert "mock" in body["builtin"]
    assert "yaml" in body["builtin"]


@pytest.mark.asyncio
async def test_tools_endpoint_mock(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/v1/tools?adapter=mock")
    assert response.status_code == 200
    assert len(response.json()["tools"]) == 5


@pytest.mark.asyncio
async def test_tools_endpoint_yaml(app):
    transport = ASGITransport(app=app)
    config = "examples/tenant-kit-adapter/adapter.yaml"
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/v1/tools?adapter=yaml&config_path={config}")
    assert response.status_code == 200
    names = {t["name"] for t in response.json()["tools"]}
    assert "list_workspaces" in names
    assert "invite_team_member" in names


@pytest.mark.asyncio
async def test_chat_help(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/v1/chat", json={"message": "help"})
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_chat_full_create_flow(app):
    transport = ASGITransport(app=app)
    abilities = ["workspaces:read", "workspaces:write", "team:invite"]
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r1 = await client.post(
            "/v1/chat",
            json={"message": "create workspace Acme subdomain acme", "abilities": abilities},
        )
        assert r1.json()["status"] == "confirm"
        sid = r1.json()["session_id"]

        r2 = await client.post(
            "/v1/chat",
            json={"message": "yes", "session_id": sid, "abilities": abilities},
        )
        assert r2.json()["status"] == "ok"
        assert r2.json()["tool_result"]["ok"] is True

        r3 = await client.post(
            "/v1/chat",
            json={"message": "list workspaces", "session_id": sid, "abilities": abilities},
        )
        assert r3.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_chat_yaml_adapter(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v1/chat",
            json={
                "adapter": "yaml",
                "config_path": "examples/tenant-kit-adapter/adapter.yaml",
                "adapter_config": {"token": "fake"},
                "message": "help",
            },
        )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_chat_invalid_adapter(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v1/chat",
            json={"adapter": "does_not_exist", "message": "hi"},
        )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_chat_auto_confirm(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v1/chat",
            json={
                "message": "create workspace X subdomain x",
                "abilities": ["workspaces:write"],
                "auto_confirm": True,
            },
        )
    assert response.json()["status"] == "ok"


def test_yaml_spec_roundtrip(tmp_path):
    original = load_adapter_spec("examples/tenant-kit-adapter/adapter.yaml")
    out = tmp_path / "roundtrip.yaml"
    save_adapter_spec(original, out)
    reloaded = load_adapter_spec(out)
    assert reloaded.name == original.name
    assert len(reloaded.tools) == len(original.tools)
    assert {t.name for t in reloaded.tools} == {t.name for t in original.tools}
