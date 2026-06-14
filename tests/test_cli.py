import json
from pathlib import Path

from typer.testing import CliRunner

from operator_agent.adapters.mock import reset_mock_store
from operator_agent.server.cli import app

runner = CliRunner()


def test_cli_demo():
    reset_mock_store()
    result = runner.invoke(app, ["demo"])
    assert result.exit_code == 0
    assert "list_workspaces succeeded" in result.stdout
    assert "Demo complete" in result.stdout


def test_cli_tools_mock():
    result = runner.invoke(app, ["tools", "--adapter", "mock"])
    assert result.exit_code == 0
    assert "create_workspace" in result.stdout
    assert "provision_link" in result.stdout


def test_cli_tools_yaml():
    result = runner.invoke(
        app,
        [
            "tools",
            "--adapter",
            "yaml",
            "--config",
            "examples/tenant-kit-adapter/adapter.yaml",
        ],
    )
    assert result.exit_code == 0
    assert "list_workspaces" in result.stdout
    assert "invite_team_member" in result.stdout


def test_cli_scaffold(tmp_path):
    out = tmp_path / "out"
    result = runner.invoke(
        app,
        ["scaffold-adapter", "myapp", "--output", str(out), "--base-url", "http://my.test"],
    )
    assert result.exit_code == 0
    config = out / "myapp-adapter" / "adapter.yaml"
    assert config.exists()
    assert "myapp" in config.read_text(encoding="utf-8")


def test_cli_generate_from_openapi(tmp_path):
    spec = tmp_path / "openapi.yaml"
    spec.write_text(
        """
openapi: 3.0.0
info:
  title: CLI Test API
paths:
  /api/widgets:
    get:
      summary: List widgets
""",
        encoding="utf-8",
    )
    out = tmp_path / "generated.yaml"
    result = runner.invoke(
        app,
        [
            "generate-from-openapi",
            str(spec),
            "--output",
            str(out),
            "--base-url",
            "http://cli.test",
        ],
    )
    assert result.exit_code == 0
    assert out.exists()
    assert "get_api_widgets" in out.read_text(encoding="utf-8")


def test_cli_chat_yaml_missing_config():
    result = runner.invoke(app, ["chat", "--adapter", "yaml"])
    assert result.exit_code == 1
    assert "requires --config" in result.stdout
