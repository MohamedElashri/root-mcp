"""Central deployment quota and concurrency enforcement."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from root_mcp.config import Config
from root_mcp.security.context import RequestContext


class QuotaExceeded(Exception):
    """Raised when a request exceeds configured central quotas."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message

    def to_error(self, request_id: str) -> dict[str, Any]:
        """Return the client-facing quota error shape."""
        return {
            "error": "quota_exceeded",
            "message": self.message,
            "request_id": request_id,
            "reason": self.code,
        }


class QuotaManager:
    """Track process-local request quotas for central deployments."""

    def __init__(self, config: Config):
        self.config = config
        self._lock = asyncio.Lock()
        self._principal_running: dict[str, int] = {}
        self._tenant_running: dict[str, int] = {}

    @asynccontextmanager
    async def reserve(
        self,
        ctx: RequestContext,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> AsyncIterator[None]:
        """Reserve concurrency capacity for one central tool call."""
        if ctx.deployment_profile != "central":
            yield
            return

        self.validate_arguments(tool_name, arguments)
        principal_key = self._principal_key(ctx)
        tenant_key = self._tenant_key(ctx)

        async with self._lock:
            principal_count = self._principal_running.get(principal_key, 0)
            tenant_count = self._tenant_running.get(tenant_key, 0)
            if principal_count >= self.config.quotas.max_concurrent_requests_per_principal:
                raise QuotaExceeded(
                    "principal_concurrency_exceeded",
                    "Principal concurrency quota exceeded",
                )
            if tenant_count >= self.config.quotas.max_concurrent_requests_per_tenant:
                raise QuotaExceeded(
                    "tenant_concurrency_exceeded",
                    "Tenant concurrency quota exceeded",
                )

            self._principal_running[principal_key] = principal_count + 1
            self._tenant_running[tenant_key] = tenant_count + 1

        try:
            yield
        finally:
            async with self._lock:
                self._decrement(self._principal_running, principal_key)
                self._decrement(self._tenant_running, tenant_key)

    def validate_arguments(self, tool_name: str, arguments: dict[str, Any]) -> None:
        """Reject requests that visibly exceed row quotas before execution."""
        del tool_name
        max_rows = self.config.quotas.max_rows_per_call
        if max_rows is None:
            return

        requested_rows = self._requested_rows(arguments)
        if requested_rows is not None and requested_rows > max_rows:
            raise QuotaExceeded(
                "row_quota_exceeded",
                f"Requested row count exceeds configured quota ({max_rows})",
            )

    def validate_result(self, result: dict[str, Any] | None) -> None:
        """Reject results whose reported output bytes exceed configured quota."""
        max_bytes = self.config.quotas.max_output_bytes_per_call
        if max_bytes is None:
            return

        output_bytes = exported_bytes(result)
        if output_bytes is not None and output_bytes > max_bytes:
            raise QuotaExceeded(
                "output_bytes_quota_exceeded",
                f"Output size exceeds configured quota ({max_bytes} bytes)",
            )

    @staticmethod
    def running_counts_for(ctx: RequestContext) -> tuple[str, str]:
        """Return the process-local counter keys for a request context."""
        return QuotaManager._principal_key(ctx), QuotaManager._tenant_key(ctx)

    @staticmethod
    def _principal_key(ctx: RequestContext) -> str:
        return ctx.principal_id or "anonymous"

    @staticmethod
    def _tenant_key(ctx: RequestContext) -> str:
        return ctx.tenant_id or ctx.principal_id or "default"

    @staticmethod
    def _decrement(counts: dict[str, int], key: str) -> None:
        value = counts.get(key, 0) - 1
        if value > 0:
            counts[key] = value
        else:
            counts.pop(key, None)

    @staticmethod
    def _requested_rows(arguments: dict[str, Any]) -> int | None:
        limit = arguments.get("limit")
        if isinstance(limit, int):
            return limit

        entry_start = arguments.get("entry_start")
        entry_stop = arguments.get("entry_stop")
        if isinstance(entry_start, int) and isinstance(entry_stop, int):
            return max(0, entry_stop - entry_start)
        if isinstance(entry_stop, int):
            return max(0, entry_stop)
        return None


def exported_bytes(result: dict[str, Any] | None) -> int | None:
    """Extract an exported byte count from common result shapes."""
    if not isinstance(result, dict):
        return None

    for key in ("size_bytes", "bytes_exported", "bytes_written", "file_size"):
        value = result.get(key)
        if isinstance(value, int):
            return value

    data = result.get("data")
    if isinstance(data, dict):
        return exported_bytes(data)
    return None
