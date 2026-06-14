from __future__ import annotations

import json
from typing import Any

from operator_agent.core.config import Settings
from operator_agent.core.planner import MockPlanner, PlanStep, Planner
from operator_agent.tools.base import ToolRegistry


class OpenAIPlanner:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def plan(
        self,
        message: str,
        registry: ToolRegistry,
        history: list[dict[str, str]],
        system_prompt: str,
    ) -> PlanStep:
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise RuntimeError(
                "OpenAI planner requires optional dependency. Install with: pip install operator-agent[llm]"
            ) from exc

        if not self.settings.openai_api_key:
            raise RuntimeError("operator_agent_OPENAI_API_KEY is not set.")

        client = AsyncOpenAI(api_key=self.settings.openai_api_key)
        tools = [_openai_tool_schema(tool.schema()) for tool in registry.list_tools()]
        messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
        messages.extend(history[-12:])
        messages.append({"role": "user", "content": message})

        response = await client.chat.completions.create(
            model=self.settings.openai_model,
            messages=messages,
            tools=tools or None,
            tool_choice="auto" if tools else None,
        )
        choice = response.choices[0].message

        if choice.tool_calls:
            call = choice.tool_calls[0]
            args = json.loads(call.function.arguments or "{}")
            return PlanStep(type="tool", tool_name=call.function.name, tool_args=args)

        return PlanStep(type="respond", content=choice.content or "")


def _openai_tool_schema(schema: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": schema["name"],
            "description": schema["description"],
            "parameters": schema["parameters"],
        },
    }


def build_planner(settings: Settings) -> Planner:
    mode = settings.planner
    if mode == "auto":
        mode = "openai" if settings.openai_api_key else "mock"
    if mode == "openai":
        return OpenAIPlanner(settings)
    return MockPlanner()
