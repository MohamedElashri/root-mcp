"""Native ROOT/PyROOT execution support (optional)."""

from .backends import (
    CentralNativeDisabledBackend,
    LocalSubprocessBackend,
    NativeExecutionBackend,
    NativeExecutionRequest,
    NativeExecutionResult,
    build_native_execution_backend,
)
from .executor import RootCodeExecutor
from .sandbox import CodeValidator, ValidationResult
from . import templates

__all__ = [
    "CentralNativeDisabledBackend",
    "CodeValidator",
    "LocalSubprocessBackend",
    "NativeExecutionBackend",
    "NativeExecutionRequest",
    "NativeExecutionResult",
    "RootCodeExecutor",
    "ValidationResult",
    "build_native_execution_backend",
    "templates",
]
