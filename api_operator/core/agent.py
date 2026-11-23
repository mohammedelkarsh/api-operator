from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from api_operator.adapters.base import Adapter
from api_operator.core.audit import (
    AuditSink,
    JsonlAuditSink,
    NullAuditSink,
    build_audit_event,
)
from api_operator.core.config import Settings
from api_operator.core.executor import ToolExecutor
from api_operator.core.formatters import format_tool_success
from api_operator.core.guardrails import Guardrails
from api_operator.core.memory import Session, SessionStore
from api_operator.core.planner import Planner
from api_operator.core.planner_openai import build_planner
from api_operator.core.policy import PolicyContext, PolicyEngine
from api_operator.core.quota import (
    InMemoryQuotaGateway,
    QuotaContext,
    QuotaGateway,
    UnlimitedQuotaGateway,
)
from api_operator.core.schemas import (
    Decision,
    DryRunReport,
    DryRunRequestPreview,
    PolicyDecision,
    QuotaDecision,
)
from api_operator.tools.base import ToolRegistry


@dataclass
class AgentResponse:
    session_id: str
    message: str
    status: str = "ok"  # ok | confirm | error | deny
    tool: str | None = None
    tool_result: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    dry_run_report: DryRunReport | None = None


class Agent:
    def __init__(
        self,
        adapter: Adapter,
        settings: Settings | None = None,
        planner: Planner | None = None,
        sessions: SessionStore | None = None,
        policy: PolicyEngine | None = None,
        policy_path: str | Path | None = None,
        audit: AuditSink | None = None,
        quota: QuotaGateway | None = None,
    ) -> None:
        self.settings = settings or Settings()
        self.adapter = adapter
        self.registry: ToolRegistry = adapter.build_registry()
        self.guardrails = Guardrails(
            require_confirm_dangerous=self.settings.require_confirm_dangerous
        )
        self.executor = ToolExecutor(self.guardrails)
        self.planner = planner or build_planner(self.settings)
        self.sessions = sessions or SessionStore()
        if policy is not None:
            self.policy = policy
        elif policy_path is not None:
            self.policy = PolicyEngine.load_optional(policy_path)
        else:
            self.policy = PolicyEngine()

        if audit is not None:
            self.audit = audit
        elif not self.settings.audit_enabled:
            self.audit = NullAuditSink()
        elif self.settings.audit_path:
            self.audit = JsonlAuditSink(self.settings.audit_path)
        else:
            self.audit = NullAuditSink()

        if quota is not None:
            self.quota = quota
        elif self.settings.quota_budget is not None:
            self.quota = InMemoryQuotaGateway(budget=self.settings.quota_budget)
        else:
            self.quota = UnlimitedQuotaGateway()

    async def chat(
        self,
        message: str,
        session_id: str | None = None,
        abilities: list[str] | None = None,
        auto_confirm: bool = False,
        *,
        dry_run: bool | None = None,
        role: str | None = None,
        tenant_id: str | None = None,
        actor_id: str | None = None,
        context_metadata: dict[str, Any] | None = None,
    ) -> AgentResponse:
        session = self.sessions.get_or_create(session_id, self.adapter.name)
        session.add("user", message)
        use_dry_run = self.settings.dry_run if dry_run is None else dry_run

        policy_ctx = PolicyContext(
            abilities=abilities,
            role=role,
            tenant_id=tenant_id,
            actor_id=actor_id,
            session_id=session.id,
            metadata=context_metadata or {},
        )

        if session.pending_confirmation and not auto_confirm and not use_dry_run:
            if self.guardrails.is_confirmation(message):
                pending = session.pending_confirmation
                session.pending_confirmation = None
                return await self._run_tool(
                    session,
                    pending["tool_name"],
                    pending["tool_args"],
                    policy_ctx,
                    skip_confirmation=True,
                )

            if self.guardrails.is_cancellation(message):
                session.pending_confirmation = None
                reply = "Cancelled. No changes were made."
                session.add("assistant", reply, status="ok")
                return AgentResponse(session_id=session.id, message=reply, status="ok")

        plan = await self.planner.plan(
            message=message,
            registry=self.registry,
            history=session.history(),
            system_prompt=self.adapter.system_prompt(),
        )

        if plan.type == "respond":
            session.add("assistant", plan.content, status="ok")
            return AgentResponse(session_id=session.id, message=plan.content, status="ok")

        if plan.type == "clarify":
            session.add("assistant", plan.content, status="ok")
            return AgentResponse(session_id=session.id, message=plan.content, status="ok")

        if plan.type != "tool" or not plan.tool_name:
            reply = "Could not determine an action."
            session.add("assistant", reply, status="error")
            return AgentResponse(session_id=session.id, message=reply, status="error")

        tool = self.registry.get(plan.tool_name)
        if tool is None:
            reply = f"Tool not found: {plan.tool_name}"
            session.add("assistant", reply, status="error")
            return AgentResponse(session_id=session.id, message=reply, status="error")

        return await self._run_tool(
            session,
            plan.tool_name,
            plan.tool_args or {},
            policy_ctx,
            skip_confirmation=auto_confirm,
            dry_run=use_dry_run,
        )

    async def _run_tool(
        self,
        session: Session,
        tool_name: str,
        tool_args: dict[str, Any],
        policy_ctx: PolicyContext,
        *,
        skip_confirmation: bool,
        dry_run: bool = False,
    ) -> AgentResponse:
        started = time.perf_counter()
        tool = self.registry.get(tool_name)
        if tool is None:
            reply = f"Tool not found: {tool_name}"
            session.add("assistant", reply, status="error")
            return AgentResponse(session_id=session.id, message=reply, status="error")

        decision = self.policy.check(
            tool,
            context=policy_ctx,
            skip_confirmation=skip_confirmation or not self.settings.require_confirm_dangerous,
        )

        if dry_run:
            response = self._dry_run_response(session, tool_name, tool_args, decision)
            self._emit_audit(
                session=session,
                tool_name=tool_name,
                tool_args=tool_args,
                policy_ctx=policy_ctx,
                decision=decision.decision.value,
                result_status=response.status,
                duration_ms=(time.perf_counter() - started) * 1000,
                dry_run=True,
            )
            return response

        if decision.decision == Decision.DENY:
            reply = decision.reason or f"Denied: {tool_name}"
            session.add("assistant", reply, status="deny", tool=tool_name)
            response = AgentResponse(
                session_id=session.id,
                message=reply,
                status="deny",
                tool=tool_name,
                metadata={"policy": decision.model_dump(mode="json")},
            )
            self._emit_audit(
                session=session,
                tool_name=tool_name,
                tool_args=tool_args,
                policy_ctx=policy_ctx,
                decision=Decision.DENY.value,
                result_status="deny",
                duration_ms=(time.perf_counter() - started) * 1000,
                error=reply,
            )
            return response

        if decision.decision == Decision.CONFIRM:
            session.pending_confirmation = {
                "tool_name": tool_name,
                "tool_args": tool_args,
            }
            confirm_msg = self.executor.confirmation_message(tool, tool_args)
            if decision.reason:
                confirm_msg = f"{confirm_msg}\n({decision.reason})"
            session.add("assistant", confirm_msg, status="confirm")
            response = AgentResponse(
                session_id=session.id,
                message=confirm_msg,
                status="confirm",
                tool=tool_name,
                metadata={
                    "arguments": tool_args,
                    "policy": decision.model_dump(mode="json"),
                },
            )
            self._emit_audit(
                session=session,
                tool_name=tool_name,
                tool_args=tool_args,
                policy_ctx=policy_ctx,
                decision=Decision.CONFIRM.value,
                result_status="confirm",
                duration_ms=(time.perf_counter() - started) * 1000,
            )
            return response

        quota_ctx = QuotaContext(
            tenant_id=policy_ctx.tenant_id,
            actor_id=policy_ctx.actor_id,
            session_id=session.id,
            tool=tool_name,
        )
        estimated = 1.0
        if isinstance(self.quota, InMemoryQuotaGateway):
            estimated = self.quota.estimate(tool_name)
        reservation = self.quota.check(quota_ctx, estimated)
        if reservation.decision == QuotaDecision.DENY:
            reply = reservation.reason or f"Quota exceeded for tool '{tool_name}'."
            session.add("assistant", reply, status="deny", tool=tool_name)
            response = AgentResponse(
                session_id=session.id,
                message=reply,
                status="deny",
                tool=tool_name,
                metadata={
                    "policy": decision.model_dump(mode="json"),
                    "quota": reservation.model_dump(mode="json"),
                },
            )
            self._emit_audit(
                session=session,
                tool_name=tool_name,
                tool_args=tool_args,
                policy_ctx=policy_ctx,
                decision=Decision.DENY.value,
                result_status="deny",
                duration_ms=(time.perf_counter() - started) * 1000,
                error=reply,
                metadata={"quota": reservation.model_dump(mode="json")},
            )
            return response

        result, error = await self.executor.execute(
            self.registry,
            tool_name,
            tool_args,
            abilities=policy_ctx.abilities,
        )
        if error is None:
            self.policy.record_call(session.id, tool_name)
            self.quota.commit(quota_ctx, estimated, reservation.reservation_id)
        else:
            self.quota.rollback(quota_ctx, reservation.reservation_id)

        response = self._finalize_tool(
            session,
            tool_name,
            result,
            error,
            policy=decision,
            quota=reservation.model_dump(mode="json"),
        )
        self._emit_audit(
            session=session,
            tool_name=tool_name,
            tool_args=tool_args,
            policy_ctx=policy_ctx,
            decision=Decision.ALLOW.value,
            result_status=response.status,
            duration_ms=(time.perf_counter() - started) * 1000,
            error=error,
            metadata={"quota": reservation.model_dump(mode="json")},
        )
        return response

    def _dry_run_response(
        self,
        session: Session,
        tool_name: str,
        tool_args: dict[str, Any],
        decision: PolicyDecision,
    ) -> AgentResponse:
        preview_raw = self.adapter.preview_tool_call(tool_name, tool_args)
        would_call = None
        if isinstance(preview_raw, dict) and "error" not in preview_raw:
            would_call = DryRunRequestPreview(
                method=preview_raw.get("method"),
                url=preview_raw.get("url"),
                headers=preview_raw.get("headers") or {},
                body=preview_raw.get("body"),
                path_params=preview_raw.get("path_params") or {},
                query=preview_raw.get("query") or {},
            )

        status_map = {
            Decision.ALLOW: "ok",
            Decision.DENY: "deny",
            Decision.CONFIRM: "confirm",
        }
        status = status_map[decision.decision]
        if decision.decision == Decision.ALLOW:
            reply = (
                f"[dry-run] Would call `{tool_name}` with {tool_args}. "
                "No side effects executed."
            )
        elif decision.decision == Decision.DENY:
            reply = f"[dry-run] Denied: {decision.reason or tool_name}"
        else:
            reply = (
                f"[dry-run] Would require confirmation for `{tool_name}` "
                f"with {tool_args}."
            )

        report = DryRunReport(
            session_id=session.id,
            message=reply,
            status=status,  # type: ignore[arg-type]
            tool=tool_name,
            arguments=tool_args,
            policy=decision,
            would_call=would_call,
            metadata=(
                {"preview_error": preview_raw.get("error")}
                if preview_raw and "error" in preview_raw
                else {}
            ),
        )
        session.add("assistant", reply, status=status, tool=tool_name, dry_run=True)
        return AgentResponse(
            session_id=session.id,
            message=reply,
            status=status,
            tool=tool_name,
            metadata={
                "dry_run": True,
                "policy": decision.model_dump(mode="json"),
                "arguments": tool_args,
                "would_call": would_call.model_dump(mode="json") if would_call else preview_raw,
            },
            dry_run_report=report,
        )

    def _finalize_tool(
        self,
        session: Session,
        tool_name: str,
        result: Any,
        error: str | None,
        *,
        policy: PolicyDecision | None = None,
        quota: dict[str, Any] | None = None,
    ) -> AgentResponse:
        meta: dict[str, Any] = {}
        if policy is not None:
            meta["policy"] = policy.model_dump(mode="json")
        if quota is not None:
            meta["quota"] = quota

        if error:
            status = "deny" if error.startswith("Permission denied") else "error"
            session.add("assistant", error, status=status, tool=tool_name)
            return AgentResponse(
                session_id=session.id,
                message=error,
                status=status,
                tool=tool_name,
                metadata=meta,
            )

        payload = result.to_dict() if result else {"ok": False}
        if payload.get("ok"):
            reply = format_tool_success(tool_name, payload.get("data") or {})
            session.add("assistant", reply, status="ok", tool=tool_name)
            return AgentResponse(
                session_id=session.id,
                message=reply,
                status="ok",
                tool=tool_name,
                tool_result=payload,
                metadata=meta,
            )

        err = payload.get("error", "Tool failed.")
        session.add("assistant", err, status="error", tool=tool_name)
        return AgentResponse(
            session_id=session.id,
            message=str(err),
            status="error",
            tool=tool_name,
            tool_result=payload,
            metadata=meta,
        )

    def _emit_audit(
        self,
        *,
        session: Session,
        tool_name: str,
        tool_args: dict[str, Any],
        policy_ctx: PolicyContext,
        decision: str,
        result_status: str,
        duration_ms: float,
        dry_run: bool = False,
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if not self.settings.audit_enabled:
            return
        event = build_audit_event(
            session_id=session.id,
            adapter=self.adapter.name,
            tool=tool_name,
            arguments=tool_args,
            decision=decision,
            result_status=result_status,
            duration_ms=duration_ms,
            tenant_id=policy_ctx.tenant_id,
            actor_id=policy_ctx.actor_id,
            dry_run=dry_run,
            error=error,
            metadata=metadata,
        )
        self.audit.emit(event)

    def list_tools(self) -> list[dict[str, Any]]:
        return self.registry.schemas()
