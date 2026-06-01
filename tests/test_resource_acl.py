"""Resource ACL tests for central deployment path access."""

from __future__ import annotations

from pathlib import Path

import pytest

from root_mcp.config import Config, DeploymentConfig, PolicyConfig, ResourceConfig, SecurityConfig
from root_mcp.core.io.validators import PathValidator
from root_mcp.security import RequestContext
from root_mcp.security.resources import ResourceAccessDenied, ResourceResolver


def _ctx(*, roles: set[str] | None = None, principal: str = "alice") -> RequestContext:
    return RequestContext(
        deployment_profile="central",
        transport="streamable_http",
        principal_id=principal,
        roles=roles or set(),
        request_id="req-acl",
    )


def _resolver(tmp_path: Path, resource: ResourceConfig) -> ResourceResolver:
    config = Config(
        deployment=DeploymentConfig(profile="central", transport="streamable_http"),
        security=SecurityConfig(allowed_roots=[str(tmp_path)]),
        policy=PolicyConfig(default_tool_action="deny", allow_tools=["inspect_file"]),
        resources=[resource],
    )
    return ResourceResolver(config, PathValidator(config))


def test_resource_role_acl_denies_unmatched_caller(tmp_path: Path) -> None:
    resource = ResourceConfig(
        name="cms",
        uri=f"file://{tmp_path}",
        allowed_roles=["cms-reader"],
    )
    resolver = _resolver(tmp_path, resource)

    with pytest.raises(ResourceAccessDenied) as exc:
        resolver.resolve_path("@cms/events.root", _ctx(), "read")

    assert exc.value.code == "resource_acl_denied"


def test_resource_role_acl_allows_matching_role(tmp_path: Path) -> None:
    resource = ResourceConfig(
        name="cms",
        uri=f"file://{tmp_path}",
        allowed_roles=["cms-reader"],
    )
    resolver = _resolver(tmp_path, resource)

    resolved = resolver.resolve_path("@cms/events.root", _ctx(roles={"cms-reader"}), "read")

    assert resolved.path == tmp_path / "events.root"
    assert resolved.reference == "@cms/events.root"


def test_resource_export_requires_export_permission(tmp_path: Path) -> None:
    resource = ResourceConfig(name="cms", uri=f"file://{tmp_path}", allow_export=False)
    resolver = _resolver(tmp_path, resource)

    with pytest.raises(ResourceAccessDenied) as exc:
        resolver.resolve_path({"resource": "cms", "path": "events.root"}, _ctx(), "export")

    assert exc.value.code == "resource_export_denied"


def test_resource_listing_flag_hides_resource(tmp_path: Path) -> None:
    resource = ResourceConfig(name="hidden", uri=f"file://{tmp_path}", allow_listing=False)
    resolver = _resolver(tmp_path, resource)

    assert resolver.accessible_resources(_ctx(), "listing") == []
