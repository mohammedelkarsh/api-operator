from __future__ import annotations

from typing import Any, get_args, get_origin


_TYPE_MAP: dict[type, str] = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
}


def _json_type(python_type: type | str) -> str:
    if isinstance(python_type, str):
        return python_type
    origin = get_origin(python_type)
    if origin is list:
        return "array"
    return _TYPE_MAP.get(python_type, "string")


def tool_parameters_schema(
    parameters: dict[str, type | str],
    required: list[str],
) -> dict[str, Any]:
    properties: dict[str, Any] = {}
    for name, param_type in parameters.items():
        properties[name] = {"type": _json_type(param_type)}
    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }
