from __future__ import annotations

from typing import Any

from workspace_agent.adapters.base import Adapter
from workspace_agent.tools.base import Tool, ToolRegistry, ToolResult


class _MockStore:
    workspaces: dict[str, dict[str, Any]] = {}
    invitations: list[dict[str, Any]] = []
    connections: dict[str, dict[str, Any]] = {}


def reset_mock_store() -> None:
    _MockStore.workspaces.clear()
    _MockStore.invitations.clear()
    _MockStore.connections.clear()


class MockAdapter(Adapter):
    name = "mock"
    description = "In-memory demo adapter for SaaS + connectivity scenarios"

    def build_registry(self) -> ToolRegistry:
        registry = ToolRegistry()
        registry.register(
            Tool(
                name="list_workspaces",
                description="List all mock workspaces",
                handler=self._list_workspaces,
                parameters={},
            )
        )
        registry.register(
            Tool(
                name="create_workspace",
                description="Create a mock workspace with name and subdomain",
                handler=self._create_workspace,
                parameters={"name": str, "subdomain": str},
                required=["name", "subdomain"],
                dangerous=True,
                requires_ability="workspaces:write",
            )
        )
        registry.register(
            Tool(
                name="invite_member",
                description="Invite a team member to a workspace by subdomain",
                handler=self._invite_member,
                parameters={"subdomain": str, "email": str, "role": str},
                required=["subdomain", "email"],
                dangerous=True,
                requires_ability="team:invite",
            )
        )
        registry.register(
            Tool(
                name="list_connections",
                description="List network connections (connectivity demo)",
                handler=self._list_connections,
                parameters={},
            )
        )
        registry.register(
            Tool(
                name="provision_link",
                description="Provision a network link between two sites",
                handler=self._provision_link,
                parameters={"site_a": str, "site_b": str, "bandwidth_mbps": int},
                required=["site_a", "site_b"],
                dangerous=True,
            )
        )
        return registry

    def system_prompt(self) -> str:
        return (
            "You are Workspace Agent (mock mode). You help operators manage "
            "workspaces and network links using registered tools only. "
            "Reply in the user's language (Arabic or English). "
            "Never claim an action succeeded unless a tool returned ok=true."
        )

    async def _list_workspaces(self) -> ToolResult:
        items = list(_MockStore.workspaces.values())
        return ToolResult(ok=True, data={"workspaces": items, "count": len(items)})

    async def _create_workspace(self, name: str, subdomain: str) -> ToolResult:
        key = subdomain.strip().lower()
        if key in _MockStore.workspaces:
            return ToolResult(ok=False, error=f"Workspace '{key}' already exists.")
        workspace = {
            "id": key,
            "name": name.strip(),
            "subdomain": key,
            "url": f"https://{key}.example.test",
        }
        _MockStore.workspaces[key] = workspace
        return ToolResult(ok=True, data=workspace)

    async def _invite_member(
        self,
        subdomain: str,
        email: str,
        role: str = "member",
    ) -> ToolResult:
        key = subdomain.strip().lower()
        if key not in _MockStore.workspaces:
            return ToolResult(ok=False, error=f"Workspace '{key}' not found.")
        invitation = {
            "workspace": key,
            "email": email.strip().lower(),
            "role": role.strip().lower() or "member",
            "status": "sent",
        }
        _MockStore.invitations.append(invitation)
        return ToolResult(ok=True, data=invitation)

    async def _list_connections(self) -> ToolResult:
        items = list(_MockStore.connections.values())
        return ToolResult(ok=True, data={"connections": items, "count": len(items)})

    async def _provision_link(
        self,
        site_a: str,
        site_b: str,
        bandwidth_mbps: int = 100,
    ) -> ToolResult:
        link_id = f"{site_a.strip().lower()}-{site_b.strip().lower()}"
        if link_id in _MockStore.connections:
            return ToolResult(ok=False, error=f"Link '{link_id}' already exists.")
        link = {
            "id": link_id,
            "site_a": site_a.strip(),
            "site_b": site_b.strip(),
            "bandwidth_mbps": bandwidth_mbps,
            "status": "active",
        }
        _MockStore.connections[link_id] = link
        return ToolResult(ok=True, data=link)


def get_mock_store() -> _MockStore:
    return _MockStore
