from __future__ import annotations

from pathlib import Path
from typing import Any

from api_operator.core.agent import Agent
from api_operator.core.audit import AuditSink
from api_operator.core.config import Settings
from api_operator.core.memory import SessionStore
from api_operator.core.policy import PolicyEngine
from api_operator.core.quota import QuotaGateway
from api_operator.rag.knowledge import KnowledgeStore
from api_operator.adapters.registry import load_adapter


def _resolve_policy_path(
    settings: Settings,
    config_path: str | None,
    policy_path: str | None,
) -> str | None:
    if policy_path:
        return policy_path
    if settings.policy_path:
        return settings.policy_path
    if config_path:
        sibling = Path(config_path).with_name("policy.yaml")
        if sibling.is_file():
            return str(sibling)
    return None


def build_agent(
    adapter_name: str = "mock",
    settings: Settings | None = None,
    adapter_class: str | None = None,
    config_path: str | None = None,
    sessions: SessionStore | None = None,
    policy: PolicyEngine | None = None,
    policy_path: str | None = None,
    audit: AuditSink | None = None,
    quota: QuotaGateway | None = None,
    knowledge: KnowledgeStore | None = None,
    **adapter_kwargs: Any,
) -> Agent:
    settings = settings or Settings()
    adapter = load_adapter(
        adapter_name,
        adapter_class=adapter_class,
        config_path=config_path,
        **adapter_kwargs,
    )
    resolved = _resolve_policy_path(settings, config_path, policy_path)
    return Agent(
        adapter=adapter,
        settings=settings,
        sessions=sessions,
        policy=policy,
        policy_path=resolved,
        audit=audit,
        quota=quota,
        knowledge=knowledge,
    )
