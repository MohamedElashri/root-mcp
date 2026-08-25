"""Policy engine tests for deployment-profile tool authorization."""

from __future__ import annotations

import pytest
from mcp.types import Tool

from root_mcp.config import Config, DeploymentConfig, PolicyConfig
from root_mcp.security import PolicyDenied, PolicyEngine, RequestContext


def _ctx(profile: str = "local") -> RequestContext:
    return RequestContext(
        deployment_profile=profile,
        transport="streamable_http" if profile == "central" else "stdio",
        request_id="req-test",
    )


def _tool(name: str) -> Tool:
    return Tool(name=name, description=f"{name} tool", input_schema={"type": "object"})


def test_local_default_allows_tools() -> None:
    engine = PolicyEngine(Config())

    decision = engine.authorize_tool_call(_ctx(), "switch_mode", {"mode": "core"})

    assert decision.allowed is True


def test_deny_list_wins_over_allow_list() -> None:
    engine = PolicyEngine(
        Config(
            policy=PolicyConfig(
                default_tool_action="allow",
                allow_tools=["list_files"],
                deny_tools=["list_files"],
            )
        )
    )

    with pytest.raises(PolicyDenied) as exc:
        engine.authorize_tool_call(_ctx(), "list_files", {"resource": "data"})

    assert exc.value.decision.code == "tool_denied"


def test_central_requires_explicit_allow_list() -> None:
    engine = PolicyEngine(
        Config(
            deployment=DeploymentConfig(profile="central", transport="streamable_http"),
            policy=PolicyConfig(default_tool_action="allow", allow_tools=["list_files"]),
        )
    )

    with pytest.raises(PolicyDenied) as exc:
        engine.authorize_tool_call(_ctx("central"), "inspect_file", {"path": "@data/a.root"})

    assert exc.value.decision.code == "tool_not_allowed"


def test_central_denies_switch_mode_even_when_allow_listed() -> None:
    engine = PolicyEngine(
        Config(
            deployment=DeploymentConfig(profile="central", transport="streamable_http"),
            policy=PolicyConfig(default_tool_action="deny", allow_tools=["switch_mode"]),
        )
    )

    with pytest.raises(PolicyDenied) as exc:
        engine.authorize_tool_call(_ctx("central"), "switch_mode", {"mode": "core"})

    assert exc.value.decision.code == "central_switch_mode_denied"


def test_central_denies_native_root_without_isolated_executor() -> None:
    engine = PolicyEngine(
        Config(
            deployment=DeploymentConfig(profile="central", transport="streamable_http"),
            policy=PolicyConfig(default_tool_action="deny", allow_tools=["run_root_code"]),
        )
    )

    with pytest.raises(PolicyDenied) as exc:
        engine.authorize_tool_call(_ctx("central"), "run_root_code", {"code": "import ROOT"})

    assert exc.value.decision.code == "central_native_root_denied"


def test_named_resource_policy_rejects_absolute_paths() -> None:
    engine = PolicyEngine(
        Config(
            policy=PolicyConfig(
                default_tool_action="allow",
                require_named_resources=True,
            )
        )
    )

    with pytest.raises(PolicyDenied) as exc:
        engine.authorize_tool_call(_ctx(), "inspect_file", {"path": "/data/file.root"})

    assert exc.value.decision.code == "raw_local_path_denied"


def test_named_resource_policy_allows_resource_alias() -> None:
    engine = PolicyEngine(
        Config(
            policy=PolicyConfig(
                default_tool_action="allow",
                require_named_resources=True,
            )
        )
    )

    decision = engine.authorize_tool_call(_ctx(), "inspect_file", {"path": "@data/file.root"})

    assert decision.allowed is True


def test_filter_tools_hides_policy_denied_tools() -> None:
    engine = PolicyEngine(
        Config(
            deployment=DeploymentConfig(profile="central", transport="streamable_http"),
            policy=PolicyConfig(
                default_tool_action="deny", allow_tools=["list_files", "switch_mode"]
            ),
        )
    )

    visible = engine.filter_tools(_ctx("central"), [_tool("list_files"), _tool("switch_mode")])

    assert [tool.name for tool in visible] == ["list_files"]
