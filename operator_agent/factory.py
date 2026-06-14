from __future__ import annotations

from typing import Any

from operator_agent.core.agent import Agent
from operator_agent.core.config import Settings
from operator_agent.core.memory import SessionStore
from operator_agent.adapters.registry import load_adapter


def build_agent(
    adapter_name: str = "mock",
    settings: Settings | None = None,
    adapter_class: str | None = None,
    config_path: str | None = None,
    sessions: SessionStore | None = None,
    **adapter_kwargs: Any,
) -> Agent:
    settings = settings or Settings()
    adapter = load_adapter(
        adapter_name,
        adapter_class=adapter_class,
        config_path=config_path,
        **adapter_kwargs,
    )
    return Agent(adapter=adapter, settings=settings, sessions=sessions)
