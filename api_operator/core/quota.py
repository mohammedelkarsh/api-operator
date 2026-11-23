"""Quota / budget hooks — host owns real billing; core only gates execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from api_operator.core.schemas import QuotaDecision, QuotaReservation


@dataclass
class QuotaContext:
    tenant_id: str | None = None
    actor_id: str | None = None
    session_id: str | None = None
    tool: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class QuotaGateway(Protocol):
    def check(self, context: QuotaContext, estimated_cost: float) -> QuotaReservation: ...

    def commit(self, context: QuotaContext, actual_cost: float, reservation_id: str) -> None: ...

    def rollback(self, context: QuotaContext, reservation_id: str) -> None: ...


class UnlimitedQuotaGateway:
    """Default: never block. Useful until a host wires real metering."""

    def check(self, context: QuotaContext, estimated_cost: float) -> QuotaReservation:
        return QuotaReservation.allow(estimated_cost=estimated_cost)

    def commit(self, context: QuotaContext, actual_cost: float, reservation_id: str) -> None:
        return None

    def rollback(self, context: QuotaContext, reservation_id: str) -> None:
        return None


class InMemoryQuotaGateway:
    """Simple local budget for demos and tests."""

    def __init__(self, budget: float = 100.0, *, tool_costs: dict[str, float] | None = None) -> None:
        self.budget = budget
        self.spent = 0.0
        self.tool_costs = tool_costs or {}
        self._reservations: dict[str, float] = {}

    def estimate(self, tool_name: str | None, fallback: float = 1.0) -> float:
        if tool_name and tool_name in self.tool_costs:
            return self.tool_costs[tool_name]
        return fallback

    def check(self, context: QuotaContext, estimated_cost: float) -> QuotaReservation:
        remaining = self.budget - self.spent
        if estimated_cost > remaining:
            return QuotaReservation.deny(
                f"Quota exceeded: need {estimated_cost}, remaining {remaining}.",
                estimated_cost=estimated_cost,
            )
        reservation = QuotaReservation.allow(
            estimated_cost=estimated_cost,
            remaining=remaining - estimated_cost,
        )
        self._reservations[reservation.reservation_id] = estimated_cost
        # Hold estimated cost until commit/rollback
        self.spent += estimated_cost
        return reservation

    def commit(self, context: QuotaContext, actual_cost: float, reservation_id: str) -> None:
        held = self._reservations.pop(reservation_id, 0.0)
        self.spent = self.spent - held + actual_cost

    def rollback(self, context: QuotaContext, reservation_id: str) -> None:
        held = self._reservations.pop(reservation_id, 0.0)
        self.spent -= held
