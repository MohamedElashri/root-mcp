"""Security primitives for ROOT-MCP deployment profiles."""

from root_mcp.security.audit import AuditEvent, AuditLogger, build_audit_event
from root_mcp.security.auth import AuthenticationError, AuthResult, HTTPAuthenticator
from root_mcp.security.context import RequestContext
from root_mcp.security.policy import PolicyDecision, PolicyDenied, PolicyEngine
from root_mcp.security.quotas import QuotaExceeded, QuotaManager, exported_bytes
from root_mcp.security.resources import ResolvedResourcePath, ResourceAccessDenied, ResourceResolver

__all__ = [
    "AuditEvent",
    "AuditLogger",
    "AuthResult",
    "AuthenticationError",
    "HTTPAuthenticator",
    "PolicyDecision",
    "PolicyDenied",
    "PolicyEngine",
    "QuotaExceeded",
    "QuotaManager",
    "RequestContext",
    "ResolvedResourcePath",
    "ResourceAccessDenied",
    "ResourceResolver",
    "build_audit_event",
    "exported_bytes",
]
