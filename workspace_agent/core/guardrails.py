from __future__ import annotations

from typing import Any

from workspace_agent.tools.base import Tool


class Guardrails:
    def __init__(self, require_confirm_dangerous: bool = True) -> None:
        self.require_confirm_dangerous = require_confirm_dangerous

    def check_ability(self, tool: Tool, abilities: list[str] | None) -> str | None:
        if tool.requires_ability is None:
            return None
        if abilities is None:
            return None
        if tool.requires_ability not in abilities:
            return (
                f"Permission denied: tool '{tool.name}' requires "
                f"ability '{tool.requires_ability}'."
            )
        return None

    def missing_parameters(self, tool: Tool, arguments: dict[str, Any]) -> list[str]:
        missing: list[str] = []
        for name in tool.required:
            value = arguments.get(name)
            if value is None or (isinstance(value, str) and not value.strip()):
                missing.append(name)
        return missing

    def needs_confirmation(self, tool: Tool) -> bool:
        return self.require_confirm_dangerous and tool.dangerous

    @staticmethod
    def is_confirmation(message: str) -> bool:
        normalized = message.strip().lower()
        return normalized in {
            "yes",
            "y",
            "confirm",
            "ok",
            "okay",
            "نعم",
            "أكد",
            "اكد",
            "موافق",
        }

    @staticmethod
    def is_cancellation(message: str) -> bool:
        normalized = message.strip().lower()
        return normalized in {"no", "n", "cancel", "stop", "لا", "الغ", "إلغاء", "الغاء"}
