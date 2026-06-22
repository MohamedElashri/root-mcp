"""Structured audit logging for central ROOT-MCP deployments."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from root_mcp.config import AuditConfig
from root_mcp.security.context import RequestContext

logger = logging.getLogger(__name__)


class AuditEvent(BaseModel):
    """Normalized audit record for one tool call."""

    request_id: str
    principal: str | None = None
    tenant: str | None = None
    session: str | None = None
    transport: str
    profile: str
    tool_name: str
    normalized_resource: str | None = None
    policy_decision: str
    limits: dict[str, Any] = Field(default_factory=dict)
    output_path: str | None = None
    duration_ms: float
    status: str


class AuditLogger:
    """Emit audit events to configured sinks as compact JSON lines."""

    def __init__(self, config: AuditConfig | None = None):
        self.config = config or AuditConfig()

    def log_event(self, event: AuditEvent) -> None:
        line = json.dumps(event.model_dump(), sort_keys=True)
        if self.config.sink in {"logger", "both"}:
            logger.info("audit_event %s", line)
        if self.config.sink in {"jsonl", "both"}:
            self._write_jsonl(line)

    def _write_jsonl(self, line: str) -> None:
        if not self.config.jsonl_path:
            logger.error("audit sink %s requires audit.jsonl_path", self.config.sink)
            return

        try:
            path = Path(self.config.jsonl_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as f:
                f.write(line)
                f.write("\n")
        except OSError:
            logger.exception("failed to write audit event to %s", self.config.jsonl_path)


def build_audit_event(
    *,
    ctx: RequestContext,
    tool_name: str,
    arguments: dict[str, Any],
    result: dict[str, Any] | None,
    policy_decision: str,
    status: str,
    duration_ms: float,
) -> AuditEvent:
    """Build an audit event from request, arguments, and tool result."""
    return AuditEvent(
        request_id=ctx.request_id,
        principal=ctx.principal_id,
        tenant=ctx.tenant_id,
        session=ctx.session_id,
        transport=ctx.transport,
        profile=ctx.deployment_profile,
        tool_name=tool_name,
        normalized_resource=_extract_resource(arguments, result),
        policy_decision=policy_decision,
        limits=_extract_limits(arguments),
        output_path=_extract_output_path(result),
        duration_ms=round(duration_ms, 3),
        status=status,
    )


def _extract_resource(arguments: dict[str, Any], result: dict[str, Any] | None) -> str | None:
    path = arguments.get("path") or arguments.get("file_path")
    if isinstance(path, str) and path.startswith("@"):
        return path
    if isinstance(path, dict):
        resource = path.get("resource")
        relative_path = path.get("path")
        if isinstance(resource, str) and isinstance(relative_path, str):
            return f"@{resource}/{relative_path}"

    resource = arguments.get("resource")
    if isinstance(resource, str):
        return f"@{resource}"

    if isinstance(result, dict):
        metadata = result.get("metadata")
        if isinstance(metadata, dict) and isinstance(metadata.get("resource"), str):
            return f"@{metadata['resource']}"
    return None


def _extract_limits(arguments: dict[str, Any]) -> dict[str, Any]:
    limit_keys = {
        "limit",
        "entry_start",
        "entry_stop",
        "bins",
        "x_bins",
        "y_bins",
        "bins_x",
        "bins_y",
        "timeout",
    }
    return {key: arguments[key] for key in sorted(limit_keys) if key in arguments}


def _extract_output_path(result: dict[str, Any] | None) -> str | None:
    if not isinstance(result, dict):
        return None

    for key in ("output_path", "plot_path", "artifact_id"):
        value = result.get(key)
        if isinstance(value, str):
            return value

    data = result.get("data")
    if isinstance(data, dict):
        for key in ("output_path", "plot_path", "artifact_id"):
            value = data.get(key)
            if isinstance(value, str):
                return value
    return None
