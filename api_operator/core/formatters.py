from __future__ import annotations

from typing import Any


def format_tool_success(tool_name: str, data: Any) -> str:
    if not isinstance(data, dict):
        return f"{tool_name.replace('_', ' ')} completed successfully."

    formatters = {
        "list_workspaces": _format_list_workspaces,
        "create_workspace": _format_create_workspace,
        "get_usage": _format_get_usage,
        "get_subscription": _format_get_subscription,
        "invite_member": _format_invite,
        "invite_team_member": _format_invite,
        "list_connections": _format_list_connections,
        "provision_link": _format_provision_link,
    }
    formatter = formatters.get(tool_name)
    if formatter is not None:
        return formatter(data)

    return _format_generic(tool_name, data)


def _workspace_items(data: dict[str, Any]) -> list[dict[str, Any]]:
    payload = data.get("data", data)
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        nested = payload.get("workspaces")
        if isinstance(nested, list):
            return [item for item in nested if isinstance(item, dict)]
        if any(key in payload for key in ("id", "name", "subdomain")):
            return [payload]
    nested = data.get("workspaces")
    if isinstance(nested, list):
        return [item for item in nested if isinstance(item, dict)]
    return []


def _format_list_workspaces(data: dict[str, Any]) -> str:
    items = _workspace_items(data)
    if not items:
        return "No workspaces found."

    lines = [f"Found {len(items)} workspace(s):", ""]
    for workspace in items:
        name = workspace.get("name") or workspace.get("id") or "Unknown"
        identifier = workspace.get("id") or workspace.get("subdomain") or "?"
        line = f"• {name} ({identifier})"
        url = workspace.get("url")
        if url:
            line += f"\n  {url}"
        status_bits: list[str] = []
        if workspace.get("suspended"):
            status_bits.append("suspended")
        if workspace.get("subscribed"):
            status_bits.append("subscribed")
        if status_bits:
            line += f"\n  Status: {', '.join(status_bits)}"
        lines.append(line)

    return "\n".join(lines)


def _format_create_workspace(data: dict[str, Any]) -> str:
    workspace = data.get("data", data)
    if not isinstance(workspace, dict):
        return "Workspace created successfully."

    name = workspace.get("name") or workspace.get("id") or "Workspace"
    identifier = workspace.get("id") or workspace.get("subdomain") or "?"
    lines = [f"Workspace created: {name} ({identifier})"]
    url = workspace.get("url")
    if url:
        lines.append(url)
    return "\n".join(lines)


def _format_get_usage(data: dict[str, Any]) -> str:
    payload = data.get("data", data)
    if not isinstance(payload, dict):
        return "Usage retrieved."

    workspace_id = payload.get("workspace_id", "workspace")
    lines = [f"Usage for {workspace_id}:"]
    for key, value in payload.items():
        if key == "workspace_id":
            continue
        label = key.replace("_", " ").strip()
        lines.append(f"• {label}: {value}")
    return "\n".join(lines)


def _format_get_subscription(data: dict[str, Any]) -> str:
    payload = data.get("data", data)
    if not isinstance(payload, dict):
        return "Subscription retrieved."

    workspace_id = payload.get("workspace_id", "workspace")
    plan = payload.get("plan", "unknown")
    status = payload.get("status", "unknown")
    return f"Subscription for {workspace_id}: {plan} ({status})"


def _format_invite(data: dict[str, Any]) -> str:
    payload = data.get("data", data)
    if not isinstance(payload, dict):
        return "Invitation sent."

    email = payload.get("email", "member")
    workspace = payload.get("workspace") or payload.get("subdomain") or "workspace"
    role = payload.get("role")
    line = f"Invitation sent to {email} for {workspace}"
    if role:
        line += f" as {role}"
    return f"{line}."


def _format_list_connections(data: dict[str, Any]) -> str:
    payload = data.get("data", data)
    items: list[Any]
    if isinstance(payload, dict):
        nested = payload.get("connections")
        items = nested if isinstance(nested, list) else []
    elif isinstance(payload, list):
        items = payload
    else:
        items = []

    if not items:
        return "No connections found."

    lines = [f"Found {len(items)} connection(s):", ""]
    for item in items:
        if not isinstance(item, dict):
            continue
        site_a = item.get("site_a", "?")
        site_b = item.get("site_b", "?")
        bandwidth = item.get("bandwidth_mbps")
        line = f"• {site_a} ↔ {site_b}"
        if bandwidth is not None:
            line += f" ({bandwidth} Mbps)"
        lines.append(line)

    return "\n".join(lines)


def _format_provision_link(data: dict[str, Any]) -> str:
    payload = data.get("data", data)
    if not isinstance(payload, dict):
        return "Link provisioned successfully."

    site_a = payload.get("site_a", "?")
    site_b = payload.get("site_b", "?")
    bandwidth = payload.get("bandwidth_mbps")
    line = f"Link provisioned: {site_a} ↔ {site_b}"
    if bandwidth is not None:
        line += f" at {bandwidth} Mbps"
    return line


def _format_generic(tool_name: str, data: dict[str, Any]) -> str:
    label = tool_name.replace("_", " ")
    if data.get("message") and len(data) == 1:
        return str(data["message"])
    return f"{label} completed successfully."
