from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="WORKSPACE_AGENT_",
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
