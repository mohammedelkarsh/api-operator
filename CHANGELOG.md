# Changelog

All notable changes to this project are documented in this file.

## [1.1.0] - 2026-11-23

### Added

- **L1 embedding knowledge** (`knowledge_backend=embedding`) with OpenAI or offline hashing embedder
- **L2 pgvector retrieval** (`knowledge_backend=pgvector` + `knowledge_pg_dsn`)
- Optional extra: `pip install "api-operator[rag]"`
- Docs: expanded `docs/knowledge.md`

## [1.0.0] - 2026-11-23

**Safe API Agent** production label. Builds on 0.11 foundation; additive and backward compatible for existing adapters.

### Added

- Opt-in **keyword knowledge (L0)**: `API_OPERATOR_KNOWLEDGE_ENABLED` + `KNOWLEDGE_PATHS`
- Tenant-scoped doc isolation under `/tenants/{id}/`
- `docs/knowledge.md` (L1+ `rag` extra deferred to 1.1.0)

### Changed

- Package version **1.0.0**; README / FastAPI metadata aligned

## [0.11.0] - 2026-11-23

Foundation for **Safe API Agent** (see `docs/ROADMAP-vNEXT.md`). Opt-in; existing adapters keep working.

### Added

- **Policy engine** (`policy.yaml`): allow / deny / confirm, deny lists, confirm lists, session `max_calls`, role/tenant rules
- **Dry-run**: CLI `--dry-run`, HTTP `dry_run=true`, `DryRunReport` + YAML `would_call` preview
- **Audit**: `AuditSink` protocol, JSONL / memory sinks, sensitive-field redaction
- **Quota hooks**: `QuotaGateway` + in-memory budget gateway (host owns real billing)
- Shared schemas: `PolicyDecision`, `QuotaReservation`, `AuditEvent`, `DryRunReport`
- Docs: `docs/policy.md`, `docs/dry-run.md`, `docs/audit.md`, `docs/quotas.md`, `docs/public-api-inventory.md`
- Example `examples/tenant-kit-adapter/policy.yaml`
- Example `examples/jsonplaceholder-adapter/` (public REST, non–tenant-kit)
- OpenAPI generator: tag-based `requires_ability`, write methods marked dangerous, draft `policy.yaml`
- `scaffold-adapter` also writes `policy.yaml`

### Changed

- Agent `status` may be `deny` (additive) for policy/quota/ability rejection
- README reframed as **Safe API Agent**; version `0.11.0`

## [0.10.0] - 2026-06-15

### Added

- YAML adapter `connect_host` — route HTTP to an internal host (e.g. Docker `nginx`) while preserving logical `Host` headers for multi-tenant subdomains
- Optional CORS for `api-operator serve` via `API_OPERATOR_CORS_ORIGINS` (comma-separated)
- `Dockerfile` for containerized deployments
- `formatters.py` — human-readable tool success messages (no raw JSON in chat replies)
- Mock adapter tools: `get_usage`, `get_subscription`

### Changed

- Mock planner — friendlier help text and NL patterns for tenant-kit flows
- FastAPI app version metadata updated to 0.10.0

## [0.9.0] - 2026-06-14

Renamed to **`api-operator`** (GitHub + PyPI). PyPI blocks names starting with `operator` (stdlib conflict).

### Added

- Core agent runtime: planning, guardrails, tool execution, session memory
- `mock` adapter for offline demos and tests
- `yaml` adapter — configure HTTP tools without Python
- OpenAPI scaffold CLI (`generate-from-openapi`, `scaffold-adapter`)
- CLI: `chat`, `demo`, `tools`, `serve`
- FastAPI server: `/health`, `/v1/adapters`, `/v1/tools`, `/v1/chat`
- Example adapter for [Laravel Tenant Kit](https://github.com/mohammedelkarsh/laravel-tenant-kit)
- Live integration script: `scripts/integration_tenant_kit.py`
- 69 unit tests; optional pytest integration marker

### Notes

- Default planner is rule-based (`mock`); OpenAI planner is optional (`pip install api-operator[llm]`)
- Tenant team invites require a tenant-scoped Sanctum token (see example adapter README)
