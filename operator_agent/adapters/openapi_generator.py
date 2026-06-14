from __future__ import annotations

import re
import json
from pathlib import Path
from typing import Any

import yaml

from operator_agent.adapters.yaml_spec import AdapterSpec, ParameterSpec, ToolSpec, save_adapter_spec

_METHODS = {"get", "post", "put", "patch", "delete"}


def generate_adapter_from_openapi(
    spec_path: str | Path,
    *,
    base_url: str,
    name: str | None = None,
    description: str | None = None,
    path_prefix: str | None = None,
    include_methods: set[str] | None = None,
    tag_filter: set[str] | None = None,
    dangerous_paths: set[str] | None = None,
) -> AdapterSpec:
    path = Path(spec_path)
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        raw = json.loads(text)
    else:
        raw = yaml.safe_load(text)
    if not isinstance(raw, dict):
        raise ValueError("OpenAPI spec must be a YAML/JSON object")

    info = raw.get("info") or {}
    adapter_name = name or str(info.get("title", path.stem)).lower().replace(" ", "_")
    adapter_description = description or str(info.get("description", f"{adapter_name} API adapter"))
    methods = {m.upper() for m in (include_methods or {"GET", "POST"})}
    dangerous_paths = dangerous_paths or set()

    tools: list[ToolSpec] = []
    paths = raw.get("paths") or {}
    for route, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        if path_prefix and not route.startswith(path_prefix):
            continue

        for method, operation in path_item.items():
            if method.lower() not in _METHODS or not isinstance(operation, dict):
                continue
            if method.upper() not in methods:
                continue

            tags = operation.get("tags") or []
            if tag_filter and not (set(tags) & tag_filter):
                continue

            tool = _operation_to_tool(route, method.upper(), operation, dangerous_paths)
            if tool:
                tools.append(tool)

    if not tools:
        raise ValueError("No tools generated — check path_prefix, methods, or tag_filter.")

    return AdapterSpec(
        name=adapter_name,
        description=adapter_description,
        base_url=base_url.rstrip("/"),
        system_prompt=(
            f"You are Operator Agent for {adapter_name}. "
            "Use tools to call the project API. Confirm dangerous actions. "
            "Reply in the user's language."
        ),
        tools=tools,
        token_env=f"{adapter_name.upper()}_API_TOKEN",
    )


def _operation_to_tool(
    route: str,
    method: str,
    operation: dict[str, Any],
    dangerous_paths: set[str],
) -> ToolSpec | None:
    operation_id = operation.get("operationId")
    summary = operation.get("summary") or operation.get("description") or f"{method} {route}"
    name = _tool_name(operation_id, method, route)
    parameters: dict[str, ParameterSpec] = {}
    path = route

    for param in operation.get("parameters") or []:
        if not isinstance(param, dict):
            continue
        pname = param.get("name")
        if not pname:
            continue
        location = param.get("in")
        required = bool(param.get("required", False))
        schema = param.get("schema") or {}
        ptype = str(schema.get("type", "string"))
        parameters[str(pname)] = ParameterSpec(type=ptype, required=required)
        if location == "path":
            path = path.replace(f"{{{pname}}}", f"{{{pname}}}")

    body_template: dict[str, Any] | None = None
    request_body = operation.get("requestBody") or {}
    content = request_body.get("content") or {}
    json_content = content.get("application/json") or {}
    schema = json_content.get("schema") or {}
    props = schema.get("properties") or {}
    required_fields = set(schema.get("required") or [])
    if props:
        body_template = {}
        for pname, pschema in props.items():
            if not isinstance(pschema, dict):
                continue
            parameters.setdefault(
                str(pname),
                ParameterSpec(
                    type=str(pschema.get("type", "string")),
                    required=str(pname) in required_fields,
                ),
            )
            body_template[str(pname)] = f"{{{pname}}}"

    dangerous = method in {"POST", "PUT", "PATCH", "DELETE"} or route in dangerous_paths

    return ToolSpec(
        name=name,
        description=str(summary).strip(),
        method=method,
        path=path,
        parameters=parameters,
        body=body_template,
        dangerous=dangerous,
    )


def _tool_name(operation_id: str | None, method: str, route: str) -> str:
    if operation_id:
        return _slugify(operation_id)
    slug = _slugify(route.replace("{", "").replace("}", "").replace("/", "_"))
    return _slugify(f"{method.lower()}_{slug}")


def _slugify(value: str) -> str:
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9_]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value[:64] or "tool"


SCAFFOLD_TEMPLATE = """name: {name}
description: {description}
base_url: {base_url}

auth:
  type: bearer
  header: Authorization
  env_token: {token_env}

system_prompt: |
  You are Operator Agent for {name}.
  Use registered tools only. Confirm dangerous actions.
  Reply in the user's language (Arabic or English).

tools:
  - name: list_items
    description: List items from the project API
    method: GET
    path: /api/items
    requires_ability: items:read

  - name: create_item
    description: Create a new item
    method: POST
    path: /api/items
    dangerous: true
    requires_ability: items:write
    parameters:
      title:
        type: string
        required: true
    body:
      title: "{{title}}"
"""


def scaffold_adapter(
    name: str,
    output_dir: str | Path,
    *,
    base_url: str = "http://localhost:8000",
    description: str | None = None,
) -> Path:
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    config_path = directory / "adapter.yaml"
    token_env = f"{name.upper()}_API_TOKEN"
    config_path.write_text(
        SCAFFOLD_TEMPLATE.format(
            name=name,
            description=description or f"{name} API adapter",
            base_url=base_url.rstrip("/"),
            token_env=token_env,
        ),
        encoding="utf-8",
    )

    readme = directory / "README.md"
    readme.write_text(
        f"""# {name} adapter (YAML)

No Python required — edit `adapter.yaml` and run:

```powershell
python -m operator_agent.server.cli chat --adapter yaml --config adapter.yaml
```

Set token:

```powershell
$env:{token_env} = "your-api-token"
```

Or pass `--token` on the CLI.

Generate from OpenAPI:

```powershell
python -m operator_agent.server.cli generate-from-openapi openapi.yaml --output adapter.yaml --base-url {base_url}
```
""",
        encoding="utf-8",
    )
    return config_path
