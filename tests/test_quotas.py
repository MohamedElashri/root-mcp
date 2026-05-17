"""Quota and central concurrency tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from root_mcp.config import (
    AuthConfig,
    Config,
    DeploymentConfig,
    PolicyConfig,
    QuotaConfig,
    SecurityConfig,
)
from root_mcp.security import RequestContext
from root_mcp.server import ROOTMCPServer


def _central_config(tmp_path: Path, quotas: QuotaConfig | None = None) -> Config:
    return Config(
        deployment=DeploymentConfig(profile="central", transport="streamable_http"),
        auth=AuthConfig(required=True, provider="external_bearer"),
        security=SecurityConfig(allowed_roots=[str(tmp_path)]),
        policy=PolicyConfig(default_tool_action="deny", allow_tools=["list_files"]),
        quotas=quotas or QuotaConfig(),
    )


def _ctx(principal: str = "alice", tenant: str = "tenant-a") -> RequestContext:
    return RequestContext(
        deployment_profile="central",
        transport="streamable_http",
        tenant_id=tenant,
        principal_id=principal,
        request_id=f"req-{principal}",
    )


@pytest.mark.asyncio
async def test_principal_concurrency_quota_denies_second_running_call(
    tmp_path: Path,
) -> None:
    server = ROOTMCPServer(
        _central_config(
            tmp_path,
            QuotaConfig(
                max_concurrent_requests_per_principal=1,
                max_concurrent_requests_per_tenant=10,
            ),
        )
    )

    async with server.quota_manager.reserve(_ctx(), "list_files", {"resource": "data"}):
        second = await server.handle_tool_call("list_files", {"resource": "data"}, _ctx())
        payload = json.loads(second[0].text)

    assert payload["error"] == "quota_exceeded"
    assert payload["reason"] == "principal_concurrency_exceeded"
    assert server.metrics.snapshot()["denied_calls"] == 1


@pytest.mark.asyncio
async def test_tenant_concurrency_quota_spans_principals(
    tmp_path: Path,
) -> None:
    server = ROOTMCPServer(
        _central_config(
            tmp_path,
            QuotaConfig(
                max_concurrent_requests_per_principal=10,
                max_concurrent_requests_per_tenant=1,
            ),
        )
    )

    async with server.quota_manager.reserve(_ctx("alice"), "list_files", {"resource": "data"}):
        second = await server.handle_tool_call(
            "list_files",
            {"resource": "data"},
            _ctx("bob"),
        )
        payload = json.loads(second[0].text)

    assert payload["error"] == "quota_exceeded"
    assert payload["reason"] == "tenant_concurrency_exceeded"


@pytest.mark.asyncio
async def test_row_quota_denies_visible_oversized_request(tmp_path: Path) -> None:
    server = ROOTMCPServer(_central_config(tmp_path, QuotaConfig(max_rows_per_call=10)))

    content = await server.handle_tool_call(
        "list_files",
        {"resource": "data", "limit": 11},
        _ctx(),
    )
    payload = json.loads(content[0].text)

    assert payload["error"] == "quota_exceeded"
    assert payload["reason"] == "row_quota_exceeded"


@pytest.mark.asyncio
async def test_request_timeout_returns_quota_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    server = ROOTMCPServer(_central_config(tmp_path, QuotaConfig(max_request_seconds=1)))

    def slow_dispatch(name, arguments, ctx):
        del name, arguments, ctx
        import time

        time.sleep(2)
        return {"ok": True}

    monkeypatch.setattr(server, "_dispatch_tool", slow_dispatch)

    content = await server.handle_tool_call("list_files", {"resource": "data"}, _ctx())
    payload = json.loads(content[0].text)

    assert payload["error"] == "quota_exceeded"
    assert payload["reason"] == "request_timeout"
    assert server.metrics.snapshot()["timeout_count"] == 1


@pytest.mark.asyncio
async def test_output_byte_quota_uses_reported_export_size(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    server = ROOTMCPServer(_central_config(tmp_path, QuotaConfig(max_output_bytes_per_call=100)))
    monkeypatch.setattr(
        server,
        "_dispatch_tool",
        lambda name, arguments, ctx: {"data": {"size_bytes": 101}},
    )

    content = await server.handle_tool_call("list_files", {"resource": "data"}, _ctx())
    payload = json.loads(content[0].text)

    assert payload["error"] == "quota_exceeded"
    assert payload["reason"] == "output_bytes_quota_exceeded"
