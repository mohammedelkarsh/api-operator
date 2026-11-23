# Dry-run mode

Plan + policy evaluation **without** calling upstream APIs.

## CLI

```bash
api-operator chat --adapter mock --dry-run
api-operator chat --adapter yaml --config examples/tenant-kit-adapter/adapter.yaml --dry-run
```

## HTTP

```http
POST /v1/chat
{
  "message": "create workspace Acme subdomain acme",
  "abilities": ["workspaces:write"],
  "auto_confirm": true,
  "dry_run": true
}
```

Response includes `dry_run_report`:

- `tool` / `arguments`
- `policy` decision
- `would_call` (YAML adapters: method, URL, redacted headers, body)

No `pending_confirmation` is stored in dry-run; confirm decisions are reported only.
