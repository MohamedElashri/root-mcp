"""Common error types for ROOT-MCP."""


class ROOTMCPError(Exception):
    """Base exception for ROOT-MCP errors."""

    pass


class SecurityError(ROOTMCPError):
    """Raised when a security constraint is violated."""

    pass


class ValidationError(ROOTMCPError):
    """Raised when validation fails."""

    pass


class FileOperationError(ROOTMCPError):
    """Raised when file operations fail."""

    pass


class AnalysisError(ROOTMCPError):
    """Raised when analysis operations fail."""

    pass
