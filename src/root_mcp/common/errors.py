"""Common error types for ROOT-MCP."""


class ROOTMCPError(Exception):
    """Base exception for ROOT-MCP errors."""


class SecurityError(ROOTMCPError):
    """Raised when a security constraint is violated."""


class ValidationError(ROOTMCPError):
    """Raised when validation fails."""


class FileOperationError(ROOTMCPError):
    """Raised when file operations fail."""


class AnalysisError(ROOTMCPError):
    """Raised when analysis operations fail."""
