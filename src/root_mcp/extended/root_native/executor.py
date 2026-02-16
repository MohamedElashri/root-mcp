"""Subprocess-based PyROOT code execution engine.

Executes user-provided Python/PyROOT code in an isolated subprocess,
capturing stdout, stderr, output files, and a structured result.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .sandbox import CodeValidator, ValidationResult

logger = logging.getLogger(__name__)

# Template that wraps user code for subprocess execution
_WRAPPER_TEMPLATE = """\
import json
import os
import sys
import traceback

# Redirect working directory
os.chdir({working_dir!r})

# Make input files accessible
_input_files = {input_files!r}
_output_dir = {output_dir!r}

_result = {{
    "status": "success",
    "return_value": None,
    "output_files": [],
    "error": None,
    "traceback": None,
}}

try:
    # --- Begin user code ---
{indented_code}
    # --- End user code ---
except Exception as _exc:
    _result["status"] = "error"
    _result["error"] = str(_exc)
    _result["traceback"] = traceback.format_exc()

# Collect output files
if os.path.isdir(_output_dir):
    for _f in os.listdir(_output_dir):
        _fpath = os.path.join(_output_dir, _f)
        if os.path.isfile(_fpath):
            _result["output_files"].append(_fpath)

# Write structured result to a known file
_result_path = os.path.join({working_dir!r}, "_result.json")
with open(_result_path, "w") as _rf:
    json.dump(_result, _rf)
"""


@dataclass
class ExecutionResult:
    """Result of a PyROOT code execution."""

    status: str  # "success", "error", "timeout", "validation_failed"
    stdout: str = ""
    stderr: str = ""
    return_value: Any = None
    output_files: list[str] = field(default_factory=list)
    execution_time_seconds: float = 0.0
    error: str | None = None
    traceback: str | None = None
    validation: ValidationResult | None = None


class RootCodeExecutor:
    """Execute PyROOT code in an isolated subprocess.

    Parameters
    ----------
    execution_timeout : int
        Maximum execution time in seconds.
    max_output_size : int
        Maximum size of captured stdout/stderr in bytes.
    allowed_output_formats : list[str]
        File extensions allowed in output directory.
    working_directory : str
        Base directory for execution working dirs.
    validator : CodeValidator | None
        Code validator instance. If None, a default one is created.
    """

    def __init__(
        self,
        *,
        execution_timeout: int = 60,
        max_output_size: int = 10_000_000,
        allowed_output_formats: list[str] | None = None,
        working_directory: str = "/tmp/root_mcp_native",
        validator: CodeValidator | None = None,
    ) -> None:
        self.execution_timeout = execution_timeout
        self.max_output_size = max_output_size
        self.allowed_output_formats = allowed_output_formats or [
            "png",
            "pdf",
            "svg",
            "root",
            "json",
            "csv",
        ]
        self.working_directory = working_directory
        self.validator = validator or CodeValidator()

    def execute(
        self,
        code: str,
        *,
        input_files: list[str] | None = None,
        output_dir: str | None = None,
        timeout: int | None = None,
        skip_validation: bool = False,
    ) -> ExecutionResult:
        """Execute PyROOT code in a subprocess.

        Parameters
        ----------
        code : str
            Python code to execute (may import ROOT).
        input_files : list[str] | None
            Paths to ROOT files the code needs access to.
        output_dir : str | None
            Directory for output files. Created inside working_directory if None.
        timeout : int | None
            Override execution timeout in seconds.
        skip_validation : bool
            Skip AST validation (for trusted/internal code).

        Returns
        -------
        ExecutionResult
            Structured execution result.
        """
        effective_timeout = timeout or self.execution_timeout
        input_files = input_files or []

        # Step 1: Validate code
        if not skip_validation:
            validation = self.validator.validate(code)
            if not validation.is_valid:
                return ExecutionResult(
                    status="validation_failed",
                    error="Code validation failed: " + "; ".join(validation.errors),
                    validation=validation,
                )
        else:
            validation = None

        # Step 2: Prepare working directory
        base_dir = Path(self.working_directory)
        base_dir.mkdir(parents=True, exist_ok=True)

        work_dir = tempfile.mkdtemp(dir=base_dir, prefix="exec_")
        if output_dir is None:
            output_dir = os.path.join(work_dir, "output")
        os.makedirs(output_dir, exist_ok=True)

        # Step 3: Build wrapper script
        indented_code = "\n".join(
            "    " + line if line.strip() else "" for line in code.splitlines()
        )
        wrapper = _WRAPPER_TEMPLATE.format(
            working_dir=work_dir,
            output_dir=output_dir,
            input_files=input_files,
            indented_code=indented_code,
        )

        script_path = os.path.join(work_dir, "_runner.py")
        with open(script_path, "w") as f:
            f.write(wrapper)

        # Step 4: Execute in subprocess
        start_time = time.monotonic()
        try:
            proc = subprocess.run(
                [sys.executable, script_path],
                capture_output=True,
                text=True,
                timeout=effective_timeout,
                cwd=work_dir,
                env=self._build_env(),
            )
            elapsed = time.monotonic() - start_time

            # Truncate output if too large
            stdout = self._truncate(proc.stdout)
            stderr = self._truncate(proc.stderr)

            # Step 5: Read structured result
            result_path = os.path.join(work_dir, "_result.json")
            structured = self._read_result_file(result_path)

            return ExecutionResult(
                status=structured.get("status", "error"),
                stdout=stdout,
                stderr=stderr,
                return_value=structured.get("return_value"),
                output_files=structured.get("output_files", []),
                execution_time_seconds=round(elapsed, 3),
                error=structured.get("error"),
                traceback=structured.get("traceback"),
                validation=validation,
            )

        except subprocess.TimeoutExpired:
            elapsed = time.monotonic() - start_time
            logger.warning(
                "ROOT code execution timed out after %.1fs (limit: %ds)",
                elapsed,
                effective_timeout,
            )
            return ExecutionResult(
                status="timeout",
                execution_time_seconds=round(elapsed, 3),
                error=f"Execution timed out after {effective_timeout} seconds",
                validation=validation,
            )
        except Exception as e:
            elapsed = time.monotonic() - start_time
            logger.error("ROOT code execution failed: %s", e)
            return ExecutionResult(
                status="error",
                execution_time_seconds=round(elapsed, 3),
                error=str(e),
                validation=validation,
            )

    def _build_env(self) -> dict[str, str]:
        """Build environment variables for the subprocess."""
        env = os.environ.copy()
        # Ensure ROOT batch mode (no GUI)
        env["ROOT_BATCH"] = "1"
        return env

    def _truncate(self, text: str) -> str:
        """Truncate text to max_output_size."""
        if len(text) > self.max_output_size:
            return text[: self.max_output_size] + f"\n... [truncated, {len(text)} total bytes]"
        return text

    @staticmethod
    def _read_result_file(path: str) -> dict[str, Any]:
        """Read the structured result JSON file written by the wrapper."""
        try:
            with open(path) as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.debug("Could not read result file %s: %s", path, e)
            return {
                "status": "error",
                "error": f"Failed to read execution result: {e}",
            }
