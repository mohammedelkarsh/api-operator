from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from workspace_agent.tools.base import ToolRegistry


class Adapter(ABC):
    name: str
    description: str

    @abstractmethod
    def build_registry(self) -> ToolRegistry:
        raise NotImplementedError

    @abstractmethod
    def system_prompt(self) -> str:
        raise NotImplementedError

    def auth_context(self) -> dict[str, Any]:
        return {}

    def docs_paths(self) -> list[str]:
        return []
