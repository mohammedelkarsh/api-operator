# Operator Agent

[![Tests](https://github.com/mohammedelkarsh/operator-agent/actions/workflows/tests.yml/badge.svg)](https://github.com/mohammedelkarsh/operator-agent/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)

Standalone **AI operator runtime** with pluggable adapters. Talk to your HTTP APIs instead of clicking through admin panels.

Works with Laravel, Go, connectivity platforms, or any backend with a REST API.

## Install

```bash
git clone https://github.com/mohammedelkarsh/operator-agent.git
cd operator-agent
pip install -e ".[dev]"
```

Optional OpenAI planner:

```bash
pip install -e ".[dev,llm]"
```

## Quick start

```bash
operator-agent demo
operator-agent tools --adapter mock
```

## What ships in the core package

| In core | In your projects |
|---------|------------------|
| Agent runtime (plan, guard, execute) | `adapter.yaml` per API |
| `mock` adapter (demo + tests) | OpenAPI specs |
| `yaml` adapter | API tokens in `.env` |
| CLI + HTTP server | Optional custom adapters |

## Build an adapter without Python

### Scaffold template

```bash
operator-agent scaffold-adapter my-api --output examples
```

### Generate from OpenAPI

```bash
operator-agent generate-from-openapi openapi.yaml \
  --output adapter.yaml \
  --base-url http://api.example.test \
  --path-prefix /api
```

### Laravel Tenant Kit example

See [`examples/tenant-kit-adapter/`](examples/tenant-kit-adapter/) — pairs with [laravel-tenant-kit](https://github.com/mohammedelkarsh/laravel-tenant-kit).

```bash
export TENANT_KIT_API_TOKEN="your-sanctum-token"
operator-agent chat \
  --adapter yaml \
  --config examples/tenant-kit-adapter/adapter.yaml \
  --base-url http://laravel-tenant-kit.test
```

## adapter.yaml (minimal)

```yaml
name: my_project
description: My API adapter
base_url: http://api.example.test

auth:
  type: bearer
  env_token: MY_PROJECT_API_TOKEN

tools:
  - name: list_items
    description: List items
    method: GET
    path: /api/items

  - name: create_item
    description: Create item
    method: POST
    path: /api/items
    dangerous: true
    parameters:
      title:
        type: string
        required: true
    body:
      title: "{title}"
```

Tenant subdomain APIs:

```yaml
  - name: invite_member
    method: POST
    path: /api/team/invitations
    host: tenant
    tenant_param: subdomain
    parameters:
      subdomain: { type: string, required: true }
      email: { type: string, required: true }
```

## HTTP server

```bash
operator-agent serve --port 8100
```

```json
POST /v1/chat
{
  "adapter": "yaml",
  "config_path": "examples/tenant-kit-adapter/adapter.yaml",
  "adapter_config": { "token": "YOUR_TOKEN" },
  "message": "list workspaces",
  "abilities": ["workspaces:read"]
}
```

## Integration test (Tenant Kit)

With [Tenant Kit](https://github.com/mohammedelkarsh/laravel-tenant-kit) running:

```bash
python scripts/integration_tenant_kit.py
# Docker on port 8080:
python scripts/integration_tenant_kit.py --base-url http://laravel-tenant-kit.test:8080
```

Optional pytest marker (requires env vars):

```bash
export TENANT_KIT_BASE_URL=http://laravel-tenant-kit.test
export TENANT_KIT_API_TOKEN=your-token
pytest -m integration -q
```

## Tests

```bash
pytest -q
```

## Configuration

Copy `.env.example` to `.env` for local defaults (`operator_agent_PLANNER`, port, etc.).

## Architecture

```
operator-agent (core)          your projects
├── agent runtime               ├── adapter.yaml
├── mock + yaml adapters        ├── openapi.yaml
└── scaffold / generate CLI     └── HTTP APIs (Laravel, Go, …)
```

## License

MIT — see [LICENSE](LICENSE).
