# Knowledge (RAG) — opt-in

Knowledge helps the planner choose the right tool. It is **off by default**.

## L0 — Keyword (ships in core / 1.0+)

No embeddings, no extra packages.

```bash
export API_OPERATOR_KNOWLEDGE_ENABLED=true
export API_OPERATOR_KNOWLEDGE_PATHS="docs/api.md,README.md"
api-operator chat --adapter mock
```

Or inject a store:

```python
from api_operator.rag import KeywordKnowledge
from api_operator.factory import build_agent

knowledge = KeywordKnowledge(["docs/guide.md"])
agent = build_agent("mock", knowledge=knowledge, settings=Settings(knowledge_enabled=True))
```

Retrieved excerpts are appended to the planner `system_prompt`. Responses may include:

```json
"metadata": { "knowledge": { "enabled": true, "hits": 2, "sources": ["..."] } }
```

### Tenant isolation

Paths containing `/tenants/{tenant_id}/` are private to that tenant:

- Without `tenant_id` on `/v1/chat`: only shared docs (no `/tenants/` segment)
- With `tenant_id=acme`: shared docs + `/tenants/acme/**` only — never another tenant

## L1 / L2 — planned (1.1+)

| Layer | Tech | Extra |
|-------|------|--------|
| L1 | Local embeddings | `pip install api-operator[rag]` (future) |
| L2 | Postgres + pgvector | same extra |
| L3 | Pinecone / Qdrant | later drivers |

Keyword L0 remains available without the extra.
