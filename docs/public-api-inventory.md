# Public API inventory (baseline for 1.0)

Snapshot of surfaces hosts/adapters depend on today. New Safe API Agent features
must stay **opt-in** and must not break these contracts without a major bump.

## Package exports (`api_operator`)

| Symbol | Notes |
|--------|--------|
| `Agent` | Primary runtime |
| `AgentResponse` | `status`: historically `ok \| confirm \| error`; **1.0 adds `deny`** |
| `Settings` | `API_OPERATOR_*` env |
| `Tool`, `ToolRegistry` | Tool registration |

Added in 0.11 / 1.0 (non-breaking exports):

- `PolicyEngine`, `PolicyContext`, `PolicyDecision`, `Decision`
- `AuditEvent`, `QuotaReservation`, `DryRunReport`

## Factory

```python
build_agent(adapter_name="mock", settings=None, adapter_class=None,
            config_path=None, sessions=None, policy=None, policy_path=None, **kwargs)
```

- If `policy_path` / `settings.policy_path` unset and `config_path` has sibling `policy.yaml`, it loads automatically.

## HTTP

| Endpoint | Contract |
|----------|----------|
| `GET /health` | `{status, adapter_default}` |
| `GET /v1/adapters` | builtin + yaml/external hints |
| `GET /v1/tools` | tool schemas |
| `POST /v1/chat` | `ChatRequest` → `ChatResponse` |

`ChatRequest` fields used by tenant-kit today: `message`, `session_id`, `adapter`,
`config_path`, `abilities`, `auto_confirm`, `adapter_config`.

Planned additive (opt-in): `dry_run`, `tenant_id`, `actor_id`, `role`, `policy_path`.

## CLI

`chat`, `serve`, `tools`, `scaffold-adapter`, `generate-from-openapi`, `demo`.

## Adapter YAML

`examples/tenant-kit-adapter/adapter.yaml` — mirrored from laravel-tenant-kit.
Tools: list/create/get workspace, subscription, usage, invite_team_member.

## Compatibility rules for 1.0

1. Existing chats without `policy.yaml` behave like 0.10 (ability + dangerous confirm).
2. New status value `deny` is additive; clients that only check `error` should also treat `deny`.
3. No hard dependency on Laravel, Postgres, or embeddings.
