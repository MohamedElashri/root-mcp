"""Tests for the sandboxed PyROOT code execution engine."""

from __future__ import annotations

import os
import tempfile

import pytest

from root_mcp.extended.root_native.sandbox import (
    CodeValidator,
    ValidationResult,
)
from root_mcp.extended.root_native.executor import RootCodeExecutor, ExecutionResult
from root_mcp.config import Config, RootNativeConfig

# ---------------------------------------------------------------------------
# Sandbox / CodeValidator tests
# ---------------------------------------------------------------------------


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_starts_valid(self):
        result = ValidationResult(is_valid=True)
        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []

    def test_add_error_invalidates(self):
        result = ValidationResult(is_valid=True)
        result.add_error("bad thing")
        assert result.is_valid is False
        assert "bad thing" in result.errors

    def test_add_warning_keeps_valid(self):
        result = ValidationResult(is_valid=True)
        result.add_warning("heads up")
        assert result.is_valid is True
        assert "heads up" in result.warnings


class TestCodeValidatorImports:
    """Tests for import validation."""

    def setup_method(self):
        self.validator = CodeValidator()

    def test_allows_root_import(self):
        result = self.validator.validate("import ROOT")
        assert result.is_valid is True

    def test_allows_numpy_import(self):
        result = self.validator.validate("import numpy as np")
        assert result.is_valid is True

    def test_allows_matplotlib_import(self):
        result = self.validator.validate("from matplotlib import pyplot as plt")
        assert result.is_valid is True

    def test_blocks_os_import(self):
        result = self.validator.validate("import os")
        assert result.is_valid is False
        assert any("os" in e for e in result.errors)

    def test_blocks_subprocess_import(self):
        result = self.validator.validate("import subprocess")
        assert result.is_valid is False

    def test_blocks_shutil_import(self):
        result = self.validator.validate("import shutil")
        assert result.is_valid is False

    def test_blocks_socket_import(self):
        result = self.validator.validate("import socket")
        assert result.is_valid is False

    def test_blocks_from_os_import(self):
        result = self.validator.validate("from os import path")
        assert result.is_valid is False

    def test_blocks_from_subprocess_import(self):
        result = self.validator.validate("from subprocess import run")
        assert result.is_valid is False

    def test_blocks_requests_import(self):
        result = self.validator.validate("import requests")
        assert result.is_valid is False

    def test_blocks_ctypes_import(self):
        result = self.validator.validate("import ctypes")
        assert result.is_valid is False

    def test_warns_unknown_module(self):
        result = self.validator.validate("import some_unknown_module")
        assert result.is_valid is True  # warnings don't block
        assert len(result.warnings) > 0

    def test_allows_scipy_submodule(self):
        result = self.validator.validate("from scipy.optimize import curve_fit")
        assert result.is_valid is True

    def test_blocks_http_import(self):
        result = self.validator.validate("import http.server")
        assert result.is_valid is False


class TestCodeValidatorAttributes:
    """Tests for blocked attribute access."""

    def setup_method(self):
        self.validator = CodeValidator()

    def test_blocks_system_attr(self):
        result = self.validator.validate("x.system('ls')")
        assert result.is_valid is False

    def test_blocks_popen_attr(self):
        result = self.validator.validate("x.popen('cmd')")
        assert result.is_valid is False

    def test_blocks_remove_attr(self):
        result = self.validator.validate("x.remove('file')")
        assert result.is_valid is False

    def test_blocks_rmtree_attr(self):
        result = self.validator.validate("x.rmtree('/path')")
        assert result.is_valid is False

    def test_blocks_kill_attr(self):
        result = self.validator.validate("x.kill()")
        assert result.is_valid is False

    def test_allows_normal_attrs(self):
        result = self.validator.validate("h.GetMean()")
        assert result.is_valid is True


class TestCodeValidatorBuiltins:
    """Tests for blocked built-in calls."""

    def setup_method(self):
        self.validator = CodeValidator()

    def test_blocks_exec(self):
        result = self.validator.validate("exec('print(1)')")
        assert result.is_valid is False

    def test_blocks_eval(self):
        result = self.validator.validate("eval('1+1')")
        assert result.is_valid is False

    def test_blocks_compile(self):
        result = self.validator.validate("compile('x', 'f', 'exec')")
        assert result.is_valid is False

    def test_blocks___import__(self):
        result = self.validator.validate("__import__('os')")
        assert result.is_valid is False

    def test_allows_print(self):
        result = self.validator.validate("print('hello')")
        assert result.is_valid is True

    def test_allows_len(self):
        result = self.validator.validate("len([1, 2, 3])")
        assert result.is_valid is True


class TestCodeValidatorEdgeCases:
    """Tests for edge cases in validation."""

    def setup_method(self):
        self.validator = CodeValidator()

    def test_empty_code(self):
        result = self.validator.validate("")
        assert result.is_valid is False

    def test_whitespace_only(self):
        result = self.validator.validate("   \n\n  ")
        assert result.is_valid is False

    def test_syntax_error(self):
        result = self.validator.validate("def foo(:")
        assert result.is_valid is False
        assert any("Syntax error" in e for e in result.errors)

    def test_code_too_long(self):
        validator = CodeValidator(max_code_length=100)
        result = validator.validate("x = 1\n" * 100)
        assert result.is_valid is False
        assert any("maximum length" in e for e in result.errors)

    def test_open_warning(self):
        result = self.validator.validate("f = open('output.txt', 'w')")
        assert result.is_valid is True
        assert len(result.warnings) > 0

    def test_multiline_valid_code(self):
        code = """
import ROOT
import numpy as np

h = ROOT.TH1F("h", "test", 100, -5, 5)
h.FillRandom("gaus", 10000)
print(h.GetMean(), h.GetRMS())
"""
        result = self.validator.validate(code)
        assert result.is_valid is True

    def test_multiple_blocked_items(self):
        code = """
import os
import subprocess
exec('bad')
"""
        result = self.validator.validate(code)
        assert result.is_valid is False
        assert len(result.errors) >= 3


