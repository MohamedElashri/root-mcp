"""AST-based code validation for PyROOT code execution.

This module provides best-effort security validation for user-submitted Python
code before it is executed in a subprocess. It is NOT a hard security boundary
for untrusted code — it catches common dangerous patterns but cannot prevent
all possible exploits.
"""

from __future__ import annotations

import ast
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Modules that are blocked by default — these provide shell/OS/network access
BLOCKED_MODULES: frozenset[str] = frozenset(
    {
        "os",
        "subprocess",
        "shutil",
        "socket",
        "http",
        "urllib",
        "requests",
        "httpx",
        "aiohttp",
        "ftplib",
        "smtplib",
        "telnetlib",
        "ctypes",
        "multiprocessing",
        "signal",
        "resource",
        "pty",
        "fcntl",
        "termios",
        "webbrowser",
        "code",
        "codeop",
        "compileall",
        "importlib",
        "runpy",
        "ensurepip",
        "pip",
    }
)

# Specific attribute accesses that are blocked
BLOCKED_ATTRIBUTES: frozenset[str] = frozenset(
    {
        "system",  # os.system
        "popen",  # os.popen
        "exec",  # os.exec*
        "spawn",  # os.spawn*
        "execv",
        "execve",
        "execvp",
        "execvpe",
        "spawnl",
        "spawnle",
        "spawnlp",
        "spawnlpe",
        "spawnv",
        "spawnve",
        "spawnvp",
        "spawnvpe",
        "fork",
        "forkpty",
        "kill",
        "killpg",
        "remove",
        "unlink",
        "rmdir",
        "removedirs",
        "rmtree",
    }
)

# Built-in functions that are blocked
BLOCKED_BUILTINS: frozenset[str] = frozenset(
    {
        "exec",
        "eval",
        "compile",
        "__import__",
        "breakpoint",
    }
)

# Modules that are always allowed (safe for ROOT analysis)
ALLOWED_MODULES: frozenset[str] = frozenset(
    {
        "ROOT",
        "math",
        "cmath",
        "array",
        "json",
        "csv",
        "io",
        "sys",
        "collections",
        "itertools",
        "functools",
        "operator",
        "copy",
        "re",
        "datetime",
        "time",
        "pathlib",
        "typing",
        "dataclasses",
        "enum",
        "abc",
        "numbers",
        "decimal",
        "fractions",
        "statistics",
        "random",
        "struct",
        "textwrap",
        "string",
        "numpy",
        "scipy",
        "matplotlib",
        "awkward",
        "uproot",
        "pandas",
        "hist",
    }
)


@dataclass
class ValidationResult:
    """Result of code validation."""

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)
        self.is_valid = False

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)


class CodeValidator:
    """AST-based validator for user-submitted Python code.

    Performs static analysis to detect and block dangerous patterns before
    code is executed. This is a best-effort check, not a security sandbox.

    Parameters
    ----------
    blocked_modules : frozenset[str] | None
        Modules to block. Defaults to BLOCKED_MODULES.
    blocked_attributes : frozenset[str] | None
        Attribute names to block. Defaults to BLOCKED_ATTRIBUTES.
    blocked_builtins : frozenset[str] | None
        Built-in function names to block. Defaults to BLOCKED_BUILTINS.
    allowed_modules : frozenset[str] | None
        Modules explicitly allowed. Defaults to ALLOWED_MODULES.
    max_code_length : int
        Maximum allowed code length in characters.
    """

    def __init__(
        self,
        *,
        blocked_modules: frozenset[str] | None = None,
        blocked_attributes: frozenset[str] | None = None,
        blocked_builtins: frozenset[str] | None = None,
        allowed_modules: frozenset[str] | None = None,
        max_code_length: int = 100_000,
    ) -> None:
        self.blocked_modules = blocked_modules or BLOCKED_MODULES
        self.blocked_attributes = blocked_attributes or BLOCKED_ATTRIBUTES
        self.blocked_builtins = blocked_builtins or BLOCKED_BUILTINS
        self.allowed_modules = allowed_modules or ALLOWED_MODULES
        self.max_code_length = max_code_length

    def validate(self, code: str) -> ValidationResult:
        """Validate Python code for safety.

        Parameters
        ----------
        code : str
            The Python source code to validate.

        Returns
        -------
        ValidationResult
            Validation outcome with errors and warnings.
        """
        result = ValidationResult(is_valid=True)

        # Check code length
        if len(code) > self.max_code_length:
            result.add_error(f"Code exceeds maximum length: {len(code)} > {self.max_code_length}")
            return result

        # Check for empty code
        if not code.strip():
            result.add_error("Empty code submitted")
            return result

        # Parse AST
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            result.add_error(f"Syntax error: {e}")
            return result

        # Walk the AST and check each node
        for node in ast.walk(tree):
            self._check_imports(node, result)
            self._check_attributes(node, result)
            self._check_calls(node, result)
            self._check_open(node, result)

        return result

    def _check_imports(self, node: ast.AST, result: ValidationResult) -> None:
        """Check import statements for blocked modules."""
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_root = alias.name.split(".")[0]
                if module_root in self.blocked_modules:
                    result.add_error(
                        f"Blocked import: '{alias.name}' "
                        f"(module '{module_root}' is not allowed)"
                    )
                elif module_root not in self.allowed_modules:
                    result.add_warning(f"Unknown module: '{alias.name}' — not in allowlist")

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                module_root = node.module.split(".")[0]
                if module_root in self.blocked_modules:
                    result.add_error(
                        f"Blocked import: 'from {node.module} import ...' "
                        f"(module '{module_root}' is not allowed)"
                    )
                elif module_root not in self.allowed_modules:
                    result.add_warning(f"Unknown module: '{node.module}' — not in allowlist")

    def _check_attributes(self, node: ast.AST, result: ValidationResult) -> None:
        """Check for blocked attribute accesses."""
        if isinstance(node, ast.Attribute):
            if node.attr in self.blocked_attributes:
                result.add_error(f"Blocked attribute access: '.{node.attr}'")

    def _check_calls(self, node: ast.AST, result: ValidationResult) -> None:
        """Check for blocked built-in function calls."""
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id in self.blocked_builtins:
                    result.add_error(f"Blocked built-in call: '{node.func.id}()'")

    def _check_open(self, node: ast.AST, result: ValidationResult) -> None:
        """Check open() calls — allowed but warned about."""
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "open":
                # open() for writing output files is legitimate in ROOT scripts
                result.add_warning(
                    "Code uses open() — file access is allowed but limited "
                    "to the working directory at runtime"
                )
