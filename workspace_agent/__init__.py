"""Workspace Agent — standalone AI operator with pluggable adapters."""

from workspace_agent.core.agent import Agent, AgentResponse
from workspace_agent.core.config import Settings
from workspace_agent.tools.base import Tool, ToolRegistry

__all__ = ["Agent", "AgentResponse", "Settings", "Tool", "ToolRegistry"]
__version__ = "0.9.0"
