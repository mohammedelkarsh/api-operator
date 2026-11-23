"""Shared contracts for Safe API Agent (policy, quota, audit, dry-run).

These models are the public-ish data shapes hosts and sinks should rely on.
Features that emit them remain opt-in so existing adapters keep working.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class Decision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    CONFIRM = "confirm"


class PolicyDecision(BaseModel):
    """Result of PolicyEngine.check(...)."""

    decision: Decision
    reason: str | None = None
    rule_id: str | None = None
    tool: str | None = None
    requires_confirmation: bool = False

    @classmethod
    def allow(cls, *, tool: str | None = None, reason: str | None = None, rule_id: str | None = None) -> PolicyDecision:
        return cls(decision=Decision.ALLOW, tool=tool, reason=reason, rule_id=rule_id)

    @classmethod
    def deny(cls, reason: str, *, tool: str | None = None, rule_id: str | None = None) -> PolicyDecision:
        return cls(decision=Decision.DENY, reason=reason, tool=tool, rule_id=rule_id)

    @classmethod
    def confirm(
        cls,
        *,
        tool: str | None = None,
        reason: str | None = None,
        rule_id: str | None = None,
    ) -> PolicyDecision:
        return cls(
            decision=Decision.CONFIRM,
            tool=tool,
            reason=reason,
            rule_id=rule_id,
            requires_confirmation=True,
        )


class QuotaDecision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"


class QuotaReservation(BaseModel):
    """Reservation returned by QuotaGateway.check before tool execution."""

    decision: QuotaDecision
    reservation_id: str = Field(default_factory=lambda: str(uuid4()))
    estimated_cost: float = 0.0
    remaining: float | None = None
    reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def allow(
        cls,
        *,
        estimated_cost: float = 0.0,
        remaining: float | None = None,
        reservation_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> QuotaReservation:
        kwargs: dict[str, Any] = {
            "decision": QuotaDecision.ALLOW,
            "estimated_cost": estimated_cost,
            "remaining": remaining,
            "metadata": metadata or {},
        }
        if reservation_id:
            kwargs["reservation_id"] = reservation_id
        return cls(**kwargs)

    @classmethod
    def deny(cls, reason: str, *, estimated_cost: float = 0.0) -> QuotaReservation:
        return cls(
            decision=QuotaDecision.DENY,
            estimated_cost=estimated_cost,
            reason=reason,
        )


class AuditEvent(BaseModel):
    """One audited agent step (plan, policy, execute, deny, confirm)."""

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    session_id: str | None = None
    adapter: str | None = None
    tool: str | None = None
    arguments: dict[str, Any] = Field(default_factory=dict)
    decision: Decision | Literal["execute", "skip", "error"] | None = None
    result_status: str | None = None
    duration_ms: float | None = None
    tenant_id: str | None = None
    actor_id: str | None = None
    dry_run: bool = False
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DryRunRequestPreview(BaseModel):
    """What would have been sent to the upstream API (when known)."""

    method: str | None = None
    url: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)
    body: Any = None
    path_params: dict[str, Any] = Field(default_factory=dict)
    query: dict[str, Any] = Field(default_factory=dict)


class DryRunReport(BaseModel):
    """Machine-readable dry-run outcome for CLI / HTTP clients."""

    session_id: str
    message: str
    status: Literal["ok", "confirm", "deny", "error"] = "ok"
    tool: str | None = None
    arguments: dict[str, Any] = Field(default_factory=dict)
    policy: PolicyDecision | None = None
    quota: QuotaReservation | None = None
    would_call: DryRunRequestPreview | None = None
    dry_run: Literal[True] = True
    metadata: dict[str, Any] = Field(default_factory=dict)
