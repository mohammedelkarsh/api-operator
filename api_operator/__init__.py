"""API Operator — Safe API Agent with pluggable adapters."""

from api_operator.core.agent import Agent, AgentResponse
from api_operator.core.config import Settings
from api_operator.core.audit import AuditSink, JsonlAuditSink, MemoryAuditSink
from api_operator.core.policy import PolicyContext, PolicyEngine
from api_operator.core.quota import InMemoryQuotaGateway, QuotaGateway, UnlimitedQuotaGateway
from api_operator.core.schemas import (
    AuditEvent,
    Decision,
    DryRunReport,
    PolicyDecision,
    QuotaReservation,
)
from api_operator.tools.base import Tool, ToolRegistry

__all__ = [
    "Agent",
    "AgentResponse",
    "AuditEvent",
    "AuditSink",
    "Decision",
    "DryRunReport",
    "InMemoryQuotaGateway",
    "JsonlAuditSink",
    "MemoryAuditSink",
    "PolicyContext",
    "PolicyDecision",
    "PolicyEngine",
    "QuotaGateway",
    "QuotaReservation",
    "Settings",
    "Tool",
    "ToolRegistry",
    "UnlimitedQuotaGateway",
]
__version__ = "1.0.0"
