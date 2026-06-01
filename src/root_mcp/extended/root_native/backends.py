"""Native ROOT execution backend abstractions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from root_mcp.config import Config
from root_mcp.extended.root_native.executor import ExecutionResult, RootCodeExecutor
from root_mcp.extended.root_native.sandbox import CodeValidator


@dataclass(frozen=True)
class NativeExecutionRequest:
    """One native ROOT execution request."""

    code: str
    input_files: list[str] | None = None
    output_dir: str | None = None
    timeout: int | None = None
    skip_validation: bool = False


NativeExecutionResult = ExecutionResult


class NativeExecutionBackend(Protocol):
    """Backend interface for native ROOT execution."""

    isolated: bool

    def execute(self, request: NativeExecutionRequest) -> NativeExecutionResult:
        """Execute a native ROOT request and return a structured result."""


class LocalSubprocessBackend:
    """Local-only native ROOT backend backed by ``RootCodeExecutor``."""

    isolated = False

    def __init__(self, config: Config, *, validator: CodeValidator | None = None) -> None:
        if config.deployment.profile != "local":
            raise ValueError("local_subprocess native ROOT backend is only allowed locally")

        root_cfg = config.root_native
        self.executor = RootCodeExecutor(
            execution_timeout=root_cfg.execution_timeout,
            max_output_size=root_cfg.max_output_size,
            allowed_output_formats=root_cfg.allowed_output_formats,
            working_directory=root_cfg.working_directory,
            validator=validator,
        )

    def execute(self, request: NativeExecutionRequest) -> NativeExecutionResult:
        """Execute through the local subprocess executor."""
        return self.executor.execute(
            request.code,
            input_files=request.input_files,
            output_dir=request.output_dir,
            timeout=request.timeout,
            skip_validation=request.skip_validation,
        )


class CentralNativeDisabledBackend:
    """Explicit central posture: native ROOT execution is not available."""

    isolated = False

    def execute(self, request: NativeExecutionRequest) -> NativeExecutionResult:
        """Return a structured denial result without executing user code."""
        return NativeExecutionResult(
            status="disabled",
            error=(
                "Native ROOT execution is disabled for central deployments. "
                "Configure a documented isolated backend before enabling these tools."
            ),
        )


def build_native_execution_backend(
    config: Config,
    *,
    validator: CodeValidator | None = None,
) -> NativeExecutionBackend:
    """Create the configured native ROOT execution backend."""
    backend = config.root_native.execution_backend
    if backend == "disabled":
        return CentralNativeDisabledBackend()
    if backend == "local_subprocess":
        return LocalSubprocessBackend(config, validator=validator)
    raise ValueError(f"Unsupported native ROOT execution backend: {backend}")


def central_native_execution_is_enabled(config: Config) -> bool:
    """Return whether the configured backend can run native ROOT centrally."""
    if config.deployment.profile != "central":
        return False
    if not config.features.enable_root:
        return False
    return False
