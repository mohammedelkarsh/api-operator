#!/usr/bin/env python3
"""
Live integration test: api-operator + Laravel Tenant Kit.

Prerequisites:
  - Tenant Kit cloned and running (see tenant-kit README)
  - Database migrated and seeded
  - Demo workspace reachable (subdomain in hosts/DNS)

Usage:
  python scripts/integration_tenant_kit.py
  python scripts/integration_tenant_kit.py --base-url http://laravel-tenant-kit.test:8080
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import uuid
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
ADAPTER_YAML = ROOT / "examples" / "tenant-kit-adapter" / "adapter.yaml"

DEFAULT_BASE = "http://laravel-tenant-kit.test"
# Defaults match Laravel Tenant Kit seed data (see tenant-kit README)
ADMIN_EMAIL = os.environ.get("TENANT_KIT_ADMIN_EMAIL", "admin@laravel-tenant-kit.test")
ADMIN_PASSWORD = os.environ.get("TENANT_KIT_ADMIN_PASSWORD", "password")
DEMO_SUBDOMAIN = "demo"
DEMO_USER_EMAIL = os.environ.get("TENANT_KIT_DEMO_EMAIL", "demo@demo.test")
DEMO_USER_PASSWORD = os.environ.get("TENANT_KIT_DEMO_PASSWORD", "password")


def ok(msg: str) -> None:
    print(f"  [OK] {msg}")


def fail(msg: str) -> None:
    print(f"  [FAIL] {msg}")


def step(title: str) -> None:
    print(f"\n== {title} ==")


async def obtain_token(base_url: str) -> str:
    return await _issue_token(
        base_url,
        ADMIN_EMAIL,
        ADMIN_PASSWORD,
        device_name="api-operator-integration",
    )


async def obtain_tenant_token(base_url: str, subdomain: str) -> str:
    host = _central_host(base_url)
    tenant_url = f"http://{subdomain}.{host}"
    if base_url.startswith("https://"):
        tenant_url = f"https://{subdomain}.{host}"
    return await _issue_token(
        tenant_url,
        DEMO_USER_EMAIL,
        DEMO_USER_PASSWORD,
        device_name="api-operator-integration-tenant",
        abilities=["user:read", "team:read", "team:invite"],
    )


async def _issue_token(
    api_base: str,
    email: str,
    password: str,
    *,
    device_name: str,
    abilities: list[str] | None = None,
) -> str:
    payload: dict[str, object] = {
        "email": email,
        "password": password,
        "device_name": device_name,
    }
    if abilities is not None:
        payload["abilities"] = abilities

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{api_base.rstrip('/')}/api/auth/token",
            json=payload,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )
    if response.status_code != 200:
        raise RuntimeError(
            f"Token request failed ({response.status_code}): {response.text[:300]}"
        )
    body = response.json()
    token = body.get("token")
    if not token:
        raise RuntimeError(f"No token in response: {body}")
    return str(token)


def _central_host(base_url: str) -> str:
    rest = base_url.split("://", 1)[1]
    return rest.split("/", 1)[0]


async def detect_base_url() -> str:
    """Try port 80 first, then Docker Compose :8080."""
    candidates = [
        DEFAULT_BASE,
        "http://laravel-tenant-kit.test:8080",
    ]
    async with httpx.AsyncClient(timeout=8.0) as client:
        for url in candidates:
            try:
                response = await client.get(f"{url.rstrip('/')}/")
                if response.status_code < 500:
                    return url.rstrip("/")
            except httpx.HTTPError:
                continue
    return DEFAULT_BASE


async def run_agent_steps(
    base_url: str,
    central_token: str,
    tenant_token: str,
    workspace_subdomain: str,
    invite_subdomain: str,
) -> list[str]:
    from api_operator.core.config import Settings
    from api_operator.factory import build_agent

    if not ADAPTER_YAML.exists():
        raise FileNotFoundError(f"Missing adapter config: {ADAPTER_YAML}")

    central_agent = build_agent(
        "yaml",
        config_path=str(ADAPTER_YAML),
        token=central_token,
        base_url=base_url.rstrip("/"),
        settings=Settings(planner="mock"),
    )
    tenant_agent = build_agent(
        "yaml",
        config_path=str(ADAPTER_YAML),
        token=tenant_token,
        base_url=base_url.rstrip("/"),
        settings=Settings(planner="mock"),
    )
    central_abilities = ["workspaces:read", "workspaces:write"]
    tenant_abilities = ["team:read", "team:invite"]
    logs: list[str] = []

    async def say(
        agent,
        message: str,
        *,
        abilities: list[str],
        session_id: str | None = None,
        auto_confirm: bool = False,
    ) -> str:
        response = await agent.chat(
            message=message,
            session_id=session_id,
            abilities=abilities,
            auto_confirm=auto_confirm,
        )
        logs.append(f"{message!r} -> {response.status}: {response.message[:120]}")
        if response.status == "error":
            raise RuntimeError(logs[-1])
        return response.session_id

    sid = await say(
        central_agent,
        "list workspaces",
        abilities=central_abilities,
    )
    sid = await say(
        central_agent,
        f"create workspace IntegrationTest subdomain {workspace_subdomain}",
        abilities=central_abilities,
        session_id=sid,
    )
    sid = await say(central_agent, "yes", abilities=central_abilities, session_id=sid)
    sid = await say(
        central_agent,
        "list workspaces",
        abilities=central_abilities,
        session_id=sid,
    )

    # Team invite uses the seeded demo subdomain (must resolve in DNS/hosts).
    invite_email = f"integration+{workspace_subdomain}@example.test"
    tenant_sid = await say(
        tenant_agent,
        f"invite {invite_email} to {invite_subdomain} member",
        abilities=tenant_abilities,
    )
    await say(tenant_agent, "yes", abilities=tenant_abilities, session_id=tenant_sid)
    return logs


async def verify_api(base_url: str, token: str, workspace_subdomain: str) -> None:
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        workspaces = await client.get(f"{base_url}/api/workspaces", headers=headers)
        if workspaces.status_code != 200:
            raise RuntimeError(f"GET /api/workspaces -> {workspaces.status_code}")
        data = workspaces.json().get("data", [])
        ids = {item.get("id") for item in data}
        if workspace_subdomain not in ids:
            raise RuntimeError(f"Workspace '{workspace_subdomain}' not in API list: {ids}")


async def main() -> int:
    parser = argparse.ArgumentParser(description="Integrate api-operator with tenant-kit")
    parser.add_argument(
        "--base-url",
        default="",
        help="Central APP_URL (auto-detect Laragon :80 vs Docker :8080 if omitted)",
    )
    parser.add_argument(
        "--subdomain",
        default="",
        help="Workspace subdomain to create (random agentXXXXXXXX if omitted)",
    )
    parser.add_argument(
        "--invite-subdomain",
        default=DEMO_SUBDOMAIN,
        help="Subdomain for team invite (default: demo from tenant-kit seed)",
    )
    args = parser.parse_args()
    base_url = (args.base_url or await detect_base_url()).rstrip("/")
    subdomain = (args.subdomain or f"agent{uuid.uuid4().hex[:8]}").lower()
    invite_subdomain = args.invite_subdomain.lower()

    print("API Operator × Tenant Kit — integration test")
    print(f"Base URL: {base_url}")
    print(f"Subdomain: {subdomain} (invite on '{invite_subdomain}')")
    print(f"Adapter:  {ADAPTER_YAML}")

    errors = 0

    step("1. Reach tenant-kit")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            ping = await client.get(f"{base_url}/")
        if ping.status_code >= 500:
            fail(f"Central app returned {ping.status_code}")
            errors += 1
        else:
            ok(f"Central app reachable (HTTP {ping.status_code})")
    except httpx.HTTPError as exc:
        fail(f"Cannot reach {base_url}: {exc}")
        print("\nStart Tenant Kit first. See https://github.com/mohammedelkarsh/laravel-tenant-kit")
        return 1

    step("2. Obtain Sanctum tokens")
    try:
        central_token = await obtain_token(base_url)
        ok(f"Central token ({central_token[:12]}...)")
        tenant_token = await obtain_tenant_token(base_url, invite_subdomain)
        ok(f"Tenant token for '{invite_subdomain}' ({tenant_token[:12]}...)")
    except RuntimeError as exc:
        fail(str(exc))
        return 1

    step("3. Agent conversation (YAML adapter)")
    try:
        logs = await run_agent_steps(
            base_url,
            central_token,
            tenant_token,
            subdomain,
            invite_subdomain,
        )
        for line in logs:
            ok(line)
    except RuntimeError as exc:
        fail(str(exc))
        errors += 1

    step("4. Verify via API")
    try:
        await verify_api(base_url, central_token, subdomain)
        ok(f"Workspace '{subdomain}' visible in GET /api/workspaces")
    except RuntimeError as exc:
        fail(str(exc))
        errors += 1

    print("\n" + ("=" * 50))
    if errors:
        print(f"INTEGRATION FAILED ({errors} step(s))")
        return 1
    print("INTEGRATION PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
