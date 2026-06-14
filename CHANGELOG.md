# Changelog

All notable changes to this project are documented in this file.

## [0.9.0] - 2026-06-14

Renamed from `workspace-agent` to **`operator-agent`** (GitHub + PyPI package name).

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

- Default planner is rule-based (`mock`); OpenAI planner is optional (`pip install operator-agent[llm]`)
- Tenant team invites require a tenant-scoped Sanctum token (see example adapter README)
