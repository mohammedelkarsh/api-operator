from __future__ import annotations

import os
import re
from typing import Any
from urllib.parse import urlparse, urlunparse

import httpx

from api_operator.adapters.base import Adapter
from api_operator.adapters.yaml_spec import AdapterSpec, ToolSpec, load_adapter_spec
from api_operator.tools.base import Tool, ToolRegistry, ToolResult

_PLACEHOLDER = re.compile(r"\{(\w+)\}")


class YamlAdapter(Adapter):
    """
    HTTP adapter driven by a YAML config file — no Python required per project.

    See examples/tenant-kit-adapter/adapter.yaml and `scaffold-adapter` CLI.
    """

    name = "yaml"
    description = "YAML-configured HTTP adapter"

    def __init__(
        self,
        config_path: str,
        token: str | None = None,
        base_url: str | None = None,
        connect_host: str | None = None,
    ) -> None:
        self.spec = load_adapter_spec(config_path)
        self.name = self.spec.name
        self.description = self.spec.description
        self.token = token or _token_from_env(self.spec.token_env)
        if base_url:
            self.spec.base_url = base_url.rstrip("/")
        self.connect_host = connect_host or self.spec.connect_host

    def auth_context(self) -> dict[str, Any]:
        return {"token": "***" if self.token else None, "base_url": self.spec.base_url}

    def build_registry(self) -> ToolRegistry:
        registry = ToolRegistry()
        for tool_spec in self.spec.tools:
            registry.register(self._build_tool(tool_spec))
        return registry

    def system_prompt(self) -> str:
        return self.spec.system_prompt

    def _build_tool(self, spec: ToolSpec) -> Tool:
        param_types: dict[str, type | str] = {}
        required: list[str] = []
        for name, param in spec.parameters.items():
            param_types[name] = param.type
            if param.required:
                required.append(name)

        async def handler(**kwargs: Any) -> ToolResult:
            return await self._execute(spec, kwargs)

        return Tool(
            name=spec.name,
            description=spec.description,
            handler=handler,
            parameters=param_types,
            required=required,
            dangerous=spec.dangerous,
            requires_ability=spec.requires_ability,
        )

    async def _execute(self, spec: ToolSpec, args: dict[str, Any]) -> ToolResult:
        if self.spec.auth_type == "bearer" and not self.token:
            return ToolResult(ok=False, error="Missing API token for YAML adapter.")

        for name, param in spec.parameters.items():
            if args.get(name) is None and param.default is not None:
                args[name] = param.default

        url = self._build_url(spec, args)
        json_body = self._build_body(spec.body, args) if spec.body else None
        params = self._build_query(spec.query, args) if spec.query else None

        headers = {"Accept": "application/json"}
        if json_body is not None:
            headers["Content-Type"] = "application/json"
        if self.token and self.spec.auth_type == "bearer":
            headers[self.spec.auth_header] = f"Bearer {self.token}"

        request_url, headers = _apply_connect_host(url, self.connect_host, headers)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.request(
                    spec.method,
                    request_url,
                    headers=headers,
                    json=json_body,
                    params=params,
                )
        except httpx.HTTPError as exc:
            return ToolResult(ok=False, error=f"HTTP error: {exc}")

        try:
            body = response.json()
        except ValueError:
            body = {"raw": response.text}

        if response.is_success:
            return ToolResult(ok=True, data=body if isinstance(body, dict) else {"data": body})

        error = body.get("message") if isinstance(body, dict) else response.text
        return ToolResult(
            ok=False,
            error=f"API {response.status_code}: {error}",
            data=body if isinstance(body, dict) else {},
        )

    def _build_url(self, spec: ToolSpec, args: dict[str, Any]) -> str:
        path = spec.path
        for match in _PLACEHOLDER.finditer(path):
            key = match.group(1)
            if key not in args:
                raise ValueError(f"Missing path parameter: {key}")
            path = path.replace(f"{{{key}}}", str(args[key]))

        base = self._resolve_base(spec, args)
        return f"{base}{path}"

    def _resolve_base(self, spec: ToolSpec, args: dict[str, Any]) -> str:
        if spec.host != "tenant":
            return self.spec.base_url

        subdomain_key = spec.tenant_param
        subdomain = args.get(subdomain_key)
        if not subdomain:
            raise ValueError(f"Missing tenant parameter: {subdomain_key}")

        return _tenant_base_url(self.spec.base_url, str(subdomain))

    def _build_body(self, template: dict[str, Any], args: dict[str, Any]) -> dict[str, Any]:
        return _render_mapping(template, args)

    def _build_query(self, template: dict[str, str], args: dict[str, Any]) -> dict[str, str]:
        return {key: str(_render_value(value, args)) for key, value in template.items()}


def _tenant_base_url(base_url: str, subdomain: str) -> str:
    if "://" not in base_url:
        raise ValueError("base_url must include scheme")
    scheme, rest = base_url.split("://", 1)
    host = rest.split("/", 1)[0]
    return f"{scheme}://{subdomain}.{host}"


def _render_mapping(template: dict[str, Any], args: dict[str, Any]) -> dict[str, Any]:
    return {key: _render_value(value, args) for key, value in template.items()}


def _render_value(value: Any, args: dict[str, Any]) -> Any:
    if isinstance(value, str):
        rendered = value
        for match in _PLACEHOLDER.finditer(value):
            key = match.group(1)
            if key not in args:
                raise ValueError(f"Missing body parameter: {key}")
            rendered = rendered.replace(f"{{{key}}}", str(args[key]))
        return rendered
    if isinstance(value, dict):
        return _render_mapping(value, args)
    return value


def _token_from_env(env_name: str | None) -> str | None:
    if not env_name:
        return None
    return os.environ.get(env_name)


def _apply_connect_host(
    url: str,
    connect_host: str | None,
    headers: dict[str, str],
) -> tuple[str, dict[str, str]]:
    if not connect_host:
        return url, headers

    parsed = urlparse(url)
    if not parsed.hostname:
        return url, headers

    host_header = parsed.hostname
    if parsed.port:
        host_header = f"{host_header}:{parsed.port}"

    headers = dict(headers)
    headers["Host"] = host_header
    request_url = urlunparse(
        (
            parsed.scheme,
            connect_host,
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment,
        )
    )
    return request_url, headers