# ---------------------------------------------------------------------------
# Executor tests
# ---------------------------------------------------------------------------


class TestRootCodeExecutor:
    """Tests for the subprocess-based code executor."""

    def setup_method(self):
        self.work_dir = tempfile.mkdtemp(prefix="test_root_exec_")
        self.executor = RootCodeExecutor(
            execution_timeout=10,
            working_directory=self.work_dir,
        )

    def test_execute_simple_print(self):
        """Execute simple Python code that prints output."""
        result = self.executor.execute("print('hello from executor')")
        assert result.status == "success"
        assert "hello from executor" in result.stdout
        assert result.execution_time_seconds > 0

    def test_execute_math(self):
        """Execute code that does math."""
        code = """
import math
result = math.sqrt(144)
print(f"result={result}")
"""
        result = self.executor.execute(code)
        assert result.status == "success"
        assert "result=12.0" in result.stdout

    def test_execute_validation_failure(self):
        """Code that fails validation should not execute."""
        code = "import os\nos.system('rm -rf /')"
        result = self.executor.execute(code)
        assert result.status == "validation_failed"
        assert result.error is not None
        assert "validation failed" in result.error.lower()

    def test_execute_skip_validation(self):
        """skip_validation=True should bypass the validator."""
        # This code would fail validation but should run with skip
        code = "print('ran successfully')"
        result = self.executor.execute(code, skip_validation=True)
        assert result.status == "success"
        assert "ran successfully" in result.stdout

    def test_execute_runtime_error(self):
        """Code with a runtime error should report error status."""
        code = "x = 1 / 0"
        result = self.executor.execute(code)
        assert result.status == "error"
        assert result.error is not None
        assert "ZeroDivisionError" in (result.traceback or "")

    def test_execute_timeout(self):
        """Code that exceeds timeout should be killed."""
        executor = RootCodeExecutor(
            execution_timeout=2,
            working_directory=self.work_dir,
        )
        code = """
import time
time.sleep(30)
"""
        result = executor.execute(code)
        assert result.status == "timeout"
        assert result.error is not None

    def test_execute_output_files(self):
        """Code that writes files should report them."""
        code = """
import json
output_path = _output_dir + "/test_output.json"
with open(output_path, "w") as f:
    json.dump({"key": "value"}, f)
"""
        result = self.executor.execute(code)
        assert result.status == "success"
        assert len(result.output_files) > 0
        assert any("test_output.json" in f for f in result.output_files)

    def test_execute_captures_stderr(self):
        """Stderr output should be captured."""
        code = """
import sys
print("error message", file=sys.stderr)
"""
        result = self.executor.execute(code)
        assert result.status == "success"
        assert "error message" in result.stderr

    def test_execute_with_timeout_override(self):
        """Timeout parameter should override default."""
        code = "print('fast')"
        result = self.executor.execute(code, timeout=5)
        assert result.status == "success"

    def test_execute_creates_working_dir(self):
        """Executor should create working directory if it doesn't exist."""
        new_dir = os.path.join(self.work_dir, "new_subdir")
        executor = RootCodeExecutor(working_directory=new_dir)
        result = executor.execute("print('ok')")
        assert result.status == "success"
        assert os.path.isdir(new_dir)

    def test_execution_result_dataclass(self):
        """ExecutionResult should have all expected fields."""
        result = ExecutionResult(status="success")
        assert result.status == "success"
        assert result.stdout == ""
        assert result.stderr == ""
        assert result.return_value is None
        assert result.output_files == []
        assert result.execution_time_seconds == 0.0
        assert result.error is None
        assert result.traceback is None
        assert result.validation is None


class TestRootNativeConfig:
    """Tests for RootNativeConfig in the Config model."""

    def test_default_config(self):
        config = Config()
        assert config.root_native.execution_timeout == 60
        assert config.root_native.max_output_size == 10_000_000
        assert config.root_native.working_directory == "/tmp/root_mcp_native"
        assert config.root_native.max_code_length == 100_000
        assert "png" in config.root_native.allowed_output_formats
        assert "root" in config.root_native.allowed_output_formats

    def test_custom_config(self):
        config = Config(
            root_native=RootNativeConfig(
                execution_timeout=120,
                max_output_size=5_000_000,
                working_directory="/custom/path",
            )
        )
        assert config.root_native.execution_timeout == 120
        assert config.root_native.max_output_size == 5_000_000
        assert config.root_native.working_directory == "/custom/path"

    def test_invalid_timeout(self):
        with pytest.raises(Exception):
            RootNativeConfig(execution_timeout=0)

    def test_invalid_max_output_size(self):
        with pytest.raises(Exception):
            RootNativeConfig(max_output_size=-1)
