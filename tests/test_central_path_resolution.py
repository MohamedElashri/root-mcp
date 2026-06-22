"""Central named-resource path resolution tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from root_mcp.config import (
    AuthConfig,
    Config,
    DeploymentConfig,
    PolicyConfig,
    ResourceConfig,
    SecurityConfig,
)
from root_mcp.core.io.validators import PathValidator
from root_mcp.security import RequestContext
from root_mcp.security.resources import ResourceAccessDenied, ResourceResolver
from root_mcp.server import ROOTMCPServer


def _ctx(*, roles: set[str] | None = None) -> RequestContext:
    return RequestContext(
        deployment_profile="central",
        transport="streamable_http",
        principal_id="alice",
        roles=roles or set(),
        request_id="req-path",
    )


def _central_config(
    tmp_path: Path,
    *,
    resources: list[ResourceConfig] | None = None,
    allow_central_absolute_paths: bool = False,
    allow_tools: list[str] | None = None,
) -> Config:
    return Config(
        deployment=DeploymentConfig(profile="central", transport="streamable_http"),
        auth=AuthConfig(required=True, provider="external_bearer"),
        security=SecurityConfig(allowed_roots=[str(tmp_path)]),
        policy=PolicyConfig(
            default_tool_action="deny",
            allow_tools=allow_tools or ["inspect_file", "list_files"],
            allow_central_absolute_paths=allow_central_absolute_paths,
        ),
        resources=resources or [ResourceConfig(name="data", uri=f"file://{tmp_path}")],
    )


def _payload(content) -> dict:
    return json.loads(content[0].text)


def test_structured_resource_reference_resolves_inside_resource(tmp_path: Path) -> None:
    config = _central_config(tmp_path)
    resolver = ResourceResolver(config, PathValidator(config))

    resolved = resolver.resolve_path(
        {"resource": "data", "path": "nested/events.root"},
        _ctx(),
        "read",
    )

    assert resolved.path == tmp_path / "nested" / "events.root"
    assert resolved.reference == "@data/nested/events.root"


def test_resource_reference_rejects_path_traversal(tmp_path: Path) -> None:
    config = _central_config(tmp_path)
    resolver = ResourceResolver(config, PathValidator(config))

    with pytest.raises(ResourceAccessDenied) as exc:
        resolver.resolve_path("@data/../secret.root", _ctx(), "read")

    assert exc.value.code == "invalid_resource_reference"


@pytest.mark.asyncio
async def test_central_rejects_raw_absolute_path_by_default(tmp_path: Path) -> None:
    server = ROOTMCPServer(_central_config(tmp_path, allow_tools=["inspect_file"]))

    payload = _payload(
        await server.handle_tool_call(
            "inspect_file",
            {"path": str(tmp_path / "events.root")},
            _ctx(),
        )
    )

    assert payload["error"] == "raw_local_path_denied"
    assert str(tmp_path) not in json.dumps(payload)


def test_central_compat_absolute_path_still_must_be_inside_allowed_root(tmp_path: Path) -> None:
    config = _central_config(tmp_path, allow_central_absolute_paths=True)
    resolver = ResourceResolver(config, PathValidator(config))

    with pytest.raises(ResourceAccessDenied) as exc:
        resolver.resolve_path("/etc/passwd", _ctx(), "read")

    assert exc.value.code == "raw_local_path_denied"


def test_local_absolute_path_stays_backward_compatible(tmp_path: Path) -> None:
    config = Config()
    resolver = ResourceResolver(config, PathValidator(config))
    local_path = tmp_path / "events.root"

    resolved = resolver.resolve_path(str(local_path), None, "read")

    assert resolved.path == local_path


@pytest.mark.asyncio
async def test_central_list_files_returns_only_accessible_resource_aliases(tmp_path: Path) -> None:
    public = tmp_path / "public"
    secret = tmp_path / "secret"
    public.mkdir()
    secret.mkdir()
    (public / "open.root").write_bytes(b"")
    (secret / "hidden.root").write_bytes(b"")
    server = ROOTMCPServer(
        _central_config(
            tmp_path,
            resources=[
                ResourceConfig(name="secret", uri=f"file://{secret}", allowed_roles=["admin"]),
                ResourceConfig(name="public", uri=f"file://{public}"),
            ],
            allow_tools=["list_files"],
        )
    )

    payload = _payload(await server.handle_tool_call("list_files", {}, _ctx()))

    assert payload["metadata"]["resource"] == "public"
    assert [item["path"] for item in payload["data"]["files"]] == ["@public/open.root"]
