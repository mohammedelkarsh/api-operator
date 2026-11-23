# JSONPlaceholder adapter (non–tenant-kit example)

Public demo API — no Laravel, no token required.

```bash
api-operator tools --adapter yaml --config examples/jsonplaceholder-adapter/adapter.yaml
api-operator chat --adapter yaml --config examples/jsonplaceholder-adapter/adapter.yaml --dry-run
```

With live calls (still rate-limited politely by the public service):

```bash
api-operator chat --adapter yaml --config examples/jsonplaceholder-adapter/adapter.yaml
```

Try: `list posts`, `get post 1`, `create post title Hello body World userId 1` then confirm.
