from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from workspace_agent.tools.schema import tool_parameters_schema


@dataclass(slots=True)
class ToolResult:
    ok: bool
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"ok": self.ok, "data": self.data}
        if self.error:
            payload["error"] = self.error
        return payload


@dataclass(slots=True)
class Tool:
    name: str
    description: str
    handler: Callable[..., ToolResult | Awaitable[ToolResult]]
    parameters: dict[str, type | str] = field(default_factory=dict)
    required: list[str] = field(default_factory=list)
    dangerous: bool = False
    requires_ability: str | None = None

    def schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": tool_parameters_schema(self.parameters, self.required),
            "dangerous": self.dangerous,
            "requires_ability": self.requires_ability,
        }

    async def run(self, **kwargs: Any) -> ToolResult:
        result = self.handler(**kwargs)
        if inspect.isawaitable(result):
            result = await result
        return result


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[Tool]:
        return list(self._tools.values())

    def schemas(self) -> list[dict[str, Any]]:
        return [tool.schema() for tool in self.list_tools()]

    def names(self) -> list[str]:
        return list(self._tools.keys())
