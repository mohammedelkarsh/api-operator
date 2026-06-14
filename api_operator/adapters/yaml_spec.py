from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class ParameterSpec:
    type: str = "string"
    required: bool = False
    default: Any = None


@dataclass
class ToolSpec:
    name: str
    description: str
    method: str
    path: str
    parameters: dict[str, ParameterSpec] = field(default_factory=dict)
    body: dict[str, Any] | None = None
    query: dict[str, str] | None = None
    dangerous: bool = False
    requires_ability: str | None = None
    host: str = "central"  # central | tenant
    tenant_param: str = "subdomain"


@dataclass
class AdapterSpec:
    name: str
    description: str
    base_url: str
    system_prompt: str
    tools: list[ToolSpec]
    auth_type: str = "bearer"
    auth_header: str = "Authorization"
    token_env: str | None = None


def load_adapter_spec(path: str | Path) -> AdapterSpec:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Adapter config not found: {file_path}")

    raw = yaml.safe_load(file_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Adapter YAML must be a mapping")

    auth = raw.get("auth") or {}
    tools: list[ToolSpec] = []
    for item in raw.get("tools") or []:
        if not isinstance(item, dict):
            continue
        params: dict[str, ParameterSpec] = {}
        raw_params = item.get("parameters") or {}
        if isinstance(raw_params, dict):
            for pname, pspec in raw_params.items():
                if isinstance(pspec, dict):
                    params[pname] = ParameterSpec(
                        type=str(pspec.get("type", "string")),
                        required=bool(pspec.get("required", False)),
                        default=pspec.get("default"),
                    )
                else:
                    params[pname] = ParameterSpec(required=bool(pspec))

        tools.append(
            ToolSpec(
                name=str(item["name"]),
                description=str(item.get("description", item["name"])),
                method=str(item.get("method", "GET")).upper(),
                path=str(item["path"]),
                parameters=params,
                body=item.get("body"),
                query=item.get("query"),
                dangerous=bool(item.get("dangerous", False)),
                requires_ability=item.get("requires_ability"),
                host=str(item.get("host", "central")),
                tenant_param=str(item.get("tenant_param", "subdomain")),
            )
        )

    return AdapterSpec(
        name=str(raw.get("name", file_path.stem)),
        description=str(raw.get("description", "")),
        base_url=str(raw.get("base_url", "")).rstrip("/"),
        system_prompt=str(raw.get("system_prompt") or _default_prompt(raw)),
        tools=tools,
        auth_type=str(auth.get("type", "bearer")),
        auth_header=str(auth.get("header", "Authorization")),
        token_env=auth.get("env_token"),
    )


def save_adapter_spec(spec: AdapterSpec, path: str | Path) -> None:
    file_path = Path(path)
    payload: dict[str, Any] = {
        "name": spec.name,
        "description": spec.description,
        "base_url": spec.base_url,
        "auth": {"type": spec.auth_type, "header": spec.auth_header},
        "system_prompt": spec.system_prompt,
        "tools": [],
    }
    if spec.token_env:
        payload["auth"]["env_token"] = spec.token_env

    for tool in spec.tools:
        entry: dict[str, Any] = {
            "name": tool.name,
            "description": tool.description,
            "method": tool.method,
            "path": tool.path,
        }
        if tool.host != "central":
            entry["host"] = tool.host
            entry["tenant_param"] = tool.tenant_param
        if tool.dangerous:
            entry["dangerous"] = True
        if tool.requires_ability:
            entry["requires_ability"] = tool.requires_ability
        if tool.parameters:
            entry["parameters"] = {
                name: {
                    "type": param.type,
                    "required": param.required,
                    **({"default": param.default} if param.default is not None else {}),
                }
                for name, param in tool.parameters.items()
            }
        if tool.body:
            entry["body"] = tool.body
        if tool.query:
            entry["query"] = tool.query
        payload["tools"].append(entry)

    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def _default_prompt(raw: dict[str, Any]) -> str:
    name = raw.get("name", "project")
    return (
        f"You are API Operator for {name}. "
        "Use registered tools only. Confirm dangerous actions. "
        "Reply in the user's language."
    )
