"""Audit trail for Safe API Agent actions."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from api_operator.core.redaction import redact
from api_operator.core.schemas import AuditEvent


@runtime_checkable
class AuditSink(Protocol):
    def emit(self, event: AuditEvent) -> None: ...


class NullAuditSink:
    def emit(self, event: AuditEvent) -> None:
        return None


class JsonlAuditSink:
    """Append AuditEvent records as JSON lines to a file or stdout."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else None

    def emit(self, event: AuditEvent) -> None:
        line = event.model_dump_json() + "\n"
        if self.path is None:
            sys.stdout.write(line)
            sys.stdout.flush()
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(line)


class MemoryAuditSink:
    """In-memory sink for tests."""

    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    def emit(self, event: AuditEvent) -> None:
        self.events.append(event)


def build_audit_event(
    *,
    session_id: str | None = None,
    adapter: str | None = None,
    tool: str | None = None,
    arguments: dict[str, Any] | None = None,
    decision: Any = None,
    result_status: str | None = None,
    duration_ms: float | None = None,
    tenant_id: str | None = None,
    actor_id: str | None = None,
    dry_run: bool = False,
    error: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditEvent:
    return AuditEvent(
        session_id=session_id,
        adapter=adapter,
        tool=tool,
        arguments=redact(arguments or {}),
        decision=decision,
        result_status=result_status,
        duration_ms=duration_ms,
        tenant_id=tenant_id,
        actor_id=actor_id,
        dry_run=dry_run,
        error=error,
        metadata=redact(metadata or {}),
    )


def parse_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows
