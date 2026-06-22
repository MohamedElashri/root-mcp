"""Tool authorization and coarse resource policy enforcement."""

from __future__ import annotations

from pathlib import PurePosixPath, PureWindowsPath
from typing import Any
from urllib.parse import urlparse

from mcp.types import Tool
from pydantic import BaseModel

from root_mcp.config import Config
from root_mcp.security.context import RequestContext

NATIVE_ROOT_TOOLS = frozenset({"run_root_code", "run_rdataframe", "run_root_macro"})
EXPORT_TOOLS = frozenset({"export_data", "plot_histogram_1d", "plot_histogram_2d"})


class PolicyDecision(BaseModel):
    """Authorization outcome for a tool call or advertised tool."""

    allowed: bool
    code: str = "allowed"
    message: str = "Tool call is allowed"
    detail: str | None = None


class PolicyDenied(Exception):
    """Raised when server policy denies a tool call."""

    def __init__(self, decision: PolicyDecision):
        super().__init__(decision.message)
        self.decision = decision

    def to_error(self, request_id: str, *, debug: bool = False) -> dict[str, Any]:
        """Return the central-safe policy error shape sent to clients."""
        error = {
            "error": "policy_denied",
            "message": self.decision.message,
            "request_id": request_id,
            "reason": self.decision.code,
        }
        if debug and self.decision.detail:
            error["detail"] = self.decision.detail
        return error


class PolicyEngine:
    """Authorize ROOT-MCP tools against deployment and policy configuration."""

    def __init__(self, config: Config, *, isolated_executor_available: bool = False):
        self.config = config
        self.isolated_executor_available = isolated_executor_available

    def authorize_tool_call(
        self,
        ctx: RequestContext,
        name: str,
        arguments: dict[str, Any] | None = None,
    ) -> PolicyDecision:
        """Authorize one tool call and raise :class:`PolicyDenied` on denial."""
        decision = self._decide(ctx, name, arguments or {})
        if not decision.allowed:
            raise PolicyDenied(decision)
        return decision

    def filter_tools(self, ctx: RequestContext, tools: list[Tool]) -> list[Tool]:
        """Return only tools visible to this request context."""
        visible: list[Tool] = []
        for tool in tools:
            if self._decide(ctx, tool.name, {}).allowed:
                visible.append(tool)
        return visible

    def require_export_permission(
        self,
        ctx: RequestContext,
        name: str,
        arguments: dict[str, Any] | None = None,
    ) -> PolicyDecision:
        """Authorize a tool's server-side write/export behavior."""
        if name not in EXPORT_TOOLS:
            return PolicyDecision(allowed=True)

        if ctx.deployment_profile == "central" and not (arguments or {}).get("output_path"):
            decision = self._deny(
                "export_output_missing",
                "Tool call is not allowed by server policy",
                "Exporting tools require an output_path in central deployments",
            )
            raise PolicyDenied(decision)

        return PolicyDecision(allowed=True, code="export_allowed")

    def _decide(
        self,
        ctx: RequestContext,
        name: str,
        arguments: dict[str, Any],
    ) -> PolicyDecision:
        policy = self.config.policy

        if name in policy.deny_tools:
            return self._deny("tool_denied", f"Tool '{name}' is denied by server policy")

        if ctx.deployment_profile == "central":
            if name == "switch_mode":
                return self._deny(
                    "central_switch_mode_denied",
                    "Tool call is not allowed by server policy",
                    "switch_mode is disabled for central deployments",
                )

            if name in NATIVE_ROOT_TOOLS and not self.isolated_executor_available:
                return self._deny(
                    "central_native_root_denied",
                    "Tool call is not allowed by server policy",
                    "Native ROOT tools require an isolated executor in central deployments",
                )

            if name not in policy.allow_tools:
                return self._deny(
                    "tool_not_allowed",
                    "Tool call is not allowed by server policy",
                    f"{name!r} is not listed in policy.allow_tools",
                )

        elif policy.default_tool_action == "deny" and name not in policy.allow_tools:
            return self._deny(
                "tool_not_allowed",
                "Tool call is not allowed by server policy",
                f"{name!r} is not listed in policy.allow_tools",
            )

        if self._requires_named_resources() and self._contains_raw_local_path(arguments):
            return self._deny(
                "raw_local_path_denied",
                "Raw local file paths are not allowed by server policy",
                "One or more arguments contains an absolute local path",
            )

        return PolicyDecision(allowed=True)

    def _requires_named_resources(self) -> bool:
        policy = self.config.policy
        if self.config.deployment.profile == "central" and policy.allow_central_absolute_paths:
            return False
        return policy.require_named_resources or policy.disable_local_absolute_paths

    def _contains_raw_local_path(self, value: Any) -> bool:
        if isinstance(value, str):
            return _is_raw_local_path(value)
        if isinstance(value, dict):
            return any(self._contains_raw_local_path(item) for item in value.values())
        if isinstance(value, (list, tuple, set)):
            return any(self._contains_raw_local_path(item) for item in value)
        return False

    @staticmethod
    def _deny(code: str, message: str, detail: str | None = None) -> PolicyDecision:
        return PolicyDecision(allowed=False, code=code, message=message, detail=detail)


def _is_raw_local_path(value: str) -> bool:
    """Return True when *value* is an absolute local path or file URI."""
    if not value or value.startswith("@"):
        return False

    parsed = urlparse(value)
    if parsed.scheme:
        return parsed.scheme.lower() == "file"

    return PurePosixPath(value).is_absolute() or PureWindowsPath(value).is_absolute()
