"""Exercise agent-facing contracts through the SDK, including real stdio."""

from __future__ import annotations

import json
import sys

import pytest
from jsonschema import Draft202012Validator
from mcp import Client, StdioServerParameters
from mcp.shared.exceptions import MCPError

from root_mcp.config import Config, ResourceConfig, SecurityConfig
from root_mcp.protocol import SERVER_INSTRUCTIONS
from root_mcp.server import ROOTMCPServer


@pytest.mark.parametrize("mode", ["auto", "legacy"])
@pytest.mark.asyncio
async def test_stdio_discovery_and_structured_results(tmp_path, mode):
    async with Client(
        StdioServerParameters(
            command=sys.executable,
            args=["-m", "root_mcp.server", "--mode", "core", "--data-path", str(tmp_path)],
        ),
        mode=mode,
        read_timeout_seconds=15,
    ) as client:
        assert "CERN ROOT" in client.instructions
        assert client.server_info.version
        tools = await client.list_tools()
        assert "get_server_info" in {tool.name for tool in tools.tools}
        result = await client.call_tool("get_server_info", {})
        assert result.is_error is False
        assert result.structured_content == json.loads(result.content[0].text)
        assert result.structured_content["current_mode"] == "core"
        assert result.structured_content["resources"]


@pytest.mark.asyncio
async def test_catalog_resources_are_readable_json_without_storage_paths(tmp_path):
    server = ROOTMCPServer(
        Config(
            server={"mode": "core"},
            resources=[ResourceConfig(name="events", uri=f"file://{tmp_path}")],
            security=SecurityConfig(allowed_roots=[str(tmp_path)]),
        )
    )
    async with Client(server.server) as client:
        resources = await client.list_resources()
        assert resources.resources[0].mime_type == "application/json"
        result = await client.read_resource(str(resources.resources[0].uri))
        descriptor = json.loads(result.contents[0].text)
        assert descriptor["name"] == "events"
        assert descriptor["path_reference"] == "@events/relative.root"
        assert str(tmp_path) not in result.contents[0].text
        with pytest.raises(MCPError):
            await client.read_resource("root-mcp://missing")


def test_all_tool_schemas_and_side_effect_hints():
    server = ROOTMCPServer(Config())
    tools = server.list_available_tools()
    assert len(SERVER_INSTRUCTIONS) < 4096
    assert "CERN ROOT" in SERVER_INSTRUCTIONS[:512]
    for tool in tools:
        Draft202012Validator.check_schema(tool.input_schema)
        assert tool.input_schema["type"] == "object"
        assert tool.input_schema["additionalProperties"] is False
        hints = tool.annotations
        assert all(
            isinstance(getattr(hints, key), bool)
            for key in (
                "read_only_hint",
                "destructive_hint",
                "idempotent_hint",
                "open_world_hint",
            )
        )
    by_name = {tool.name: tool for tool in tools}
    assert by_name["read_branches"].annotations.read_only_hint is True
    assert by_name["read_branches"].annotations.open_world_hint is False
    assert by_name["export_data"].annotations.idempotent_hint is False
    assert by_name["export_data"].annotations.destructive_hint is True
    assert by_name["switch_mode"].annotations.read_only_hint is False
    assert by_name["switch_mode"].annotations.destructive_hint is False
    for tool in server._get_root_native_tools():
        hints = server._annotate_tool(tool).annotations
        assert hints.read_only_hint is False
        assert hints.idempotent_hint is False
        assert hints.destructive_hint is True
        assert hints.open_world_hint is True


def test_remote_file_access_is_open_world():
    server = ROOTMCPServer(
        Config(
            server={"mode": "core"},
            security=SecurityConfig(allow_remote=True, allowed_protocols=["file", "root"]),
        )
    )
    tools = {tool.name: tool for tool in server.list_available_tools()}
    assert tools["read_branches"].annotations.open_world_hint is True
    assert tools["get_server_info"].annotations.open_world_hint is False


@pytest.mark.asyncio
async def test_invalid_arguments_never_reach_dispatch(monkeypatch):
    server = ROOTMCPServer(Config(server={"mode": "core"}))

    def fail_dispatch(*args, **kwargs):
        pytest.fail("Invalid arguments reached the tool implementation")

    monkeypatch.setattr(server, "_dispatch_tool", fail_dispatch)
    async with Client(server.server) as client:
        for name, arguments in [
            ("list_files", {}),
            ("list_files", {"resource": 42}),
            ("list_files", {"resource": "data", "limit": 0}),
            ("switch_mode", {"mode": "nonexistent"}),
            ("get_server_info", {"surprise": "/private/input"}),
            (
                "read_branches",
                {
                    "path": "file.root",
                    "tree_name": "events",
                    "branches": ["pt"],
                    "entry_start": 10,
                    "entry_stop": 5,
                },
            ),
        ]:
            result = await client.call_tool(name, arguments)
            assert result.is_error is True
            assert result.structured_content["error"] == "invalid_arguments"
            assert "/private/input" not in result.content[0].text
        with pytest.raises(MCPError) as exc:
            await client.call_tool("missing_tool", {})
        assert exc.value.code == -32602


@pytest.mark.asyncio
async def test_bounded_read_options_reach_backend(monkeypatch):
    server = ROOTMCPServer(Config(server={"mode": "core"}))
    received = {}

    def read(**kwargs):
        received.update(kwargs)
        return {"data": {"pt": [1, 2]}}

    monkeypatch.setattr(server.data_access_tools, "read_branches", read)
    async with Client(server.server) as client:
        result = await client.call_tool(
            "read_branches",
            {
                "path": "file.root",
                "tree_name": "events",
                "branches": ["pt"],
                "offset": 10,
                "limit": 2,
                "flatten": True,
                "defines": {"pt": "px * 2"},
            },
        )
    assert result.is_error is False
    assert received["offset"] == 10
    assert received["limit"] == 2
    assert received["flatten"] is True
    assert received["defines"] == {"pt": "px * 2"}
