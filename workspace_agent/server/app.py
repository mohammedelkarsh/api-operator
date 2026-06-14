from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from workspace_agent.adapters.registry import available_adapters
from workspace_agent.core.config import Settings
from workspace_agent.core.memory import SessionStore
from workspace_agent.factory import build_agent


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    adapter: str | None = None
    adapter_class: str | None = None
    config_path: str | None = None
    abilities: list[str] | None = None
    auto_confirm: bool = False
    adapter_config: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    session_id: str
    message: str
    status: str
    tool: str | None = None
    tool_result: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def create_app(settings: Settings | None = None):
    from fastapi import FastAPI, HTTPException

    settings = settings or Settings()
    session_store = SessionStore()
    app = FastAPI(
        title="Workspace Agent",
        version="0.1.0",
        description="Standalone AI operator with pluggable adapters",
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "adapter_default": settings.default_adapter}

    @app.get("/v1/adapters")
    async def adapters() -> dict[str, Any]:
        return {
            "builtin": available_adapters(),
            "yaml": "Use adapter=yaml with config_path in adapter_config",
            "external": "Use adapter_class=module.path:ClassName (see examples/)",
        }

    @app.get("/v1/tools")
    async def tools(
        adapter: str | None = None,
        adapter_class: str | None = None,
        config_path: str | None = None,
        base_url: str | None = None,
        token: str | None = None,
    ) -> dict[str, Any]:
        name = adapter or settings.default_adapter
        config: dict[str, Any] = {}
        if config_path:
            config["config_path"] = config_path
        if base_url:
            config["base_url"] = base_url
        if token:
            config["token"] = token
        agent = build_agent(
            name,
            settings=settings,
            adapter_class=adapter_class,
            config_path=config_path,
            base_url=base_url,
            token=token,
        )
        return {"adapter": name, "adapter_class": adapter_class, "tools": agent.list_tools()}

    @app.post("/v1/chat", response_model=ChatResponse)
    async def chat(payload: ChatRequest) -> ChatResponse:
        name = payload.adapter or settings.default_adapter
        extra = dict(payload.adapter_config)
        cfg = payload.config_path or extra.pop("config_path", None)
        try:
            agent = build_agent(
                name,
                settings=settings,
                adapter_class=payload.adapter_class,
                config_path=cfg,
                sessions=session_store,
                **extra,
            )
        except (ValueError, TypeError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        response = await agent.chat(
            message=payload.message,
            session_id=payload.session_id,
            abilities=payload.abilities,
            auto_confirm=payload.auto_confirm,
        )
        return ChatResponse(
            session_id=response.session_id,
            message=response.message,
            status=response.status,
            tool=response.tool,
            tool_result=response.tool_result,
            metadata=response.metadata,
        )

    return app
