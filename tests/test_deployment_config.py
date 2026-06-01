"""Deployment profile configuration and validation tests."""

from __future__ import annotations

import pytest

from root_mcp.config import (
    AuthConfig,
    Config,
    DeploymentConfig,
    FeatureFlags,
    PolicyConfig,
    SecurityConfig,
    validate_deployment_config,
)


def test_local_defaults_validate() -> None:
    config = Config()

    validate_deployment_config(config)

    assert config.deployment.profile == "local"
    assert config.deployment.transport == "stdio"
    assert config.auth.required is False
    assert config.policy.default_tool_action == "allow"


def test_central_default_config_collects_unsafe_defaults() -> None:
    config = Config(deployment=DeploymentConfig(profile="central"))

    with pytest.raises(ValueError) as exc:
        validate_deployment_config(config)

    message = str(exc.value)
    assert "auth.required=true" in message
    assert "auth.provider other than 'none'" in message
    assert "transport='streamable_http'" in message
    assert "security.allowed_roots" in message
    assert "policy.allow_tools" in message


def test_central_safe_placeholder_config_validates() -> None:
    config = Config(
        deployment=DeploymentConfig(profile="central", transport="streamable_http"),
        auth=AuthConfig(required=True, provider="external_bearer", audience="root-mcp"),
        security=SecurityConfig(allowed_roots=["/data"]),
        policy=PolicyConfig(default_tool_action="deny", allow_tools=["list_files"]),
    )

    validate_deployment_config(config)


def test_central_stdio_requires_explicit_test_escape_hatch() -> None:
    config = Config(
        deployment=DeploymentConfig(profile="central", transport="stdio"),
        auth=AuthConfig(required=True, provider="external_bearer"),
        security=SecurityConfig(allowed_roots=["/data"]),
        policy=PolicyConfig(default_tool_action="deny", allow_tools=["list_files"]),
    )

    with pytest.raises(ValueError, match="transport='streamable_http'"):
        validate_deployment_config(config)

    validate_deployment_config(config, allow_central_stdio=True)


def test_central_remote_only_can_disable_local_absolute_paths() -> None:
    config = Config(
        deployment=DeploymentConfig(profile="central", transport="streamable_http"),
        auth=AuthConfig(required=True, provider="trusted_headers"),
        security=SecurityConfig(allowed_protocols=["root"]),
        policy=PolicyConfig(
            default_tool_action="deny",
            allow_tools=["list_files"],
            require_named_resources=True,
            disable_local_absolute_paths=True,
        ),
    )

    validate_deployment_config(config)


def test_central_rejects_native_root_without_isolated_executor() -> None:
    config = Config(
        deployment=DeploymentConfig(profile="central", transport="streamable_http"),
        auth=AuthConfig(required=True, provider="external_bearer"),
        security=SecurityConfig(allowed_roots=["/data"]),
        policy=PolicyConfig(default_tool_action="deny", allow_tools=["list_files"]),
        features=FeatureFlags(enable_root=True),
    )

    with pytest.raises(ValueError, match="isolated executor"):
        validate_deployment_config(config)
