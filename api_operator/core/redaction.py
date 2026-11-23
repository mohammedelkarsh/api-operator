"""Redact common secret field names from audit / dry-run payloads."""

from __future__ import annotations

from typing import Any

SENSITIVE_KEYS = frozenset(
    {
        "password",
        "passwd",
        "secret",
        "token",
        "access_token",
        "refresh_token",
        "api_key",
        "apikey",
        "authorization",
        "auth",
        "client_secret",
        "private_key",
    }
)

REDACTED = "***REDACTED***"


def redact(value: Any, *, extra_keys: set[str] | None = None) -> Any:
    """Recursively redact sensitive keys in dict/list structures."""
    keys = SENSITIVE_KEYS | {k.lower() for k in (extra_keys or set())}
    return _redact(value, keys)


def _redact(value: Any, keys: frozenset[str] | set[str]) -> Any:
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            if str(key).lower() in keys:
                out[key] = REDACTED
            else:
                out[key] = _redact(item, keys)
        return out
    if isinstance(value, list):
        return [_redact(item, keys) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact(item, keys) for item in value)
    return value
