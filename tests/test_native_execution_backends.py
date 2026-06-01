"""Native ROOT execution backend tests."""

from __future__ import annotations

import tempfile

import pytest

from root_mcp.config import Config, DeploymentConfig, RootNativeConfig
from root_mcp.extended.root_native.backends import (
    CentralNativeDisabledBackend,
    LocalSubprocessBackend,
    NativeExecutionRequest,
    build_native_execution_backend,
)


def test_local_subprocess_backend_executes_python_code() -> None:
    work_dir = tempfile.mkdtemp(prefix="test_native_backend_")
    config = Config(root_native=RootNativeConfig(working_directory=work_dir))

    backend = build_native_execution_backend(config)
    result = backend.execute(NativeExecutionRequest(code="print('backend ok')"))

    assert isinstance(backend, LocalSubprocessBackend)
    assert result.status == "success"
    assert "backend ok" in result.stdout


def test_local_subprocess_backend_rejects_central_profile() -> None:
    config = Config(deployment=DeploymentConfig(profile="central", transport="streamable_http"))

    with pytest.raises(ValueError, match="only allowed locally"):
        LocalSubprocessBackend(config)


def test_disabled_backend_never_executes_code() -> None:
    backend = CentralNativeDisabledBackend()

    result = backend.execute(NativeExecutionRequest(code="raise RuntimeError('boom')"))

    assert result.status == "disabled"
    assert "disabled for central deployments" in (result.error or "")


def test_disabled_backend_can_be_selected_in_config() -> None:
    config = Config(root_native=RootNativeConfig(execution_backend="disabled"))

    backend = build_native_execution_backend(config)
    result = backend.execute(NativeExecutionRequest(code="print('not executed')"))

    assert isinstance(backend, CentralNativeDisabledBackend)
    assert result.status == "disabled"
