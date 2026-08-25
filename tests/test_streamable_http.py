"""In-process Streamable HTTP integration tests."""

from __future__ import annotations

import json
import logging

import httpx2 as httpx
import pytest

from root_mcp.config import (
    AuthConfig,
    Config,
    DeploymentConfig,
    HTTPConfig,
    PolicyConfig,
    SecurityConfig,
)
from root_mcp.security import AuthResult
from root_mcp.server import ROOTMCPServer
from root_mcp.transport.http import build_streamable_http_app


def _config(*, allow_tools: list[str] | None = None) -> Config:
    return Config(
        server={"mode": "core"},
        deployment=DeploymentConfig(profile="central", transport="streamable_http"),
        auth=AuthConfig(required=True, provider="external_bearer"),
        security=SecurityConfig(allowed_protocols=["root"]),
        policy=PolicyConfig(
            default_tool_action="deny",
            allow_tools=allow_tools or ["get_server_info"],
            require_named_resources=True,
            disable_local_absolute_paths=True,
        ),
        http=HTTPConfig(origin_allowlist=["https://client.example"]),
    )


def _headers() -> dict[str, str]:
    return {
        "origin": "https://client.example",
        "authorization": "Bearer ok",
        "accept": "application/json",
        "content-type": "application/json",
    }


async def _initialize(client: httpx.AsyncClient) -> str | None:
    response = await client.post(
        "/mcp",
        headers=_headers(),
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "pytest", "version": "0"},
            },
        },
    )
    assert response.status_code == 200
    return response.headers.get("mcp-session-id")


@pytest.mark.asyncio
async def test_streamable_http_lists_policy_filtered_tools() -> None:
    app = build_streamable_http_app(
        ROOTMCPServer(_config(allow_tools=["get_server_info"])),
        bearer_validator=lambda token: AuthResult(principal_id="alice") if token == "ok" else None,
    )
    await app.startup()
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            session_id = await _initialize(client)
            assert session_id is not None
            response = await client.post(
                "/mcp",
                headers={
                    **_headers(),
                    "mcp-protocol-version": "2025-03-26",
                    "mcp-session-id": session_id,
                },
                json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            )
    finally:
        await app.shutdown()

    assert response.status_code == 200
    tool_names = [tool["name"] for tool in response.json()["result"]["tools"]]
    assert tool_names == ["get_server_info"]


@pytest.mark.asyncio
async def test_streamable_http_tool_call_uses_authenticated_context(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger="root_mcp.security.audit")
    app = build_streamable_http_app(
        ROOTMCPServer(_config(allow_tools=["get_server_info"])),
        bearer_validator=lambda token: (
            AuthResult(
                principal_id="alice",
                tenant_id="atlas",
                roles={"reader"},
            )
            if token == "ok"
            else None
        ),
    )
    await app.startup()
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            session_id = await _initialize(client)
            assert session_id is not None
            response = await client.post(
                "/mcp",
                headers={
                    **_headers(),
                    "mcp-protocol-version": "2025-03-26",
                    "mcp-session-id": session_id,
                },
                json={
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {"name": "get_server_info", "arguments": {}},
                },
            )
    finally:
        await app.shutdown()

    assert response.status_code == 200
    payload = json.loads(response.json()["result"]["content"][0]["text"])
    assert payload["transport"] == "streamable_http"
    assert any('"principal": "alice"' in record.message for record in caplog.records)
    assert any('"tenant": "atlas"' in record.message for record in caplog.records)


@pytest.mark.asyncio
async def test_streamable_http_policy_denial_matches_stdio_shape() -> None:
    app = build_streamable_http_app(
        ROOTMCPServer(_config(allow_tools=["get_server_info"])),
        bearer_validator=lambda token: AuthResult(principal_id="alice") if token == "ok" else None,
    )
    await app.startup()
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            session_id = await _initialize(client)
            assert session_id is not None
            response = await client.post(
                "/mcp",
                headers={
                    **_headers(),
                    "mcp-protocol-version": "2025-03-26",
                    "mcp-session-id": session_id,
                },
                json={
                    "jsonrpc": "2.0",
                    "id": 4,
                    "method": "tools/call",
                    "params": {"name": "switch_mode", "arguments": {"mode": "core"}},
                },
            )
    finally:
        await app.shutdown()

    assert response.status_code == 200
    payload = json.loads(response.json()["result"]["content"][0]["text"])
    assert payload["error"] == "policy_denied"
    assert payload["reason"] == "central_switch_mode_denied"


@pytest.mark.asyncio
async def test_streamable_http_endpoint_is_exact() -> None:
    app = build_streamable_http_app(
        ROOTMCPServer(_config()),
        bearer_validator=lambda token: AuthResult(principal_id="alice"),
    )
    await app.startup()
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
            follow_redirects=False,
        ) as client:
            ok = await client.options("/mcp", headers={"origin": "https://client.example"})
            trailing = await client.options("/mcp/", headers={"origin": "https://client.example"})
    finally:
        await app.shutdown()

    assert ok.status_code == 204
    assert trailing.status_code == 404
