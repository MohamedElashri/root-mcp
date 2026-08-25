"""Streamable HTTP transport with central deployment authentication."""

from __future__ import annotations

import ipaddress
import logging
import re
from contextlib import AsyncExitStack
from typing import Any
from uuid import uuid4

import uvicorn
from mcp.server.transport_security import TransportSecuritySettings
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from root_mcp.config import Config, validate_deployment_config
from root_mcp.security import AuthenticationError, AuthResult, HTTPAuthenticator, RequestContext
from root_mcp.security.auth import BearerValidator

logger = logging.getLogger(__name__)


class HTTPStartupError(ValueError):
    """Raised when HTTP startup settings are unsafe or unsupported."""


_SESSION_ID_RE = re.compile(r"^[\x21-\x7E]+$")


def _is_loopback_host(host: str) -> bool:
    """Return True when *host* is an explicit loopback binding."""
    normalized = host.strip().lower()
    if normalized in {"localhost"}:
        return True
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


def _is_public_bind(host: str) -> bool:
    """Return True for wildcard or non-loopback bind addresses."""
    normalized = host.strip().lower()
    if normalized in {"", "0.0.0.0", "::", "[::]"}:
        return True
    return not _is_loopback_host(normalized)


def validate_http_startup_config(config: Config) -> None:
    """Validate that HTTP startup settings are explicit and conservative."""
    errors: list[str] = []

    try:
        validate_deployment_config(config)
    except ValueError as exc:
        message = str(exc)
        prefix = "Invalid deployment configuration: "
        errors.append(message.removeprefix(prefix))

    if config.deployment.transport != "streamable_http":
        errors.append("serve-http requires deployment.transport='streamable_http'")

    if config.deployment.profile != "central" and not config.http.allow_local_http:
        errors.append(
            "serve-http requires deployment.profile='central' or http.allow_local_http=true"
        )

    if not config.auth.required:
        errors.append("serve-http requires auth.required=true")
    if config.auth.provider == "none":
        errors.append("serve-http requires auth.provider other than 'none'")

    if config.auth.provider == "external_bearer" and not config.auth.jwks_url:
        logger.info(
            "external_bearer auth has no auth.jwks_url configured; "
            "requests must be verified by an injected bearer validator"
        )

    if not config.http.host.strip():
        errors.append("serve-http requires a non-empty http.host")

    if not config.http.endpoint.startswith("/"):
        errors.append("serve-http requires http.endpoint to start with '/'")
    if any(ch.isspace() for ch in config.http.endpoint):
        errors.append("serve-http requires http.endpoint without whitespace")

    if not config.http.require_origin_header:
        errors.append("serve-http requires http.require_origin_header=true")
    if not config.http.origin_allowlist:
        errors.append("serve-http requires at least one allowed Origin")
    if any(origin.strip() == "*" for origin in config.http.origin_allowlist):
        errors.append("serve-http does not allow wildcard Origin entries")

    if _is_public_bind(config.http.host) and not config.http.allow_public_bind:
        errors.append(
            "serve-http public bind requires explicit http.allow_public_bind=true "
            "or --allow-public-bind"
        )

    if _is_public_bind(config.http.host) and not config.auth.required:
        errors.append("serve-http public bind requires auth.required=true")

    if errors:
        raise HTTPStartupError("Invalid HTTP configuration: " + "; ".join(errors))


def build_streamable_http_app(
    root_server: Any,
    *,
    bearer_validator: BearerValidator | None = None,
) -> _RootMCPHTTPApp:
    """Build a Starlette app that serves ROOT-MCP over Streamable HTTP."""
    config: Config = root_server.config
    validate_http_startup_config(config)

    # SDK v2 (2026-07-28 spec): the session manager owns per-connection state.
    # DNS rebinding protection is intentionally disabled here because the
    # wrapper below already enforces strict Origin validation and the
    # deployment may be reached through proxies with arbitrary Host headers.
    inner = root_server.server.streamable_http_app(
        streamable_http_path=config.http.endpoint,
        json_response=True,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=False,
        ),
    )
    authenticator = HTTPAuthenticator(config, bearer_validator=bearer_validator)

    return _RootMCPHTTPApp(
        config=config,
        authenticator=authenticator,
        root_server=root_server,
        inner=inner,
    )


