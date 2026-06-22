"""HTTP startup validation tests."""

from __future__ import annotations

import pytest

from root_mcp.config import (
    AuthConfig,
    Config,
    DeploymentConfig,
    HTTPConfig,
    PolicyConfig,
    SecurityConfig,
)
from root_mcp.transport.http import HTTPStartupError, validate_http_startup_config


def _central_http_config(**http_kwargs: object) -> Config:
    http_values = {"origin_allowlist": ["https://client.example"], **http_kwargs}
    return Config(
        deployment=DeploymentConfig(profile="central", transport="streamable_http"),
        auth=AuthConfig(required=True, provider="external_bearer"),
        security=SecurityConfig(allowed_protocols=["root"]),
        policy=PolicyConfig(
            default_tool_action="deny",
            allow_tools=["list_files"],
            require_named_resources=True,
            disable_local_absolute_paths=True,
        ),
        http=HTTPConfig(**http_values),
    )


def test_central_http_safe_placeholder_validates() -> None:
    validate_http_startup_config(_central_http_config())


def test_http_requires_streamable_transport() -> None:
    config = _central_http_config()
    config.deployment.transport = "stdio"

    with pytest.raises(HTTPStartupError) as exc:
        validate_http_startup_config(config)

    assert "deployment.transport='streamable_http'" in str(exc.value)


def test_http_rejects_local_profile_without_explicit_flag() -> None:
    config = _central_http_config()
    config.deployment.profile = "local"

    with pytest.raises(HTTPStartupError) as exc:
        validate_http_startup_config(config)

    assert "deployment.profile='central'" in str(exc.value)


def test_http_allows_explicit_local_http_for_tests() -> None:
    config = _central_http_config(allow_local_http=True)
    config.deployment.profile = "local"

    validate_http_startup_config(config)


def test_http_requires_origin_allowlist() -> None:
    config = _central_http_config(origin_allowlist=[])

    with pytest.raises(HTTPStartupError) as exc:
        validate_http_startup_config(config)

    assert "at least one allowed Origin" in str(exc.value)


def test_http_rejects_wildcard_origin() -> None:
    config = _central_http_config(origin_allowlist=["*"])

    with pytest.raises(HTTPStartupError) as exc:
        validate_http_startup_config(config)

    assert "wildcard Origin" in str(exc.value)


def test_public_bind_requires_explicit_flag() -> None:
    config = _central_http_config(host="0.0.0.0")

    with pytest.raises(HTTPStartupError) as exc:
        validate_http_startup_config(config)

    assert "--allow-public-bind" in str(exc.value)


def test_public_bind_validates_with_explicit_flag_and_auth() -> None:
    config = _central_http_config(host="0.0.0.0", allow_public_bind=True)

    validate_http_startup_config(config)
