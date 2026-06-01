"""Central export path isolation tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from root_mcp.config import (
    AuthConfig,
    Config,
    DeploymentConfig,
    OutputConfig,
    PolicyConfig,
    ResourceConfig,
    SecurityConfig,
)
from root_mcp.core.io.validators import PathValidator, SecurityError
from root_mcp.security import RequestContext
from root_mcp.server import ROOTMCPServer


def _ctx() -> RequestContext:
    return RequestContext(
        deployment_profile="central",
        transport="streamable_http",
        tenant_id="tenant-a",
        principal_id="alice",
        session_id="session-1",
        request_id="req-export",
    )


def _central_config(
    tmp_path: Path,
    *,
    allow_export: bool = True,
    allow_tools: list[str] | None = None,
) -> Config:
    data_root = tmp_path / "data"
    export_root = tmp_path / "exports"
    data_root.mkdir(exist_ok=True)
    return Config(
        deployment=DeploymentConfig(profile="central", transport="streamable_http"),
        auth=AuthConfig(required=True, provider="external_bearer"),
        security=SecurityConfig(allowed_roots=[str(data_root)]),
        output=OutputConfig(export_base_path=str(export_root)),
        policy=PolicyConfig(
            default_tool_action="deny",
            allow_tools=allow_tools or ["export_data", "plot_histogram_1d"],
        ),
        resources=[
            ResourceConfig(
                name="data",
                uri=f"file://{data_root}",
                allow_export=allow_export,
            )
        ],
    )


def _payload(content) -> dict[str, Any]:
    return json.loads(content[0].text)


def test_central_output_path_is_scoped_per_caller_session(tmp_path: Path) -> None:
    config = _central_config(tmp_path)
    validator = PathValidator(config)

    resolved = validator.resolve_output_path("plots/mass.png", _ctx())

    assert resolved == (
        tmp_path / "exports" / "tenant-a" / "alice" / "session-1" / "plots" / "mass.png"
    )


def test_central_output_path_rejects_traversal(tmp_path: Path) -> None:
    config = _central_config(tmp_path)
    validator = PathValidator(config)

    with pytest.raises(SecurityError, match="path traversal"):
        validator.resolve_output_path("../escape.png", _ctx())


def test_central_output_path_rejects_absolute_paths(tmp_path: Path) -> None:
    config = _central_config(tmp_path)
    validator = PathValidator(config)

    with pytest.raises(SecurityError, match="relative artifact"):
        validator.resolve_output_path("/tmp/escape.png", _ctx())


@pytest.mark.asyncio
async def test_export_data_requires_resource_export_permission(tmp_path: Path) -> None:
    server = ROOTMCPServer(_central_config(tmp_path, allow_export=False))

    payload = _payload(
        await server.handle_tool_call(
            "export_data",
            {
                "path": "@data/events.root",
                "tree_name": "events",
                "branches": ["pt"],
                "output_path": "out.json",
                "format": "json",
            },
            _ctx(),
        )
    )

    assert payload == {
        "error": "resource_export_denied",
        "message": "Resource export is not allowed for this caller",
    }


@pytest.mark.asyncio
async def test_export_data_writes_inside_scoped_export_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    server = ROOTMCPServer(_central_config(tmp_path, allow_export=True))
    captured: dict[str, Path] = {}

    class FakeTree:
        def arrays(self, **kwargs):
            return object()

    monkeypatch.setattr(server.file_manager, "get_tree", lambda *args, **kwargs: FakeTree())

    def fake_export(data, output_path, format, **kwargs):
        captured["output_path"] = Path(output_path)
        return {"output_path": str(output_path), "format": format, "entries_written": 0}

    monkeypatch.setattr(server.data_exporter, "export", fake_export)

    payload = _payload(
        await server.handle_tool_call(
            "export_data",
            {
                "path": "@data/events.root",
                "tree_name": "events",
                "branches": ["pt"],
                "output_path": "nested/out.json",
                "format": "json",
            },
            _ctx(),
        )
    )

    expected = tmp_path / "exports" / "tenant-a" / "alice" / "session-1" / "nested" / "out.json"
    assert captured["output_path"] == expected
    assert payload["output_path"] == str(expected)
