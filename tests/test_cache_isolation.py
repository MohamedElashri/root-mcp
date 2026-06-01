"""File cache isolation tests for central request contexts."""

from __future__ import annotations

from pathlib import Path

from root_mcp.config import (
    AuthConfig,
    Config,
    DeploymentConfig,
    PolicyConfig,
    ResourceConfig,
    SecurityConfig,
)
from root_mcp.core.io.file_manager import FileManager
from root_mcp.security import RequestContext


def _central_config(tmp_path: Path) -> Config:
    return Config(
        deployment=DeploymentConfig(profile="central", transport="streamable_http"),
        auth=AuthConfig(required=True, provider="external_bearer"),
        security=SecurityConfig(allowed_roots=[str(tmp_path)]),
        policy=PolicyConfig(default_tool_action="deny", allow_tools=["inspect_file"]),
        resources=[
            ResourceConfig(
                name="data",
                uri=f"file://{tmp_path}",
                allow_listing=True,
                allow_read=True,
            )
        ],
    )


def _local_config() -> Config:
    return Config()


def _ctx(principal: str, tenant: str = "tenant-a") -> RequestContext:
    return RequestContext(
        deployment_profile="central",
        transport="streamable_http",
        tenant_id=tenant,
        principal_id=principal,
        request_id=f"req-{principal}",
    )


def test_local_cache_reuses_same_path_without_identity_scope(
    tmp_path: Path,
    monkeypatch,
) -> None:
    calls: list[str] = []

    def fake_open(path, **kwargs):
        del kwargs
        calls.append(str(path))
        return object()

    monkeypatch.setattr("root_mcp.core.io.file_manager.uproot.open", fake_open)

    manager = FileManager(_local_config())
    path = tmp_path / "sample.root"

    first = manager.open(path)
    second = manager.open(path)

    assert first is second
    assert len(calls) == 1
    assert manager.get_cache_stats()["size"] == 1


def test_central_cache_is_scoped_by_principal_and_tenant(
    tmp_path: Path,
    monkeypatch,
) -> None:
    calls: list[str] = []

    def fake_open(path, **kwargs):
        del kwargs
        calls.append(str(path))
        return object()

    monkeypatch.setattr("root_mcp.core.io.file_manager.uproot.open", fake_open)

    manager = FileManager(_central_config(tmp_path))
    path = tmp_path / "sample.root"

    with manager.request_context(_ctx("alice")):
        alice_first = manager.open(path)
        alice_second = manager.open(path)

    with manager.request_context(_ctx("bob")):
        bob_first = manager.open(path)

    with manager.request_context(_ctx("alice", tenant="tenant-b")):
        tenant_b_first = manager.open(path)

    assert alice_first is alice_second
    assert bob_first is not alice_first
    assert tenant_b_first is not alice_first
    assert len(calls) == 3
    assert manager.get_cache_stats()["size"] == 3
