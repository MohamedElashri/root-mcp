#!/usr/bin/env python3
"""External-process Streamable HTTP smoke test for ROOT-MCP.

The script starts ``root-mcp serve-http`` as a subprocess, connects with the
official MCP Streamable HTTP client, initializes the session, lists tools, and
calls ``get_server_info``. It uses trusted-header auth from localhost and a
temporary restrictive central config.
"""

from __future__ import annotations

import argparse
import asyncio
from contextlib import suppress
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import textwrap
import time

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_port(port: int, *, timeout: float = 10.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with socket.socket() as sock:
            sock.settimeout(0.25)
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(0.1)
    raise TimeoutError(f"Timed out waiting for root-mcp HTTP server on port {port}")


def _write_config(path: Path, port: int, origin: str) -> None:
    path.write_text(
        textwrap.dedent(f"""\
            server:
              mode: "core"

            deployment:
              profile: "central"
              transport: "streamable_http"
              fixed_analysis_tier: true

            auth:
              required: true
              provider: "trusted_headers"
              trusted_principal_header: "x-auth-principal"
              trusted_tenant_header: "x-auth-tenant"
              trusted_roles_header: "x-auth-roles"
              trusted_scopes_header: "x-auth-scopes"
              trusted_proxy_networks: ["127.0.0.0/8", "::1/128"]

            policy:
              default_tool_action: "deny"
              allow_tools: ["get_server_info"]
              deny_tools:
                - switch_mode
                - run_root_code
                - run_rdataframe
                - run_root_macro
              require_named_resources: true
              disable_local_absolute_paths: true
              allow_central_absolute_paths: false

            http:
              host: "127.0.0.1"
              port: {port}
              endpoint: "/mcp"
              origin_allowlist: ["{origin}"]
              require_origin_header: true

            security:
              allowed_roots: []
              allow_remote: true
              allowed_protocols: ["root"]

            features:
              enable_export: false
              enable_root: false

            root_native:
              execution_backend: "disabled"
            """),
        encoding="utf-8",
    )


async def _run_client(port: int, origin: str) -> None:
    headers = {
        "Origin": origin,
        "x-auth-principal": "smoke-user",
        "x-auth-tenant": "smoke-tenant",
        "x-auth-roles": "smoke-reader",
        "Accept": "application/json, text/event-stream",
    }
    async with streamablehttp_client(f"http://127.0.0.1:{port}/mcp", headers=headers) as (
        read_stream,
        write_stream,
        _get_session_id,
    ):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tools = await session.list_tools()
            tool_names = {tool.name for tool in tools.tools}
            if "get_server_info" not in tool_names:
                raise RuntimeError(f"get_server_info missing from advertised tools: {tool_names}")

            result = await session.call_tool("get_server_info", {})
            if not result.content:
                raise RuntimeError("get_server_info returned no content")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--port", type=int, default=0, help="HTTP port, default chooses a free port"
    )
    parser.add_argument(
        "--origin",
        default="https://smoke.example",
        help="Origin to configure and send with the smoke client",
    )
    args = parser.parse_args()

    port = args.port or _free_port()
    with tempfile.TemporaryDirectory(prefix="root-mcp-smoke-") as tmp:
        config_path = Path(tmp) / "central-smoke.yaml"
        _write_config(config_path, port, args.origin)
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "root_mcp.server",
                "serve-http",
                "--config",
                str(config_path),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            _wait_for_port(port)
            asyncio.run(_run_client(port, args.origin))
            print(f"external HTTP MCP smoke passed on http://127.0.0.1:{port}/mcp")
        finally:
            process.terminate()
            with suppress(subprocess.TimeoutExpired):
                process.wait(timeout=5)
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
            if process.returncode not in {0, -15, -9}:
                stderr = process.stderr.read() if process.stderr else ""
                raise SystemExit(f"root-mcp server exited with {process.returncode}\n{stderr}")


if __name__ == "__main__":
    main()
