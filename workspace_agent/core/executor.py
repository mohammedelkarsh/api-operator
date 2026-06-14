from __future__ import annotations

from typing import Any

from workspace_agent.core.guardrails import Guardrails
from workspace_agent.tools.base import Tool, ToolRegistry, ToolResult


class ToolExecutor:
    def __init__(self, guardrails: Guardrails | None = None) -> None:
        self.guardrails = guardrails or Guardrails()

    async def execute(
        self,
        registry: ToolRegistry,
        tool_name: str,
        arguments: dict[str, Any] | None,
        abilities: list[str] | None = None,
    ) -> tuple[ToolResult | None, str | None]:
        tool = registry.get(tool_name)
        if tool is None:
            return None, f"Unknown tool: {tool_name}"

        permission_error = self.guardrails.check_ability(tool, abilities)
        if permission_error:
            return None, permission_error

        args = arguments or {}
        missing = self.guardrails.missing_parameters(tool, args)
        if missing:
            return None, f"Missing required parameters: {', '.join(missing)}"

        result = await tool.run(**args)
        return result, None

    def confirmation_message(self, tool: Tool, arguments: dict[str, Any]) -> str:
        rendered = ", ".join(f"{k}={v!r}" for k, v in arguments.items())
        return f"Confirm {tool.name}({rendered})? Reply yes to proceed or no to cancel."
