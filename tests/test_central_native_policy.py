"""Central native ROOT policy tests."""

from __future__ import annotations

import pytest

from root_mcp.config import (
    AuthConfig,
    Config,
    DeploymentConfig,
    FeatureFlags,
    PolicyConfig,
    RootNativeConfig,
    SecurityConfig,
    validate_deployment_config,
)
from root_mcp.security import PolicyDenied, PolicyEngine, RequestContext


def _central_config(*, enable_root: bool = False) -> Config:
    return Config(
        deployment=DeploymentConfig(profile="central", transport="streamable_http"),
        auth=AuthConfig(required=True, provider="external_bearer"),
        security=SecurityConfig(allowed_roots=["/data"]),
        policy=PolicyConfig(
            default_tool_action="deny",
            allow_tools=["list_files", "run_root_code", "run_rdataframe"],
        ),
        root_native=RootNativeConfig(execution_backend="disabled"),
        features=FeatureFlags(enable_root=enable_root),
    )


def _ctx() -> RequestContext:
    return RequestContext(
        deployment_profile="central",
        transport="streamable_http",
        request_id="req-native-central",
    )


def test_central_config_validates_when_native_root_is_disabled() -> None:
    validate_deployment_config(_central_config(enable_root=False))


def test_central_config_rejects_native_root_even_with_disabled_backend() -> None:
    with pytest.raises(ValueError, match="cannot enable native ROOT"):
        validate_deployment_config(_central_config(enable_root=True))


def test_central_policy_denies_arbitrary_native_root_code() -> None:
    engine = PolicyEngine(_central_config(enable_root=False))

    with pytest.raises(PolicyDenied) as exc:
        engine.authorize_tool_call(_ctx(), "run_root_code", {"code": "import ROOT"})

    assert exc.value.decision.code == "central_native_root_denied"


def test_central_policy_denies_templated_rdataframe_until_isolated() -> None:
    engine = PolicyEngine(_central_config(enable_root=False))

    with pytest.raises(PolicyDenied) as exc:
        engine.authorize_tool_call(
            _ctx(),
            "run_rdataframe",
            {
                "file_path": "@data/events.root",
                "tree_name": "Events",
                "branch": "pt",
                "bins": 20,
                "range_min": 0,
                "range_max": 100,
            },
        )

    assert exc.value.decision.code == "central_native_root_denied"
