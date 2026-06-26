import pytest

from api_operator.core.config import Settings
from api_operator.core.executor import ToolExecutor
from api_operator.core.guardrails import Guardrails
from api_operator.core.memory import SessionStore
from api_operator.core.planner import MockPlanner
from api_operator.tools.base import Tool, ToolRegistry, ToolResult
from api_operator.tools.schema import tool_parameters_schema


@pytest.mark.parametrize(
    "message,expected",
    [
        ("yes", True),
        ("YES", True),
        ("confirm", True),
        ("نعم", True),
        ("موافق", True),
        ("no", False),
        ("maybe", False),
    ],
)
def test_guardrails_confirmation(message, expected):
    assert Guardrails.is_confirmation(message) is expected


@pytest.mark.parametrize(
    "message,expected",
    [
        ("no", True),
        ("cancel", True),
        ("لا", True),
        ("إلغاء", True),
        ("yes", False),
    ],
)
def test_guardrails_cancellation(message, expected):
    assert Guardrails.is_cancellation(message) is expected


def test_guardrails_ability_check():
    tool = Tool(
        name="t",
        description="d",
        handler=lambda: ToolResult(ok=True),
        requires_ability="workspaces:write",
    )
    g = Guardrails()
    assert g.check_ability(tool, ["workspaces:read"]) is not None
    assert g.check_ability(tool, ["workspaces:write"]) is None
    assert g.check_ability(tool, None) is None


def test_guardrails_missing_parameters():
    tool = Tool(
        name="t",
        description="d",
        handler=lambda: ToolResult(ok=True),
        parameters={"name": str, "subdomain": str},
        required=["name", "subdomain"],
    )
    g = Guardrails()
    assert g.missing_parameters(tool, {"name": "Acme"}) == ["subdomain"]
    assert g.missing_parameters(tool, {"name": "Acme", "subdomain": "acme"}) == []


def test_session_store_memory():
    store = SessionStore()
    s1 = store.create("mock")
    s1.add("user", "hello")
    s1.add("assistant", "hi")
    assert len(s1.history()) == 2

    s2 = store.get_or_create(s1.id, "mock")
    assert s2.id == s1.id
    assert len(s2.messages) == 2


@pytest.mark.asyncio
async def test_executor_runs_tool():
    registry = ToolRegistry()

    async def handler(name: str) -> ToolResult:
        return ToolResult(ok=True, data={"name": name})

    registry.register(
        Tool(
            name="echo",
            description="echo",
            handler=handler,
            parameters={"name": str},
            required=["name"],
        )
    )
    executor = ToolExecutor()
    result, error = await executor.execute(registry, "echo", {"name": "Acme"})
    assert error is None
    assert result.ok is True
    assert result.data["name"] == "Acme"


@pytest.mark.asyncio
async def test_executor_unknown_tool():
    executor = ToolExecutor()
    result, error = await executor.execute(ToolRegistry(), "missing", {})
    assert result is None
    assert "Unknown tool" in error


@pytest.mark.asyncio
async def test_mock_planner_routes():
    from api_operator.adapters.mock import MockAdapter

    planner = MockPlanner()
    registry = MockAdapter().build_registry()

    step = await planner.plan("list workspaces", registry, [], "")
    assert step.type == "tool" and step.tool_name == "list_workspaces"

    step = await planner.plan("create workspace Acme subdomain acme", registry, [], "")
    assert step.tool_name == "create_workspace"
    assert step.tool_args["subdomain"] == "acme"

    step = await planner.plan("help", registry, [], "")
    assert step.type == "respond"

    step = await planner.plan("provision link Riyadh Jeddah 500", registry, [], "")
    assert step.tool_name == "provision_link"


@pytest.mark.asyncio
async def test_mock_planner_natural_language():
    from api_operator.adapters.mock import MockAdapter

    planner = MockPlanner()
    registry = MockAdapter().build_registry()

    for phrase in (
        "i want list of workspaces?",
        "show me all workspaces",
        "what workspaces do I have",
    ):
        step = await planner.plan(phrase, registry, [], "")
        assert step.type == "tool" and step.tool_name == "list_workspaces", phrase

    step = await planner.plan("get usage for demo", registry, [], "")
    assert step.tool_name == "get_usage"
    assert step.tool_args["workspace_id"] == "demo"

    step = await planner.plan("subscription for demo", registry, [], "")
    assert step.tool_name == "get_subscription"
    assert step.tool_args["workspace_id"] == "demo"


def test_tool_parameters_schema():
    schema = tool_parameters_schema({"name": str, "count": int}, ["name"])
    assert schema["properties"]["name"]["type"] == "string"
    assert schema["required"] == ["name"]


def test_settings_from_env(monkeypatch):
    monkeypatch.setenv("api_operator_PORT", "9999")
    monkeypatch.setenv("api_operator_PLANNER", "mock")
    settings = Settings()
    assert settings.port == 9999
    assert settings.planner == "mock"


def test_tool_registry_duplicate_raises():
    registry = ToolRegistry()
    tool = Tool(name="x", description="d", handler=lambda: ToolResult(ok=True))
    registry.register(tool)
    with pytest.raises(ValueError, match="already registered"):
        registry.register(tool)
