# Changelog

All notable changes to this project are documented in this file.

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
