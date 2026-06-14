from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

from workspace_agent.adapters.mock import reset_mock_store
from workspace_agent.adapters.openapi_generator import generate_adapter_from_openapi, scaffold_adapter
from workspace_agent.adapters.yaml_spec import save_adapter_spec
from workspace_agent.core.config import Settings
from workspace_agent.factory import build_agent
from workspace_agent.server.app import create_app

app = typer.Typer(no_args_is_help=True, help="Workspace Agent CLI")
console = Console()


def _build_agent_from_cli(
    adapter: str,
    adapter_class: str | None,
    config: str | None,
    planner: str,
    base_url: str | None,
    token: str | None,
) -> Any:
    settings = Settings(planner=planner, default_adapter=adapter)
    kwargs: dict[str, Any] = {}
    if base_url:
        kwargs["base_url"] = base_url
    if token:
        kwargs["token"] = token
    if adapter == "yaml" and not config:
        console.print("[red]--adapter yaml requires --config path/to/adapter.yaml[/red]")
        raise typer.Exit(code=1)
    return build_agent(
        adapter,
        settings=settings,
        adapter_class=adapter_class,
        config_path=config,
        **kwargs,
    )


@app.command("chat")
def chat(
    adapter: str = typer.Option("mock", help="Built-in adapter: mock | yaml"),
    config: str | None = typer.Option(None, help="Path to adapter.yaml (required for yaml adapter)"),
    adapter_class: str | None = typer.Option(None, help="External adapter class module:Class"),
    session_id: str | None = typer.Option(None, help="Reuse session id"),
    planner: str = typer.Option("mock", help="Planner: mock | openai | auto"),
    base_url: str | None = typer.Option(None, help="Override API base URL from YAML"),
    token: str | None = typer.Option(None, help="API bearer token"),
    auto_confirm: bool = typer.Option(False, help="Skip dangerous confirmations"),
) -> None:
    """Interactive chat in the terminal."""
    agent = _build_agent_from_cli(adapter, adapter_class, config, planner, base_url, token)
    sid = session_id
    label = config or adapter_class or adapter
    console.print(f"[bold green]Workspace Agent[/bold green] adapter={label} planner={planner}")
    console.print("Type 'exit' to quit.\n")

    while True:
        try:
            user_input = console.input("[bold cyan]you>[/bold cyan] ")
        except (EOFError, KeyboardInterrupt):
            console.print("\nBye.")
            break
        if user_input.strip().lower() in {"exit", "quit"}:
            break
        response = asyncio.run(
            agent.chat(
                message=user_input,
                session_id=sid,
                abilities=_default_abilities(adapter),
                auto_confirm=auto_confirm,
            )
        )
        sid = response.session_id
        color = {"ok": "green", "confirm": "yellow", "error": "red"}.get(response.status, "white")
        console.print(f"[bold {color}]agent>[/bold {color}] {response.message}")


@app.command("serve")
def serve(
    host: str = typer.Option("127.0.0.1", help="Host"),
    port: int = typer.Option(8100, help="Port"),
    adapter: str = typer.Option("mock", help="Default adapter"),
    planner: str = typer.Option("mock", help="Planner mode"),
) -> None:
    """Run HTTP API server."""
    import uvicorn

    settings = Settings(host=host, port=port, default_adapter=adapter, planner=planner)
    uvicorn.run(create_app(settings), host=host, port=port)


@app.command("tools")
def tools(
    adapter: str = typer.Option("mock", help="Adapter name"),
    config: str | None = typer.Option(None, help="adapter.yaml path for yaml adapter"),
    base_url: str | None = typer.Option(None, help="Override base URL"),
    token: str | None = typer.Option(None, help="API token"),
) -> None:
    """List registered tools for an adapter."""
    agent = _build_agent_from_cli(adapter, None, config, "mock", base_url, token)
    table = Table(title=f"Tools ({config or adapter})")
    table.add_column("Name")
    table.add_column("Dangerous")
    table.add_column("Ability")
    table.add_column("Description")
    for schema in agent.list_tools():
        table.add_row(
            schema["name"],
            str(schema.get("dangerous", False)),
            str(schema.get("requires_ability") or "-"),
            schema["description"],
        )
    console.print(table)


@app.command("scaffold-adapter")
def scaffold_cmd(
    name: str = typer.Argument(..., help="Adapter/project name"),
    output: str = typer.Option("examples", help="Output directory"),
    base_url: str = typer.Option("http://localhost:8000", help="Default API base URL"),
) -> None:
    """Create adapter.yaml + README template (no Python required)."""
    out_dir = Path(output) / f"{name}-adapter"
    path = scaffold_adapter(name, out_dir, base_url=base_url)
    console.print(f"[green]Created[/green] {path}")
    console.print(f"Edit the YAML, then run:\n  python -m workspace_agent.server.cli chat --adapter yaml --config {path}")


@app.command("generate-from-openapi")
def generate_openapi_cmd(
    spec: str = typer.Argument(..., help="OpenAPI YAML/JSON file"),
    output: str = typer.Option("adapter.yaml", help="Output adapter.yaml path"),
    base_url: str = typer.Option(..., help="API base URL"),
    path_prefix: str | None = typer.Option("/api", help="Only include paths starting with this prefix"),
    methods: str = typer.Option("GET,POST", help="Comma-separated HTTP methods to include"),
) -> None:
    """Generate adapter.yaml from an OpenAPI spec."""
    include = {m.strip().upper() for m in methods.split(",") if m.strip()}
    adapter_spec = generate_adapter_from_openapi(
        spec,
        base_url=base_url,
        path_prefix=path_prefix,
        include_methods=include,
    )
    save_adapter_spec(adapter_spec, output)
    console.print(f"[green]Generated[/green] {output} with {len(adapter_spec.tools)} tools")


@app.command("demo")
def demo() -> None:
    """Run an automated mock demo conversation."""
    reset_mock_store()
    agent = build_agent("mock", settings=Settings(planner="mock"))

    async def run() -> None:
        steps = [
            "list workspaces",
            "create workspace Acme subdomain acme",
            "yes",
            "invite admin@acme.com to acme admin",
            "yes",
            "list workspaces",
            "provision link Riyadh Jeddah 500",
            "yes",
            "list connections",
        ]
        sid = None
        for step in steps:
            console.print(f"[cyan]you>[/cyan] {step}")
            response = await agent.chat(
                message=step,
                session_id=sid,
                abilities=_default_abilities("mock"),
            )
            sid = response.session_id
            console.print(f"[green]agent>[/green] {response.message}\n")

    asyncio.run(run())
    console.print(Markdown("Demo complete. Try YAML adapter with examples/tenant-kit-adapter/adapter.yaml"))


def _default_abilities(adapter: str) -> list[str] | None:
    if adapter == "mock":
        return ["workspaces:read", "workspaces:write", "team:invite"]
    if adapter == "yaml":
        return ["workspaces:read", "workspaces:write", "team:invite"]
    return None


if __name__ == "__main__":
    app()
