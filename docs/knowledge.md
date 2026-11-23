# Knowledge (RAG) — opt-in

Knowledge helps the planner choose the right tool. It is **off by default**.

```bash
export API_OPERATOR_KNOWLEDGE_ENABLED=true
```

## Backends

| Backend | Setting | Needs | Notes |
|---------|---------|--------|--------|
| **keyword** (L0) | `API_OPERATOR_KNOWLEDGE_BACKEND=keyword` | core only | Default when knowledge is enabled |
| **embedding** (L1) | `…=embedding` | optional OpenAI key; else hashing embedder | In-memory vectors at startup |
| **pgvector** (L2) | `…=pgvector` | `pip install 'api-operator[rag]'` + DSN | Host owns indexing |

```bash
export API_OPERATOR_KNOWLEDGE_PATHS="docs/api.md,README.md"
export API_OPERATOR_KNOWLEDGE_BACKEND=keyword   # or embedding
# export API_OPERATOR_OPENAI_API_KEY=...        # for OpenAI embeddings
# export API_OPERATOR_KNOWLEDGE_PG_DSN=postgresql+psycopg://...
```

## L0 — Keyword

No embeddings. Best for small curated docs.

## L1 — Embedding (local index)

Chunks docs at agent start, embeds them, ranks by cosine similarity.

- With `API_OPERATOR_OPENAI_API_KEY`: uses `text-embedding-3-small` (override via `API_OPERATOR_KNOWLEDGE_EMBEDDING_MODEL`)
- Without a key: uses a deterministic **hashing embedder** (fine for demos/tests, weaker quality)

```python
from api_operator.rag import EmbeddingKnowledge, HashingEmbedder
from api_operator.factory import build_agent
from api_operator.core.config import Settings

knowledge = EmbeddingKnowledge(["docs/guide.md"], embedder=HashingEmbedder())
agent = build_agent(
    "mock",
    knowledge=knowledge,
    settings=Settings(knowledge_enabled=True, knowledge_backend="embedding"),
)
```

## L2 — Postgres + pgvector

Retrieval-only against a table you maintain (e.g. from Laravel):

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE api_operator_knowledge (
    id bigserial PRIMARY KEY,
    source text NOT NULL,
    excerpt text NOT NULL,
    tenant_id text NULL,
    embedding vector(1536) NOT NULL
);
```

```bash
pip install "api-operator[rag]"
export API_OPERATOR_KNOWLEDGE_ENABLED=true
export API_OPERATOR_KNOWLEDGE_BACKEND=pgvector
export API_OPERATOR_KNOWLEDGE_PG_DSN="postgresql+psycopg://user:pass@localhost/app"
```

## Tenant isolation

Paths containing `/tenants/{tenant_id}/` (and pgvector `tenant_id` column) stay private:

- No `tenant_id` on `/v1/chat` → shared docs only
- `tenant_id=acme` → shared + acme — never another tenant

## Response metadata

```json
"metadata": {
  "knowledge": {
    "enabled": true,
    "backend": "embedding",
    "hits": 2,
    "sources": ["docs/guide.md"]
  }
}
```
