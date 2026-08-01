"""Structured audit logging tests."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import pytest

from root_mcp.config import (
    AuditConfig,
    AuthConfig,
    Config,
    DeploymentConfig,
    PolicyConfig,
    SecurityConfig,
)
from root_mcp.security import RequestContext
from root_mcp.security.audit import AuditEvent, AuditLogger
from root_mcp.server import ROOTMCPServer


def _central_config(tmp_path: Path, *, allow_tools: list[str] | None = None) -> Config:
    return Config(
        deployment=DeploymentConfig(profile="central", transport="streamable_http"),
        auth=AuthConfig(required=True, provider="external_bearer"),
        security=SecurityConfig(allowed_roots=[str(tmp_path)]),
        policy=PolicyConfig(
            default_tool_action="deny",
            allow_tools=allow_tools or ["list_files", "switch_mode"],
        ),
    )


def _ctx() -> RequestContext:
    return RequestContext(
        deployment_profile="central",
        transport="streamable_http",
        tenant_id="tenant-a",
        principal_id="alice",
        session_id="session-1",
        request_id="req-audit",
    )


def _audit_events(caplog: pytest.LogCaptureFixture) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for record in caplog.records:
        if record.name != "root_mcp.security.audit":
            continue
        message = record.getMessage()
        if message.startswith("audit_event "):
            events.append(json.loads(message.split("audit_event ", 1)[1]))
    return events


def test_audit_logger_can_write_jsonl_sink(tmp_path: Path) -> None:
    audit_path = tmp_path / "audit" / "events.jsonl"
    audit_logger = AuditLogger(AuditConfig(sink="jsonl", jsonl_path=str(audit_path)))

    audit_logger.log_event(
        AuditEvent(
            request_id="req-jsonl",
            principal="alice",
            tenant="tenant-a",
            transport="streamable_http",
            profile="central",
            tool_name="list_files",
            policy_decision="allowed",
            duration_ms=1.5,
            status="success",
        )
    )

    [line] = audit_path.read_text(encoding="utf-8").splitlines()
    event = json.loads(line)
    assert event["request_id"] == "req-jsonl"
    assert event["principal"] == "alice"
    assert event["tool_name"] == "list_files"


@pytest.mark.asyncio
async def test_allowed_central_call_emits_audit_record(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    server = ROOTMCPServer(_central_config(tmp_path, allow_tools=["list_files"]))
    caplog.set_level(logging.INFO, logger="root_mcp.security.audit")
    monkeypatch.setattr(
        server,
        "_dispatch_tool",
        lambda name, arguments, ctx: {
            "data": {"output_path": "/srv/export/out.json"},
            "metadata": {"resource": "data"},
        },
    )

    await server.handle_tool_call("list_files", {"resource": "data", "limit": 10}, _ctx())

    [event] = _audit_events(caplog)
    assert event["request_id"] == "req-audit"
    assert event["principal"] == "alice"
    assert event["tenant"] == "tenant-a"
    assert event["session"] == "session-1"
    assert event["profile"] == "central"
    assert event["transport"] == "streamable_http"
    assert event["tool_name"] == "list_files"
    assert event["normalized_resource"] == "@data"
    assert event["policy_decision"] == "allowed"
    assert event["limits"] == {"limit": 10}
    assert event["output_path"] == "/srv/export/out.json"
    assert event["duration_ms"] >= 0
    assert event["status"] == "success"


@pytest.mark.asyncio
async def test_denied_central_call_emits_audit_record(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    server = ROOTMCPServer(_central_config(tmp_path, allow_tools=["switch_mode"]))
    caplog.set_level(logging.INFO, logger="root_mcp.security.audit")

    await server.handle_tool_call("switch_mode", {"mode": "core"}, _ctx())

    [event] = _audit_events(caplog)
    assert event["tool_name"] == "switch_mode"
    assert event["policy_decision"] == "central_switch_mode_denied"
    assert event["status"] == "denied"


@pytest.mark.asyncio
async def test_internal_error_still_emits_audit_record_and_safe_response(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    server = ROOTMCPServer(_central_config(tmp_path, allow_tools=["list_files"]))
    caplog.set_level(logging.INFO, logger="root_mcp.security.audit")

    def raise_path_error(name, arguments, ctx):
        raise RuntimeError("failed under /srv/private/root-mcp")

    monkeypatch.setattr(server, "_dispatch_tool", raise_path_error)

    content = await server.handle_tool_call("list_files", {"resource": "data"}, _ctx())
    payload = json.loads(content[0].text)

    assert payload == {
        "error": "internal_error",
        "message": "Internal server error",
        "request_id": "req-audit",
    }
    [event] = _audit_events(caplog)
    assert event["status"] == "error"
    assert event["policy_decision"] == "allowed"
    assert "/srv/private/root-mcp" not in json.dumps(payload)
