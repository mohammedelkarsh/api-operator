# Audit log

Every tool decision (allow / deny / confirm / dry-run) can emit an `AuditEvent`.

## Default behavior

- `API_OPERATOR_AUDIT_ENABLED=true` (default)
- Without `API_OPERATOR_AUDIT_PATH`, events are discarded (`NullAuditSink`) unless a host injects a sink
- With `API_OPERATOR_AUDIT_PATH=/var/log/api-operator.jsonl`, events append as JSON Lines

## Inject a custom sink

```python
from api_operator.core.audit import MemoryAuditSink
from api_operator.factory import build_agent

sink = MemoryAuditSink()
agent = build_agent("mock", audit=sink)
```

Hosts (e.g. laravel-tenant-kit) can implement `AuditSink.emit` to POST to a webhook or write into `agent_calls`.

## Redaction

Arguments and metadata pass through `redact()` which masks keys such as
`password`, `token`, `secret`, `authorization`, `api_key`.
