"""MCP tool for executing native ROOT/PyROOT code."""

from __future__ import annotations

import logging
from typing import Any

from root_mcp.config import Config
from root_mcp.extended.root_native.executor import RootCodeExecutor
from root_mcp.extended.root_native.sandbox import CodeValidator
from root_mcp.extended.root_native import templates

logger = logging.getLogger(__name__)


class RootNativeTools:
    """MCP tool handler for native ROOT/PyROOT code execution.

    This tool is only registered when both:
    - config.features.enable_root is True
    - Native ROOT/PyROOT is detected as available

    Parameters
    ----------
    config : Config
        Server configuration.
    """

    def __init__(self, config: Config) -> None:
        self.config = config
        root_cfg = config.root_native

        self.validator = CodeValidator(
            max_code_length=root_cfg.max_code_length,
        )
        self.executor = RootCodeExecutor(
            execution_timeout=root_cfg.execution_timeout,
            max_output_size=root_cfg.max_output_size,
            allowed_output_formats=root_cfg.allowed_output_formats,
            working_directory=root_cfg.working_directory,
            validator=self.validator,
        )

    def run_root_code(
        self,
        code: str,
        output_dir: str | None = None,
        timeout: int | None = None,
        input_files: list[str] | None = None,
    ) -> dict[str, Any]:
        """Execute PyROOT/Python code and return structured results.

        Parameters
        ----------
        code : str
            Python code to execute (may import ROOT).
        output_dir : str | None
            Directory for output files (optional).
        timeout : int | None
            Execution timeout in seconds (optional, overrides config default).
        input_files : list[str] | None
            Paths to ROOT files the code needs access to.

        Returns
        -------
        dict
            Structured result with status, stdout, stderr, output_files, etc.
        """
        logger.info("Executing run_root_code (code length: %d chars)", len(code))

        result = self.executor.execute(
            code,
            input_files=input_files,
            output_dir=output_dir,
            timeout=timeout,
        )

        # Convert ExecutionResult to dict for JSON serialization
        response: dict[str, Any] = {
            "status": result.status,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_value": result.return_value,
            "output_files": result.output_files,
            "execution_time_seconds": result.execution_time_seconds,
        }

        if result.error:
            response["error"] = result.error
        if result.traceback:
            response["traceback"] = result.traceback
        if result.validation and result.validation.warnings:
            response["warnings"] = result.validation.warnings

        return response

    def run_rdataframe(
        self,
        file_path: str,
        tree_name: str,
        branch: str,
        bins: int,
        range_min: float,
        range_max: float,
        selection: str | None = None,
        weight: str | None = None,
        output_path: str | None = None,
        timeout: int | None = None,
    ) -> dict[str, Any]:
        """Compute a 1D histogram using RDataFrame.

        This is a convenience wrapper around run_root_code that generates
        RDataFrame code from parameters, avoiding the need to write PyROOT
        boilerplate.

        Parameters
        ----------
        file_path : str
            Path to the ROOT file.
        tree_name : str
            Name of the TTree.
        branch : str
            Branch to histogram.
        bins : int
            Number of bins.
        range_min, range_max : float
            Histogram range.
        selection : str | None
            Optional cut expression (C++ syntax).
        weight : str | None
            Optional weight column name.
        output_path : str | None
            If provided, save histogram plot to this path.
        timeout : int | None
            Execution timeout in seconds.

        Returns
        -------
        dict
            Structured result with histogram data.
        """
        logger.info(
            "Executing run_rdataframe: %s:%s/%s [%d bins]",
            file_path,
            tree_name,
            branch,
            bins,
        )

        code = templates.rdataframe_histogram(
            file_path=file_path,
            tree_name=tree_name,
            branch=branch,
            bins=bins,
            range_min=range_min,
            range_max=range_max,
            selection=selection,
            weight=weight,
            output_path=output_path,
        )

        return self._execute_template(code, timeout=timeout)

    def run_root_macro(
        self,
        macro_code: str,
        output_path: str | None = None,
        timeout: int | None = None,
    ) -> dict[str, Any]:
        """Execute a ROOT C++ macro via gROOT.ProcessLine.

        Parameters
        ----------
        macro_code : str
            C++ code to execute.
        output_path : str | None
            If provided, save any canvas output to this path.
        timeout : int | None
            Execution timeout in seconds.

        Returns
        -------
        dict
            Structured result.
        """
        logger.info("Executing run_root_macro (code length: %d chars)", len(macro_code))

        code = templates.root_macro(
            macro_code=macro_code,
            output_path=output_path,
        )

        return self._execute_template(code, timeout=timeout)

    def _execute_template(
        self,
        code: str,
        *,
        timeout: int | None = None,
    ) -> dict[str, Any]:
        """Execute template-generated code, skipping AST validation.

        Template-generated code is trusted (we wrote it), so we skip
        the sandbox validation to avoid false positives from the templates
        using constructs like json.dumps internally.
        """
        result = self.executor.execute(
            code,
            timeout=timeout,
            skip_validation=True,
        )

        response: dict[str, Any] = {
            "status": result.status,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_value": result.return_value,
            "output_files": result.output_files,
            "execution_time_seconds": result.execution_time_seconds,
        }

        if result.error:
            response["error"] = result.error
        if result.traceback:
            response["traceback"] = result.traceback

        return response
