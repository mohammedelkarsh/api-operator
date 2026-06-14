# Tenant Kit adapter (YAML)

Configure the agent for [Laravel Tenant Kit](https://github.com/mohammedelkarsh/laravel-tenant-kit) without writing Python.

## Quick start

```bash
export TENANT_KIT_API_TOKEN="your-sanctum-token"
workspace-agent chat \
  --adapter yaml \
  --config examples/tenant-kit-adapter/adapter.yaml \
  --base-url http://laravel-tenant-kit.test
```

Or pass the token on the CLI:

```bash
workspace-agent chat \
  --adapter yaml \
  --config examples/tenant-kit-adapter/adapter.yaml \
  --token "YOUR_TOKEN" \
  --base-url http://laravel-tenant-kit.test
```

List available tools:

```bash
workspace-agent tools \
  --adapter yaml \
  --config examples/tenant-kit-adapter/adapter.yaml
```

## Central API token

After cloning and seeding Tenant Kit:

```bash
curl -X POST http://laravel-tenant-kit.test/api/auth/token \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@laravel-tenant-kit.test","password":"password","device_name":"agent"}'
```

Use seeded credentials from the Tenant Kit README in local dev only.

## Tenant API (team invite)

Team invitations run on the **tenant** subdomain and need a **tenant-scoped** token (not the central admin token). Issue one on the demo workspace:

```bash
curl -X POST http://demo.laravel-tenant-kit.test/api/auth/token \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@demo.test","password":"password","device_name":"agent","abilities":["team:invite","team:read"]}'
```

## Customize

Edit `adapter.yaml` — add tools, change paths, set `dangerous: true` for confirmation before writes.

## Integration test

From the workspace-agent repo root:

```bash
python scripts/integration_tenant_kit.py
```

Expect `INTEGRATION PASSED`.

## Related

Tenant Kit ships a copy under `integrations/workspace-agent/` (see tenant-kit repo).
