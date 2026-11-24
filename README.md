# API Operator — Safe API Agent

[![Tests](https://github.com/mohammedelkarsh/api-operator/actions/workflows/tests.yml/badge.svg)](https://github.com/mohammedelkarsh/api-operator/actions/workflows/tests.yml)
[![PyPI](https://img.shields.io/pypi/v/api-operator.svg)](https://pypi.org/project/api-operator/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)

Turn any OpenAPI / `adapter.yaml` into an AI agent that can **reason and act on your APIs** with **policy, dry-run, audit, and quota hooks**.

> Retrieve (optional later) → Reason → Act — with permission, cost, and audit boundaries.

Works with Laravel, Go, or any REST API. First-class example: [laravel-tenant-kit](https://github.com/mohammedelkarsh/laravel-tenant-kit).

## Install

```bash
pip install api-operator==1.1.1
# optional OpenAI planner / RAG (embeddings + pgvector)
pip install "api-operator[llm]==1.1.1"
pip install "api-operator[rag]==1.1.1"
```

Development:

```bash
git clone https://github.com/mohammedelkarsh/api-operator.git
cd api-operator
pip install -e ".[dev]"
```

## Quick start

```bash
api-operator demo
api-operator tools --adapter mock
api-operator chat --adapter mock --dry-run
```

**Windows note:** if `api-operator` is not recognized after `pip install` (user Scripts not on PATH), use the module form:

```powershell
python -m api_operator.server.cli demo
python -m api_operator.server.cli serve --host 127.0.0.1 --port 8100
```

Public API demo (no Laravel):

```bash
api-operator chat \
  --adapter yaml \
  --config examples/jsonplaceholder-adapter/adapter.yaml \
  --dry-run
```

## What ships in the core

| In core | In your projects |
|---------|------------------|
| Agent runtime (plan → policy → quota → execute) | `adapter.yaml` + optional `policy.yaml` |
| Dry-run (`--dry-run` / `dry_run=true`) | OpenAPI specs |
| AuditSink + redaction | API tokens in `.env` |
| QuotaGateway hooks | Host billing (e.g. tenant-kit meters) |
| Optional knowledge L0/L1/L2 | Docs, embeddings, or pgvector |
| `mock` + `yaml` adapters | Optional custom adapters |

No hard dependency on Laravel, Postgres, or vector DBs. Knowledge is **off** until you enable it ([docs/knowledge.md](docs/knowledge.md)).

## Safe by default

1. **Policy** — optional `policy.yaml` (allow / deny / confirm, session caps, roles)
2. **Dry-run** — see the planned tool + upstream request without side effects
3. **Audit** — JSONL / injectable sink; secrets redacted
4. **Quota** — gate before execute; real billing stays in the host app

Docs: [policy](docs/policy.md) · [dry-run](docs/dry-run.md) · [audit](docs/audit.md) · [quotas](docs/quotas.md) · [roadmap](docs/ROADMAP-vNEXT.md)

## Build an adapter without Python

### Scaffold

```bash
api-operator scaffold-adapter my-api --output examples
# writes adapter.yaml + policy.yaml + README
```

### Generate from OpenAPI

Write methods (`POST`/`PATCH`/`PUT`/`DELETE`) are marked `dangerous`. Tag-based abilities are suggested. A draft `policy.yaml` is written next to the adapter.

```bash
api-operator generate-from-openapi openapi.yaml \
  --output adapter.yaml \
  --base-url http://api.example.test \
  --path-prefix /api
```

### Examples

| Example | Purpose |
|---------|---------|
| [`examples/tenant-kit-adapter/`](examples/tenant-kit-adapter/) | Laravel Tenant Kit |
| [`examples/jsonplaceholder-adapter/`](examples/jsonplaceholder-adapter/) | Public REST demo |

```bash
export TENANT_KIT_API_TOKEN="your-sanctum-token"
api-operator chat \
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
    requires_ability: items:read

  - name: create_item
    description: Create item
    method: POST
    path: /api/items
    dangerous: true
    requires_ability: items:write
    parameters:
      title:
        type: string
        required: true
    body:
      title: "{title}"
```

Optional sibling `policy.yaml` loads automatically when you pass that adapter path.

## HTTP server

```bash
api-operator serve --port 8100
```

```json
POST /v1/chat
{
  "adapter": "yaml",
  "config_path": "examples/tenant-kit-adapter/adapter.yaml",
  "adapter_config": { "token": "YOUR_TOKEN" },
  "message": "list workspaces",
  "abilities": ["workspaces:read"],
  "dry_run": false
}
```

## Tests

```bash
pytest -q
```

Live Tenant Kit (optional):

```bash
python scripts/integration_tenant_kit.py
pytest -m integration -q
```

## Configuration

Copy `.env.example` → `.env`. Notable vars: `API_OPERATOR_PLANNER`, `API_OPERATOR_POLICY_PATH`, `API_OPERATOR_AUDIT_PATH`, `API_OPERATOR_QUOTA_BUDGET`, `API_OPERATOR_DRY_RUN`.

## Architecture

```
api-operator (Safe API Agent)     your hosts
├── plan → policy → quota → act     ├── adapter.yaml + policy.yaml
├── dry-run + audit hooks           ├── OpenAPI
└── mock / yaml adapters            └── Laravel / any REST API
```

## License

MIT — see [LICENSE](LICENSE).
