"""Central deployment tool visibility and policy-denied response tests."""

from __future__ import annotations

import json

import pytest

from root_mcp.config import AuthConfig, Config, DeploymentConfig, PolicyConfig, SecurityConfig
from root_mcp.security import RequestContext
from root_mcp.server import ROOTMCPServer


def _central_config(
    *,
    allow_tools: list[str] | None = None,
    require_named_resources: bool = False,
) -> Config:
    return Config(
        deployment=DeploymentConfig(profile="central", transport="streamable_http"),
        auth=AuthConfig(required=True, provider="external_bearer"),
        security=SecurityConfig(allowed_roots=["/data"]),
        policy=PolicyConfig(
            default_tool_action="deny",
            allow_tools=allow_tools or ["list_files", "get_server_info"],
            require_named_resources=require_named_resources,
        ),
    )


def _central_ctx() -> RequestContext:
    return RequestContext(
        deployment_profile="central",
        transport="streamable_http",
        principal_id="alice",
        request_id="req-central",
    )


def _content_payload(content) -> dict:
    return json.loads(content[0].text)


def test_local_profile_advertises_unfiltered_tools() -> None:
    server = ROOTMCPServer(Config())

    unfiltered_names = [tool.name for tool in server._get_unfiltered_tools()]
    visible_names = [tool.name for tool in server.list_available_tools()]

    assert visible_names == unfiltered_names
    assert "switch_mode" in visible_names


def test_central_profile_filters_switch_mode_from_tool_list() -> None:
    server = ROOTMCPServer(_central_config(allow_tools=["list_files", "switch_mode"]))

    visible_names = [tool.name for tool in server.list_available_tools(_central_ctx())]

    assert "list_files" in visible_names
    assert "switch_mode" not in visible_names


@pytest.mark.asyncio
async def test_central_switch_mode_call_returns_policy_error() -> None:
    server = ROOTMCPServer(_central_config(allow_tools=["switch_mode"]))

    payload = _content_payload(
        await server.handle_tool_call("switch_mode", {"mode": "core"}, _central_ctx())
    )

    assert payload == {
        "error": "policy_denied",
        "message": "Tool call is not allowed by server policy",
        "request_id": "req-central",
        "reason": "central_switch_mode_denied",
    }


@pytest.mark.asyncio
async def test_central_denied_call_does_not_leak_absolute_path() -> None:
    server = ROOTMCPServer(
        _central_config(allow_tools=["inspect_file"], require_named_resources=True)
    )

    payload = _content_payload(
        await server.handle_tool_call(
            "inspect_file",
            {"path": "/srv/private/data/file.root"},
            _central_ctx(),
        )
    )

    assert payload["error"] == "policy_denied"
    assert payload["reason"] == "raw_local_path_denied"
    assert "/srv/private/data/file.root" not in json.dumps(payload)


@pytest.mark.asyncio
async def test_central_internal_error_hides_server_paths(monkeypatch) -> None:
    server = ROOTMCPServer(_central_config(allow_tools=["list_files"]))

    def _raise_path_error(**kwargs):
        raise RuntimeError("failed under /srv/private/root-mcp")

    monkeypatch.setattr(server.discovery_tools, "list_files", _raise_path_error)

    payload = _content_payload(
        await server.handle_tool_call("list_files", {"resource": "data"}, _central_ctx())
    )

    assert payload == {
        "error": "internal_error",
        "message": "Internal server error",
        "request_id": "req-central",
    }
