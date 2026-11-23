"""Policy engine — allow / deny / confirm before tool execution.

Loads optional ``policy.yaml`` next to an adapter. When no policy file is
provided, decisions fall back to existing Guardrails (ability + dangerous).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from api_operator.core.schemas import Decision, PolicyDecision
from api_operator.tools.base import Tool


class PolicyRule(BaseModel):
    """Single policy rule. First matching rule wins (document order)."""

    id: str | None = None
    # Matchers (all specified matchers must match)
    tools: list[str] = Field(default_factory=list)
    tool_prefix: str | None = None
    abilities_any: list[str] = Field(default_factory=list)
    abilities_all: list[str] = Field(default_factory=list)
    roles: list[str] = Field(default_factory=list)
    tenants: list[str] = Field(default_factory=list)
    # Effect
    effect: Decision = Decision.ALLOW
    reason: str | None = None
    # Optional session call cap for matched tools
    max_calls_per_session: int | None = None


class PolicyDocument(BaseModel):
    """Root shape of ``policy.yaml``."""

    version: int = 1
    name: str | None = None
    description: str | None = None
    default: Decision = Decision.ALLOW
    # Tools that always require confirmation (in addition to tool.dangerous)
    confirm_tools: list[str] = Field(default_factory=list)
    # Tools / prefixes denied for everyone
    deny_tools: list[str] = Field(default_factory=list)
    # Per-tool session limits (tool_name -> max calls)
    max_calls: dict[str, int] = Field(default_factory=dict)
    rules: list[PolicyRule] = Field(default_factory=list)


@dataclass
class PolicyContext:
    """Host-provided context for a policy check."""

    abilities: list[str] | None = None
    role: str | None = None
    tenant_id: str | None = None
    actor_id: str | None = None
    session_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class PolicyEngine:
    """Evaluate tool calls against an optional PolicyDocument."""

    def __init__(self, document: PolicyDocument | None = None) -> None:
        self.document = document or PolicyDocument()
        # session_id -> tool_name -> count
        self._call_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    @classmethod
    def from_yaml(cls, path: str | Path) -> PolicyEngine:
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            raise ValueError("policy.yaml must be a mapping")
        return cls(PolicyDocument.model_validate(data))

    @classmethod
    def load_optional(cls, path: str | Path | None) -> PolicyEngine:
        if path is None:
            return cls()
        p = Path(path)
        if not p.is_file():
            return cls()
        return cls.from_yaml(p)

    def record_call(self, session_id: str | None, tool_name: str) -> None:
        if not session_id:
            return
        self._call_counts[session_id][tool_name] += 1

    def session_call_count(self, session_id: str | None, tool_name: str) -> int:
        if not session_id:
            return 0
        return self._call_counts[session_id].get(tool_name, 0)

    def check(
        self,
        tool: Tool,
        *,
        context: PolicyContext | None = None,
        skip_confirmation: bool = False,
    ) -> PolicyDecision:
        ctx = context or PolicyContext()
        doc = self.document
        name = tool.name

        # 1) Explicit deny list
        if name in doc.deny_tools:
            return PolicyDecision.deny(
                f"Tool '{name}' is denied by policy.",
                tool=name,
                rule_id="deny_tools",
            )

        # 2) Session call limits (document-level)
        limit = doc.max_calls.get(name)
        if limit is not None:
            used = self.session_call_count(ctx.session_id, name)
            if used >= limit:
                return PolicyDecision.deny(
                    f"Tool '{name}' exceeded max_calls ({limit}) for this session.",
                    tool=name,
                    rule_id="max_calls",
                )

        # 3) Ordered rules — first matching DENY/CONFIRM wins.
        #    ALLOW means "pass this gate" (useful with default: deny) but
        #    confirmation / ability checks below still apply.
        matched_allow_rule: PolicyRule | None = None
        for rule in doc.rules:
            if not self._rule_matches(rule, tool, ctx):
                continue
            if rule.max_calls_per_session is not None:
                used = self.session_call_count(ctx.session_id, name)
                if used >= rule.max_calls_per_session:
                    return PolicyDecision.deny(
                        rule.reason
                        or f"Tool '{name}' exceeded rule max_calls_per_session "
                        f"({rule.max_calls_per_session}).",
                        tool=name,
                        rule_id=rule.id or "rule_max_calls",
                    )
            if rule.effect == Decision.DENY:
                return PolicyDecision.deny(
                    rule.reason or f"Denied by policy rule '{rule.id or 'unnamed'}'.",
                    tool=name,
                    rule_id=rule.id,
                )
            if rule.effect == Decision.CONFIRM and not skip_confirmation:
                return PolicyDecision.confirm(
                    tool=name,
                    reason=rule.reason
                    or f"Confirmation required by policy rule '{rule.id or 'unnamed'}'.",
                    rule_id=rule.id,
                )
            if rule.effect == Decision.ALLOW:
                matched_allow_rule = rule
                break

        # 4) Ability check (same semantics as Guardrails when abilities provided)
        if tool.requires_ability is not None and ctx.abilities is not None:
            if tool.requires_ability not in ctx.abilities:
                return PolicyDecision.deny(
                    f"Permission denied: tool '{name}' requires "
                    f"ability '{tool.requires_ability}'.",
                    tool=name,
                    rule_id="requires_ability",
                )

        # 5) Forced confirm list / dangerous flag
        if not skip_confirmation:
            if name in doc.confirm_tools:
                return PolicyDecision.confirm(
                    tool=name,
                    reason=f"Tool '{name}' requires confirmation (confirm_tools).",
                    rule_id="confirm_tools",
                )
            if tool.dangerous:
                return PolicyDecision.confirm(
                    tool=name,
                    reason=f"Tool '{name}' is marked dangerous.",
                    rule_id="dangerous",
                )

        # 6) Document default (ALLOW rule overrides default deny)
        if matched_allow_rule is not None:
            return PolicyDecision.allow(
                tool=name,
                reason=matched_allow_rule.reason,
                rule_id=matched_allow_rule.id,
            )
        if doc.default == Decision.DENY:
            return PolicyDecision.deny(
                f"Tool '{name}' denied by default policy.",
                tool=name,
                rule_id="default",
            )
        if doc.default == Decision.CONFIRM and not skip_confirmation:
            return PolicyDecision.confirm(
                tool=name,
                reason=f"Tool '{name}' requires confirmation by default policy.",
                rule_id="default",
            )
        return PolicyDecision.allow(tool=name, rule_id="default")

    def _rule_matches(self, rule: PolicyRule, tool: Tool, ctx: PolicyContext) -> bool:
        name = tool.name
        if rule.tools and name not in rule.tools:
            return False
        if rule.tool_prefix and not name.startswith(rule.tool_prefix):
            return False
        if rule.roles:
            if ctx.role is None or ctx.role not in rule.roles:
                return False
        if rule.tenants:
            if ctx.tenant_id is None or ctx.tenant_id not in rule.tenants:
                return False
        if rule.abilities_any:
            abilities = set(ctx.abilities or [])
            if not abilities.intersection(rule.abilities_any):
                return False
        if rule.abilities_all:
            abilities = set(ctx.abilities or [])
            if not set(rule.abilities_all).issubset(abilities):
                return False
        # Empty matchers = catch-all (use carefully for default deny rules)
        return True
