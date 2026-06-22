"""HTTP authentication and request gate tests."""

from __future__ import annotations

import httpx
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


def _config() -> Config:
    return Config(
        server={"mode": "core"},
        deployment=DeploymentConfig(profile="central", transport="streamable_http"),
        auth=AuthConfig(required=True, provider="external_bearer"),
        security=SecurityConfig(allowed_protocols=["root"]),
        policy=PolicyConfig(
            default_tool_action="deny",
            allow_tools=["get_server_info"],
            require_named_resources=True,
            disable_local_absolute_paths=True,
        ),
        http=HTTPConfig(origin_allowlist=["https://client.example"]),
    )


def _trusted_header_config() -> Config:
    config = _config()
    config.auth.provider = "trusted_headers"
    return config


@pytest.mark.asyncio
async def test_http_rejects_missing_bearer_token() -> None:
    app = build_streamable_http_app(
        ROOTMCPServer(_config()),
        bearer_validator=lambda token: AuthResult(principal_id="alice") if token == "ok" else None,
    )
    await app.startup()
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.post(
                "/mcp",
                headers={"origin": "https://client.example", "accept": "application/json"},
                json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
            )
    finally:
        await app.shutdown()

    assert response.status_code == 401
    assert response.json()["error"] == "unauthorized"


@pytest.mark.asyncio
async def test_http_rejects_disallowed_origin_before_auth() -> None:
    app = build_streamable_http_app(
        ROOTMCPServer(_config()),
        bearer_validator=lambda token: AuthResult(principal_id="alice"),
    )
    await app.startup()
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.post(
                "/mcp",
                headers={
                    "origin": "https://evil.example",
                    "authorization": "Bearer ok",
                    "accept": "application/json",
                },
                json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
            )
    finally:
        await app.shutdown()

    assert response.status_code == 403
    assert response.json()["error"] == "origin_denied"


@pytest.mark.asyncio
async def test_http_rejects_invalid_session_id_header() -> None:
    app = build_streamable_http_app(
        ROOTMCPServer(_config()),
        bearer_validator=lambda token: AuthResult(principal_id="alice"),
    )
    await app.startup()
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.post(
                "/mcp",
                headers={
                    "origin": "https://client.example",
                    "authorization": "Bearer ok",
                    "accept": "application/json",
                    "mcp-session-id": "bad session",
                },
                json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
            )
    finally:
        await app.shutdown()

    assert response.status_code == 400
    assert response.json()["error"] == "invalid_session_id"


@pytest.mark.asyncio
async def test_http_trusted_headers_authenticates_from_trusted_proxy() -> None:
    app = build_streamable_http_app(ROOTMCPServer(_trusted_header_config()))
    await app.startup()
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.post(
                "/mcp",
                headers={
                    "origin": "https://client.example",
                    "x-auth-principal": "alice",
                    "x-auth-tenant": "atlas",
                    "accept": "application/json",
                    "content-type": "application/json",
                },
                json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
            )
    finally:
        await app.shutdown()

    assert response.status_code == 200
    assert response.json()["result"]["tools"][0]["name"] == "get_server_info"
