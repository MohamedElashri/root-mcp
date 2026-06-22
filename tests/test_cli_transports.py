"""CLI transport command tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from root_mcp import server as server_module


def _write_config(path: Path, *, central: bool = False) -> None:
    if central:
        path.write_text("""
deployment:
  profile: central
  transport: stdio
auth:
  required: true
  provider: external_bearer
security:
  allowed_protocols: ["root"]
policy:
  default_tool_action: deny
  allow_tools: ["list_files"]
  require_named_resources: true
  disable_local_absolute_paths: true
http:
  origin_allowlist: ["https://client.example"]
""".lstrip())
        return

    path.write_text("""
deployment:
  profile: local
  transport: streamable_http
""".lstrip())


def test_extract_server_command_defaults_to_stdio() -> None:
    command, argv = server_module._extract_server_command(["--data-path", "/data"])

    assert command == "serve-stdio-default"
    assert argv == ["--data-path", "/data"]


def test_extract_server_command_handles_explicit_transports() -> None:
    assert server_module._extract_server_command(["serve-stdio", "--mode", "core"]) == (
        "serve-stdio",
        ["--mode", "core"],
    )
    assert server_module._extract_server_command(["serve-http", "--host", "127.0.0.1"]) == (
        "serve-http",
        ["--host", "127.0.0.1"],
    )


def test_serve_stdio_forces_stdio_transport(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config_path = tmp_path / "config.yaml"
    _write_config(config_path)
    seen: dict[str, object] = {}

    class FakeServer:
        def __init__(self, config):
            seen["transport"] = config.deployment.transport

        async def run(self) -> None:
            seen["ran"] = True

    monkeypatch.setattr(server_module, "ROOTMCPServer", FakeServer)
    monkeypatch.setattr(sys, "argv", ["root-mcp", "serve-stdio", "--config", str(config_path)])

    server_module.main()

    assert seen == {"transport": "stdio", "ran": True}


def test_serve_http_forces_streamable_http_and_applies_flags(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "config.yaml"
    _write_config(config_path, central=True)
    seen: dict[str, object] = {}

    class FakeServer:
        def __init__(self, config):
            self.config = config

    async def fake_run_http(server) -> None:
        config = server.config
        seen["transport"] = config.deployment.transport
        seen["host"] = config.http.host
        seen["port"] = config.http.port
        seen["endpoint"] = config.http.endpoint
        seen["origins"] = config.http.origin_allowlist

    monkeypatch.setattr(server_module, "ROOTMCPServer", FakeServer)
    monkeypatch.setattr(server_module, "run_http", fake_run_http)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "root-mcp",
            "serve-http",
            "--config",
            str(config_path),
            "--host",
            "127.0.0.1",
            "--port",
            "9000",
            "--endpoint",
            "/root-mcp",
            "--origin",
            "https://other.example",
        ],
    )

    server_module.main()

    assert seen == {
        "transport": "streamable_http",
        "host": "127.0.0.1",
        "port": 9000,
        "endpoint": "/root-mcp",
        "origins": ["https://other.example"],
    }


def test_serve_http_rejects_stdio_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["root-mcp", "serve-http", "--transport", "stdio"])

    with pytest.raises(SystemExit) as exc:
        server_module.main()

    assert exc.value.code == 2
