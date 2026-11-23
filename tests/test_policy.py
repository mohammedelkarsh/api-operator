from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from api_operator.adapters.mock import reset_mock_store
from api_operator.core.config import Settings
from api_operator.core.policy import PolicyContext, PolicyDocument, PolicyEngine, PolicyRule
from api_operator.core.schemas import Decision
from api_operator.factory import build_agent
from api_operator.tools.base import Tool, ToolResult


def _tool(name: str, *, dangerous: bool = False, ability: str | None = None) -> Tool:
    return Tool(
        name=name,
        description=name,
        handler=lambda: ToolResult(ok=True, data={}),
        dangerous=dangerous,
        requires_ability=ability,
    )


@pytest.fixture(autouse=True)
def clean_store():
    reset_mock_store()
    yield
    reset_mock_store()


def test_default_allow_without_policy():
    engine = PolicyEngine()
    decision = engine.check(_tool("list_workspaces"), context=PolicyContext())
    assert decision.decision == Decision.ALLOW


def test_deny_tools_list():
    engine = PolicyEngine(PolicyDocument(deny_tools=["delete_workspace"]))
    decision = engine.check(_tool("delete_workspace"))
    assert decision.decision == Decision.DENY
    assert decision.rule_id == "deny_tools"


def test_confirm_tools_list():
    engine = PolicyEngine(PolicyDocument(confirm_tools=["invite_team_member"]))
    decision = engine.check(_tool("invite_team_member"))
    assert decision.decision == Decision.CONFIRM
    assert decision.requires_confirmation is True


def test_dangerous_tool_requires_confirm():
    engine = PolicyEngine()
    decision = engine.check(_tool("create_workspace", dangerous=True))
    assert decision.decision == Decision.CONFIRM
    assert decision.rule_id == "dangerous"


def test_ability_deny():
    engine = PolicyEngine()
    decision = engine.check(
        _tool("create_workspace", ability="workspaces:write"),
        context=PolicyContext(abilities=["workspaces:read"]),
    )
    assert decision.decision == Decision.DENY
    assert "Permission denied" in (decision.reason or "")


def test_rule_deny_by_role():
    engine = PolicyEngine(
        PolicyDocument(
            rules=[
                PolicyRule(
                    id="block_viewer_writes",
                    tool_prefix="create_",
                    roles=["viewer"],
                    effect=Decision.DENY,
                    reason="Viewers cannot create resources.",
                )
            ]
        )
    )
    decision = engine.check(
        _tool("create_workspace"),
        context=PolicyContext(role="viewer"),
    )
    assert decision.decision == Decision.DENY
    assert decision.rule_id == "block_viewer_writes"


def test_rule_confirm_by_tenant():
    engine = PolicyEngine(
        PolicyDocument(
            rules=[
                PolicyRule(
                    id="tenant_confirm",
                    tools=["provision_link"],
                    tenants=["acme"],
                    effect=Decision.CONFIRM,
                )
            ]
        )
    )
    decision = engine.check(
        _tool("provision_link"),
        context=PolicyContext(tenant_id="acme"),
    )
    assert decision.decision == Decision.CONFIRM


def test_max_calls_per_session():
    engine = PolicyEngine(PolicyDocument(max_calls={"list_workspaces": 2}))
    tool = _tool("list_workspaces")
    ctx = PolicyContext(session_id="s1")

    assert engine.check(tool, context=ctx).decision == Decision.ALLOW
    engine.record_call("s1", "list_workspaces")
    assert engine.check(tool, context=ctx).decision == Decision.ALLOW
    engine.record_call("s1", "list_workspaces")
    denied = engine.check(tool, context=ctx)
    assert denied.decision == Decision.DENY
    assert denied.rule_id == "max_calls"


def test_load_policy_yaml(tmp_path: Path):
    path = tmp_path / "policy.yaml"
    path.write_text(
        yaml.dump(
            {
                "version": 1,
                "name": "demo",
                "deny_tools": ["drop_database"],
                "confirm_tools": ["create_workspace"],
                "max_calls": {"list_workspaces": 5},
                "rules": [
                    {
                        "id": "deny_admin_delete",
                        "tools": ["delete_workspace"],
                        "roles": ["member"],
                        "effect": "deny",
                        "reason": "Members cannot delete workspaces.",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    engine = PolicyEngine.from_yaml(path)
    assert engine.check(_tool("drop_database")).decision == Decision.DENY
    assert engine.check(_tool("create_workspace")).decision == Decision.CONFIRM
    assert (
        engine.check(
            _tool("delete_workspace"),
            context=PolicyContext(role="member"),
        ).decision
        == Decision.DENY
    )


@pytest.mark.asyncio
async def test_agent_deny_status_from_policy(tmp_path: Path):
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text(
        yaml.dump({"deny_tools": ["create_workspace"]}),
        encoding="utf-8",
    )
    agent = build_agent(
        "mock",
        settings=Settings(planner="mock"),
        policy_path=str(policy_path),
    )
    response = await agent.chat(
        "create workspace Acme subdomain acme",
        abilities=["workspaces:write"],
        auto_confirm=True,
    )
    assert response.status == "deny"
    assert response.tool == "create_workspace"
    assert "policy" in response.metadata


@pytest.mark.asyncio
async def test_agent_confirm_from_policy_list(tmp_path: Path):
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text(
        yaml.dump({"confirm_tools": ["list_workspaces"]}),
        encoding="utf-8",
    )
    agent = build_agent(
        "mock",
        settings=Settings(planner="mock"),
        policy_path=str(policy_path),
    )
    response = await agent.chat("list workspaces", abilities=["workspaces:read"])
    assert response.status == "confirm"
    assert response.tool == "list_workspaces"


@pytest.mark.asyncio
async def test_agent_permission_denied_status_is_deny():
    agent = build_agent("mock", settings=Settings(planner="mock"))
    response = await agent.chat(
        "create workspace Acme subdomain acme",
        abilities=["workspaces:read"],
        auto_confirm=True,
    )
    assert response.status == "deny"
    assert "Permission denied" in response.message
