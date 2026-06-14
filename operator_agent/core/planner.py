from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from operator_agent.tools.base import ToolRegistry


@dataclass
class PlanStep:
    type: str  # respond | tool | clarify
    content: str = ""
    tool_name: str | None = None
    tool_args: dict[str, Any] | None = None


class Planner(Protocol):
    async def plan(
        self,
        message: str,
        registry: ToolRegistry,
        history: list[dict[str, str]],
        system_prompt: str,
    ) -> PlanStep: ...


class MockPlanner:
    """Rule-based planner for offline demos and tests (no LLM required)."""

    async def plan(
        self,
        message: str,
        registry: ToolRegistry,
        history: list[dict[str, str]],
        system_prompt: str,
    ) -> PlanStep:
        text = message.strip()
        lower = text.lower()

        if "help" in lower or "مساعدة" in text or lower.strip() == "tools":
            names = ", ".join(registry.names())
            return PlanStep(
                type="respond",
                content=(
                    "I can run these tools: "
                    f"{names}. Try: 'list workspaces', 'create workspace Acme subdomain acme', "
                    "'invite admin@acme.com to acme', 'provision link Riyadh Jeddah 500'."
                ),
            )

        if _wants_create_workspace(lower):
            args = _extract_workspace_args(text)
            if args.get("name") and args.get("subdomain") and registry.get("create_workspace"):
                return PlanStep(
                    type="tool",
                    tool_name="create_workspace",
                    tool_args=args,
                )
            return PlanStep(
                type="clarify",
                content="Please provide workspace name and subdomain (e.g. name Acme, subdomain acme).",
            )

        if _wants_invite(lower, text):
            tool_name = "invite_member" if registry.get("invite_member") else "invite_team_member"
            if registry.get(tool_name):
                args = _extract_invite_args(text)
                if args.get("email"):
                    subdomain = args.get("subdomain") or "acme"
                    return PlanStep(
                        type="tool",
                        tool_name=tool_name,
                        tool_args={
                            "subdomain": subdomain,
                            "email": args["email"],
                            "role": args.get("role", "member"),
                        },
                    )
                return PlanStep(type="clarify", content="Which email should I invite?")

        if _wants_provision_link(lower):
            args = _extract_link_args(text)
            if args.get("site_a") and args.get("site_b") and registry.get("provision_link"):
                return PlanStep(type="tool", tool_name="provision_link", tool_args=args)

        if _wants_list_connections(lower, text) and registry.get("list_connections"):
            return PlanStep(type="tool", tool_name="list_connections", tool_args={})

        if _wants_list_workspaces(lower, text) and registry.get("list_workspaces"):
            return PlanStep(type="tool", tool_name="list_workspaces", tool_args={})

        return PlanStep(
            type="respond",
            content=(
                "I did not map that request to a tool. Say 'help' to see examples, or be explicit "
                "(e.g. 'list workspaces', 'create workspace Acme subdomain acme')."
            ),
        )


def _wants_create_workspace(lower: str) -> bool:
    return (
        "create workspace" in lower
        or "new workspace" in lower
        or "أنشئ workspace" in lower
        or "انشئ workspace" in lower
    )


def _wants_invite(lower: str, text: str) -> bool:
    return "invite" in lower or "ادع" in lower or "دعوة" in text


def _wants_provision_link(lower: str) -> bool:
    return "provision link" in lower or ("provision" in lower and "link" in lower)


def _wants_list_connections(lower: str, text: str) -> bool:
    if not ("connection" in lower or "link" in lower or "اتصال" in text or "رابط" in text):
        return False
    return any(word in lower for word in ("list", "show", "display")) or "اعرض" in text


def _wants_list_workspaces(lower: str, text: str) -> bool:
    if "workspace" not in lower and "workspace" not in text:
        return False
    if _wants_create_workspace(lower):
        return False
    return (
        "list workspace" in lower
        or "list workspaces" in lower
        or "show workspace" in lower
        or "show workspaces" in lower
        or lower.strip() == "workspaces"
        or "ورّيني" in text
        or "اعرض" in text
    )


def _extract_workspace_args(text: str) -> dict[str, Any]:
    args: dict[str, Any] = {}
    lower = text.lower()
    if "subdomain" in lower:
        parts = lower.split("subdomain", 1)[1].strip().split()
        if parts:
            args["subdomain"] = parts[0].strip(",.")
    if "name" in lower:
        segment = text.split("name", 1)[1]
        if "subdomain" in segment.lower():
            segment = segment.split("subdomain", 1)[0]
        args["name"] = segment.strip().strip(",.")
    tokens = text.replace(",", " ").split()
    for idx, token in enumerate(tokens):
        if token.lower() == "workspace" and idx + 1 < len(tokens):
            maybe_name = tokens[idx + 1]
            if maybe_name.lower() not in {"subdomain", "named", "on"}:
                args.setdefault("name", maybe_name)
        if token.lower() == "subdomain" and idx + 1 < len(tokens):
            args["subdomain"] = tokens[idx + 1].strip(".,")
    return args


def _extract_invite_args(text: str) -> dict[str, Any]:
    args: dict[str, Any] = {}
    for token in text.replace(",", " ").split():
        if "@" in token:
            args["email"] = token.strip(".,")
    lower = text.lower()
    if " to " in lower:
        subdomain = lower.split(" to ", 1)[1].strip().split()[0]
        args["subdomain"] = subdomain.strip(".,")
    for token in text.split():
        if token.lower() in {"admin", "member"}:
            args["role"] = token.lower()
    return args


def _extract_link_args(text: str) -> dict[str, Any]:
    args: dict[str, Any] = {}
    lower = text.lower()
    if "provision" in lower and "link" in lower:
        tail = text.lower().split("link", 1)[1].strip()
        parts = tail.split()
        if len(parts) >= 2:
            args["site_a"] = parts[0].capitalize()
            args["site_b"] = parts[1].capitalize()
        if len(parts) >= 3 and parts[2].isdigit():
            args["bandwidth_mbps"] = int(parts[2])
    return args
