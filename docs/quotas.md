# Quota hooks

The core never talks to Stripe. It exposes `QuotaGateway` so hosts can meter usage.

## Protocol

```python
class QuotaGateway(Protocol):
    def check(self, context, estimated_cost) -> QuotaReservation: ...
    def commit(self, context, actual_cost, reservation_id) -> None: ...
    def rollback(self, context, reservation_id) -> None: ...
```

- Default: `UnlimitedQuotaGateway` (never blocks)
- Local demos: set `API_OPERATOR_QUOTA_BUDGET=100` → `InMemoryQuotaGateway`
- Over-quota returns `status=deny` **before** tool execution

## Laravel / tenant-kit wiring (later)

1. On each `/v1/chat` tool allow path, call your PHP meter (or have the Python sidecar call a signed callback).
2. Map workspace plan limits → `QuotaGateway.check`.
3. On success, increment `agent_calls` via `commit`.
4. On tool failure, `rollback` so held budget is released.

Keep billing truth in the host; api-operator only enforces the gate.
