# Policy engine

Optional `policy.yaml` beside an adapter (or via `API_OPERATOR_POLICY_PATH` / CLI `--policy`).

## Decisions

| Decision | Meaning |
|----------|---------|
| `allow` | Proceed to execute (or dry-run report) |
| `deny` | Reject with a clear reason (`status=deny`) |
| `confirm` | Ask the user before executing |

## Minimal example

```yaml
version: 1
name: demo
default: allow
deny_tools:
  - drop_database
confirm_tools:
  - create_workspace
max_calls:
  list_workspaces: 20
rules:
  - id: block_viewers
    tools: [create_workspace]
    roles: [viewer]
    effect: deny
    reason: Viewers cannot create workspaces.
```

## Evaluation order

1. `deny_tools`
2. Document `max_calls`
3. First matching rule (`deny` / `confirm` win; `allow` only gates `default: deny`)
4. Tool `requires_ability` (when `abilities` are provided)
5. `confirm_tools` / tool `dangerous`
6. Document `default`

Without a policy file, behavior matches 0.10: ability checks + dangerous confirmation.