class _RootMCPHTTPApp:
    """ASGI wrapper that validates HTTP policy before entering the MCP transport."""

    def __init__(
        self,
        config: Config,
        authenticator: HTTPAuthenticator,
        root_server: Any,
        inner: Any,
    ):
        self.config = config
        self.authenticator = authenticator
        self.root_server = root_server
        self.inner = inner
        self._exit_stack: AsyncExitStack | None = None

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] == "lifespan":
            await self._handle_lifespan(receive, send)
            return
        if scope["type"] != "http":  # pragma: no cover
            await _send_response(Response(status_code=404), scope, receive, send)
            return

        if scope.get("path") != self.config.http.endpoint:
            await _send_response(Response(status_code=404), scope, receive, send)
            return

        if scope.get("method") not in {"GET", "POST", "DELETE", "OPTIONS"}:
            await _send_response(Response(status_code=405), scope, receive, send)
            return

        request = Request(scope, receive, send)
        if request.method == "OPTIONS":
            response = _preflight_response(self.config, request)
            await _send_response(response, scope, receive, send)
            return

        origin_response = _validate_origin(self.config, request)
        if origin_response is not None:
            await _send_response(origin_response, scope, receive, send)
            return

        session_response = _validate_session_id_header(request)
        if session_response is not None:
            await _send_response(session_response, scope, receive, send)
            return

        try:
            identity = await self.authenticator.authenticate(request)
        except AuthenticationError as exc:
            response = _auth_error_response(exc)
            await _send_response(response, scope, receive, send)
            return

        request.state.root_mcp_context = _request_context_from_http(
            self.config,
            request,
            identity,
        )
        await self.inner(scope, receive, send)

    async def startup(self) -> None:
        """Start the MCP session manager."""
        if self._exit_stack is not None:
            return

        self._exit_stack = AsyncExitStack()
        await self._exit_stack.enter_async_context(self.root_server.server.session_manager.run())

    async def shutdown(self) -> None:
        """Stop the MCP session manager."""
        if self._exit_stack is None:
            return
        await self._exit_stack.aclose()
        self._exit_stack = None

    async def _handle_lifespan(self, receive: Any, send: Any) -> None:
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                try:
                    await self.startup()
                except Exception as exc:  # pragma: no cover  # noqa: BLE001
                    await send({"type": "lifespan.startup.failed", "message": str(exc)})
                else:
                    await send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.shutdown":
                try:
                    await self.shutdown()
                except Exception as exc:  # pragma: no cover  # noqa: BLE001
                    await send({"type": "lifespan.shutdown.failed", "message": str(exc)})
                else:
                    await send({"type": "lifespan.shutdown.complete"})
                return


async def run_http(root_server: Any) -> None:
    """Run ROOT-MCP over Streamable HTTP."""
    config: Config = root_server.config
    app = build_streamable_http_app(root_server)
    logger.info(
        "Starting %s Streamable HTTP endpoint on http://%s:%s%s",
        config.server.name,
        config.http.host,
        config.http.port,
        config.http.endpoint,
    )
    server_config = uvicorn.Config(
        app,
        host=config.http.host,
        port=config.http.port,
        log_level="info",
    )
    await uvicorn.Server(server_config).serve()


async def run_http_skeleton(config: Config) -> None:
    """Backward-compatible validation shim from Phase 5."""
    validate_http_startup_config(config)
    raise NotImplementedError(
        "run_http_skeleton validates only startup settings; use run_http() with "
        "a ROOTMCPServer instance to serve Streamable HTTP."
    )


def _request_context_from_http(
    config: Config,
    request: Request,
    identity: AuthResult | None,
) -> RequestContext:
    request_id = request.headers.get("x-request-id") or str(uuid4())
    return RequestContext(
        deployment_profile=config.deployment.profile,
        transport="streamable_http",
        principal_id=identity.principal_id if identity else None,
        tenant_id=identity.tenant_id if identity else None,
        session_id=request.headers.get("mcp-session-id"),
        roles=identity.roles if identity else set(),
        resource_scopes=identity.resource_scopes if identity else set(),
        request_id=request_id,
    )


async def _send_response(
    response: Response, scope: dict[str, Any], receive: Any, send: Any
) -> None:
    await response(scope, receive, send)


def _validate_origin(config: Config, request: Request) -> Response | None:
    origin = request.headers.get("origin")
    if not origin:
        if config.http.require_origin_header:
            return JSONResponse(
                {"error": "origin_required", "message": "Origin header is required"},
                status_code=403,
            )
        return None

    if origin not in config.http.origin_allowlist:
        return JSONResponse(
            {"error": "origin_denied", "message": "Origin is not allowed"},
            status_code=403,
        )
    return None


def _validate_session_id_header(request: Request) -> Response | None:
    session_id = request.headers.get("mcp-session-id")
    if session_id and not _SESSION_ID_RE.fullmatch(session_id):
        return JSONResponse(
            {"error": "invalid_session_id", "message": "Invalid MCP session ID"},
            status_code=400,
        )
    return None


def _preflight_response(config: Config, request: Request) -> Response:
    origin = request.headers.get("origin")
    if config.http.require_origin_header and not origin:
        return JSONResponse(
            {"error": "origin_required", "message": "Origin header is required"},
            status_code=403,
        )
    if origin and origin not in config.http.origin_allowlist:
        return JSONResponse(
            {"error": "origin_denied", "message": "Origin is not allowed"},
            status_code=403,
        )

    headers = {
        "Access-Control-Allow-Methods": "GET, POST, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": (
            "Authorization, Content-Type, Accept, Origin, MCP-Protocol-Version, "
            "Mcp-Session-Id, X-Request-Id"
        ),
    }
    if origin:
        headers["Access-Control-Allow-Origin"] = origin
    return Response(status_code=204, headers=headers)


def _auth_error_response(exc: AuthenticationError) -> JSONResponse:
    return JSONResponse(
        {"error": "unauthorized", "message": exc.message},
        status_code=exc.status_code,
        headers={"WWW-Authenticate": 'Bearer realm="root-mcp"'} if exc.status_code == 401 else None,
    )
