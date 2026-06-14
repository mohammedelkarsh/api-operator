from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from api_operator.adapters.base import Adapter
from api_operator.core.config import Settings
from api_operator.core.executor import ToolExecutor
from api_operator.core.guardrails import Guardrails
from api_operator.core.memory import Session, SessionStore
from api_operator.core.planner import Planner
from api_operator.core.planner_openai import build_planner
from api_operator.tools.base import ToolRegistry


@dataclass
class AgentResponse:
    session_id: str
    message: str
    status: str = "ok"  # ok | confirm | error
    tool: str | None = None
    tool_result: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class Agent:
    def __init__(
        self,
        adapter: Adapter,
        settings: Settings | None = None,
        planner: Planner | None = None,
        sessions: SessionStore | None = None,
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

    async def chat(
        self,
        message: str,
        session_id: str | None = None,
        abilities: list[str] | None = None,
        auto_confirm: bool = False,
    ) -> AgentResponse:
        session = self.sessions.get_or_create(session_id, self.adapter.name)
        session.add("user", message)

        if session.pending_confirmation and not auto_confirm:
            if self.guardrails.is_confirmation(message):
                pending = session.pending_confirmation
                session.pending_confirmation = None
                result, error = await self.executor.execute(
                    self.registry,
                    pending["tool_name"],
                    pending["tool_args"],
                    abilities=abilities,
                )
                return self._finalize_tool(session, pending["tool_name"], result, error)

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

        if self.guardrails.needs_confirmation(tool) and not auto_confirm:
            session.pending_confirmation = {
                "tool_name": plan.tool_name,
                "tool_args": plan.tool_args or {},
            }
            confirm_msg = self.executor.confirmation_message(tool, plan.tool_args or {})
            session.add("assistant", confirm_msg, status="confirm")
            return AgentResponse(
                session_id=session.id,
                message=confirm_msg,
                status="confirm",
                tool=plan.tool_name,
                metadata={"arguments": plan.tool_args or {}},
            )

        result, error = await self.executor.execute(
            self.registry,
            plan.tool_name,
            plan.tool_args,
            abilities=abilities,
        )
        return self._finalize_tool(session, plan.tool_name, result, error)

    def _finalize_tool(
        self,
        session: Session,
        tool_name: str,
        result: Any,
        error: str | None,
    ) -> AgentResponse:
        if error:
            session.add("assistant", error, status="error", tool=tool_name)
            return AgentResponse(
                session_id=session.id,
                message=error,
                status="error",
                tool=tool_name,
            )

        payload = result.to_dict() if result else {"ok": False}
        if payload.get("ok"):
            reply = f"{tool_name} succeeded: {payload.get('data')}"
            session.add("assistant", reply, status="ok", tool=tool_name)
            return AgentResponse(
                session_id=session.id,
                message=reply,
                status="ok",
                tool=tool_name,
                tool_result=payload,
            )

        err = payload.get("error", "Tool failed.")
        session.add("assistant", err, status="error", tool=tool_name)
        return AgentResponse(
            session_id=session.id,
            message=str(err),
            status="error",
            tool=tool_name,
            tool_result=payload,
        )

    def list_tools(self) -> list[dict[str, Any]]:
        return self.registry.schemas()
