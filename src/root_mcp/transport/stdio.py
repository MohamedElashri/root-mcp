"""Stdio transport runner."""

from __future__ import annotations

from typing import Any

from mcp.server.stdio import stdio_server


async def run_stdio(server: Any) -> None:
    """Run a low-level MCP server over stdio."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )
