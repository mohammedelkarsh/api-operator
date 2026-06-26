from api_operator.core.formatters import format_tool_success


def test_format_list_workspaces_from_api_payload():
    message = format_tool_success(
        "list_workspaces",
        {
            "data": [
                {
                    "id": "demo",
                    "name": "Demo Workspace",
                    "url": "http://demo.test",
                    "suspended": False,
                }
            ]
        },
    )

    assert "Found 1 workspace(s)" in message
    assert "Demo Workspace (demo)" in message
    assert "http://demo.test" in message
    assert "{" not in message


def test_format_list_workspaces_empty():
    message = format_tool_success("list_workspaces", {"workspaces": [], "count": 0})
    assert message == "No workspaces found."


def test_format_create_workspace():
    message = format_tool_success(
        "create_workspace",
        {"id": "acme", "name": "Acme", "url": "http://acme.test"},
    )
    assert "Workspace created: Acme (acme)" in message
    assert "http://acme.test" in message
