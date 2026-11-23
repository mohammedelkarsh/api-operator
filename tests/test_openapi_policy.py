from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from api_operator.adapters.openapi_generator import (
    generate_adapter_from_openapi,
    generate_policy_draft,
    save_policy_draft,
    scaffold_adapter,
)
from api_operator.adapters.yaml_spec import load_adapter_spec
from api_operator.server.cli import app

runner = CliRunner()


def test_openapi_marks_writes_dangerous_and_suggests_abilities(tmp_path: Path):
    spec = tmp_path / "api.yaml"
    spec.write_text(
        """
openapi: 3.0.0
info:
  title: Pets API
paths:
  /api/pets:
    get:
      tags: [Pets]
      summary: List pets
    post:
      tags: [Pets]
      summary: Create pet
      requestBody:
        content:
          application/json:
            schema:
              type: object
              required: [name]
              properties:
                name: { type: string }
""",
        encoding="utf-8",
    )
    adapter = generate_adapter_from_openapi(
        spec,
        base_url="http://pets.test",
        path_prefix="/api",
        include_methods={"GET", "POST"},
    )
    by_name = {t.name: t for t in adapter.tools}
    list_tool = next(t for t in adapter.tools if t.method == "GET")
    create_tool = next(t for t in adapter.tools if t.method == "POST")
    assert list_tool.dangerous is False
    assert list_tool.requires_ability == "pets:read"
    assert create_tool.dangerous is True
    assert create_tool.requires_ability == "pets:write"
    assert by_name  # non-empty


def test_policy_draft_includes_confirm_tools(tmp_path: Path):
    spec = tmp_path / "api.json"
    spec.write_text(
        json.dumps(
            {
                "openapi": "3.0.0",
                "info": {"title": "Demo"},
                "paths": {
                    "/api/items": {
                        "get": {"summary": "List", "tags": ["Items"]},
                        "post": {"summary": "Create", "tags": ["Items"]},
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    adapter = generate_adapter_from_openapi(
        spec,
        base_url="http://x.test",
        path_prefix="/api",
        include_methods={"GET", "POST"},
    )
    draft = generate_policy_draft(adapter)
    assert any(name for name in draft["confirm_tools"])
    policy_path = save_policy_draft(adapter, tmp_path / "policy.yaml")
    assert policy_path.is_file()
    text = policy_path.read_text(encoding="utf-8")
    assert "confirm_tools" in text


def test_scaffold_writes_policy(tmp_path: Path):
    path = scaffold_adapter("demo", tmp_path / "demo-adapter")
    assert path.name == "adapter.yaml"
    assert (path.parent / "policy.yaml").is_file()
    assert (path.parent / "README.md").is_file()


def test_cli_generate_writes_policy(tmp_path: Path):
    spec = tmp_path / "openapi.yaml"
    spec.write_text(
        """
openapi: 3.0.0
info:
  title: CLI Pets
paths:
  /api/pets:
    get:
      tags: [Pets]
      summary: List
    post:
      tags: [Pets]
      summary: Create
""",
        encoding="utf-8",
    )
    out = tmp_path / "adapter.yaml"
    result = runner.invoke(
        app,
        [
            "generate-from-openapi",
            str(spec),
            "--output",
            str(out),
            "--base-url",
            "http://cli.test",
            "--methods",
            "GET,POST",
        ],
    )
    assert result.exit_code == 0, result.stdout
    assert out.exists()
    policy = tmp_path / "policy.yaml"
    assert policy.exists()
    adapter = load_adapter_spec(out)
    create = next(t for t in adapter.tools if t.method == "POST")
    assert create.dangerous is True
    assert create.requires_ability == "pets:write"


def test_jsonplaceholder_example_loads():
    adapter = load_adapter_spec("examples/jsonplaceholder-adapter/adapter.yaml")
    assert adapter.name == "jsonplaceholder"
    names = {t.name for t in adapter.tools}
    assert "list_posts" in names
    assert "create_post" in names
    create = next(t for t in adapter.tools if t.name == "create_post")
    assert create.dangerous is True
