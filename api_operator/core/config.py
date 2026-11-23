from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="api_operator_",
        env_file=".env",
        extra="ignore",
    )

    host: str = "127.0.0.1"
    port: int = 8100
    default_adapter: str = "mock"
    planner: str = "auto"  # auto | mock | openai
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    require_confirm_dangerous: bool = True
    log_tool_calls: bool = True
    cors_origins: str = ""  # comma-separated origins; empty disables CORS middleware
    policy_path: str | None = None  # optional policy.yaml
    audit_enabled: bool = True
    audit_path: str | None = None  # JSONL file; None = NullAuditSink unless injected
    dry_run: bool = False
    quota_budget: float | None = None  # enables InMemoryQuotaGateway when set
    knowledge_enabled: bool = False  # opt-in knowledge (off by default)
    knowledge_paths: str | None = None  # comma-separated doc paths (L0/L1)
    knowledge_limit: int = 3
    knowledge_backend: str = "keyword"  # keyword | embedding | pgvector
    knowledge_embedding_model: str = "text-embedding-3-small"
    knowledge_pg_dsn: str | None = None  # postgres DSN for L2 pgvector
