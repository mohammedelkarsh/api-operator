import os

import json

import pytest

from api_operator.adapters.openapi_generator import generate_adapter_from_openapi
from api_operator.adapters.yaml_adapter import YamlAdapter, _token_from_env
from api_operator.adapters.yaml_spec import save_adapter_spec
from api_operator.core.config import Settings
from api_operator.factory import build_agent
from api_operator.rag.indexer import DocsIndex


TENANT_YAML = """
name: tenant_test
description: tenant
base_url: http://app.test
tools:
  - name: invite_team_member
    method: POST
    path: /api/team/invitations
    host: tenant
    tenant_param: subdomain
    parameters:
      subdomain: { type: string, required: true }
      email: { type: string, required: true }
    body:
      email: "{email}"
      role: member
"""


@pytest.mark.asyncio
async def test_yaml_tenant_host_url(tmp_path, monkeypatch):
    path = tmp_path / "t.yaml"
    path.write_text(TENANT_YAML, encoding="utf-8")
    adapter = YamlAdapter(config_path=str(path), token="tok")
    spec = next(t for t in adapter.spec.tools if t.name == "invite_team_member")

    captured = {}

    class FakeResponse:
        status_code = 201
        text = ""
        def json(self): return {"ok": True}
        @property
        def is_success(self): return True

    class FakeClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def request(self, method, url, **kwargs):
            captured["url"] = url
            return FakeResponse()

    monkeypatch.setattr("api_operator.adapters.yaml_adapter.httpx.AsyncClient", lambda **k: FakeClient())
    result = await adapter._execute(spec, {"subdomain": "acme", "email": "a@b.com"})
    assert result.ok
    assert captured["url"] == "http://acme.app.test/api/team/invitations"


@pytest.mark.asyncio
async def test_yaml_missing_token(tmp_path):
    path = tmp_path / "a.yaml"
    path.write_text(
        "name: x\nbase_url: http://t.test\ntools:\n  - name: t\n    method: GET\n    path: /\n",
        encoding="utf-8",
    )
    adapter = YamlAdapter(config_path=str(path), token=None)
    spec = adapter.spec.tools[0]
    result = await adapter._execute(spec, {})
    assert result.ok is False
    assert "token" in result.error.lower()


@pytest.mark.asyncio
async def test_yaml_api_error_response(tmp_path, monkeypatch):
    path = tmp_path / "a.yaml"
    path.write_text(
        "name: x\nbase_url: http://t.test\ntools:\n  - name: t\n    method: GET\n    path: /fail\n",
        encoding="utf-8",
    )
    adapter = YamlAdapter(config_path=str(path), token="tok")
    spec = adapter.spec.tools[0]

    class FakeResponse:
        status_code = 403
        text = "Forbidden"
        def json(self): return {"message": "Forbidden"}
        @property
        def is_success(self): return False

    class FakeClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def request(self, *a, **k): return FakeResponse()

    monkeypatch.setattr("api_operator.adapters.yaml_adapter.httpx.AsyncClient", lambda **k: FakeClient())
    result = await adapter._execute(spec, {})
    assert result.ok is False
    assert "403" in result.error


def test_token_from_env(monkeypatch):
    monkeypatch.setenv("MY_TOKEN", "secret")
    assert _token_from_env("MY_TOKEN") == "secret"
    assert _token_from_env(None) is None


def test_openapi_json_format(tmp_path):
    spec = tmp_path / "api.json"
    spec.write_text(
        json.dumps(
            {
                "openapi": "3.0.0",
                "info": {"title": "JSON API"},
                "paths": {"/api/ping": {"get": {"summary": "Ping"}}},
            }
        ),
        encoding="utf-8",
    )
    adapter_spec = generate_adapter_from_openapi(spec, base_url="http://x.test", path_prefix="/api")
    assert len(adapter_spec.tools) == 1


def test_openapi_empty_raises(tmp_path):
    spec = tmp_path / "empty.yaml"
    spec.write_text("openapi: 3.0.0\ninfo:\n  title: E\npaths: {}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="No tools generated"):
        generate_adapter_from_openapi(spec, base_url="http://x.test")


def test_rag_search(tmp_path):
    doc = tmp_path / "doc.md"
    doc.write_text(
        "Workspace provisioning uses tenant:provision command.\n\n"
        "Short.\n\n"
        "Multi-tenant SaaS applications require isolated databases per workspace.",
        encoding="utf-8",
    )
    index = DocsIndex([doc])
    hits = index.search("workspace provisioning tenant")
    assert len(hits) >= 1
    assert "provisioning" in hits[0]["excerpt"].lower()


def test_rag_missing_file():
    index = DocsIndex(["/nonexistent/file.md"])
    assert index.chunks == []


@pytest.mark.asyncio
async def test_yaml_agent_chat_with_mock_http(tmp_path, monkeypatch):
    yaml_path = tmp_path / "adapter.yaml"
    yaml_path.write_text(
        """
name: api
base_url: http://api.test
tools:
  - name: list_workspaces
    method: GET
    path: /api/workspaces
""",
        encoding="utf-8",
    )

    class FakeResponse:
        status_code = 200
        text = ""
        def json(self): return {"data": [{"id": "a"}]}
        @property
        def is_success(self): return True

    class FakeClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def request(self, *a, **k): return FakeResponse()

    monkeypatch.setattr("api_operator.adapters.yaml_adapter.httpx.AsyncClient", lambda **k: FakeClient())

    agent = build_agent("yaml", config_path=str(yaml_path), token="t", settings=Settings(planner="mock"))
    response = await agent.chat("list workspaces", abilities=["workspaces:read"])
    assert response.status == "ok"
    assert "list_workspaces" in response.message
