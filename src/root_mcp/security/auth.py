"""HTTP authentication helpers for central ROOT-MCP deployments."""

from __future__ import annotations

import ipaddress
from collections.abc import Awaitable, Callable
from inspect import isawaitable
from typing import Any, cast

from pydantic import BaseModel, Field
from starlette.requests import Request

from root_mcp.config import Config

BearerValidator = Callable[
    [str], "AuthResult | dict[str, Any] | None | Awaitable[AuthResult | dict[str, Any] | None]"
]


class AuthenticationError(Exception):
    """Raised when an HTTP request cannot be authenticated."""

    def __init__(self, message: str, *, status_code: int = 401):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class AuthResult(BaseModel):
    """Verified caller identity extracted from HTTP authentication."""

    principal_id: str
    tenant_id: str | None = None
    roles: set[str] = Field(default_factory=set)
    resource_scopes: set[str] = Field(default_factory=set)


class HTTPAuthenticator:
    """Authenticate HTTP requests according to :class:`Config.auth`."""

    def __init__(
        self,
        config: Config,
        *,
        bearer_validator: BearerValidator | None = None,
    ):
        self.config = config
        self.bearer_validator = bearer_validator

    async def authenticate(self, request: Request) -> AuthResult | None:
        """Return verified identity for *request* or raise an auth error."""
        if not self.config.auth.required:
            return None

        provider = self.config.auth.provider
        if provider == "external_bearer":
            return await self._authenticate_external_bearer(request)
        if provider == "trusted_headers":
            return self._authenticate_trusted_headers(request)

        raise AuthenticationError("Authentication is required", status_code=401)

    async def _authenticate_external_bearer(self, request: Request) -> AuthResult:
        header = request.headers.get("authorization", "")
        scheme, _, token = header.partition(" ")
        if scheme.lower() != "bearer" or not token.strip():
            raise AuthenticationError("Missing bearer token", status_code=401)

        token = token.strip()
        if self.bearer_validator is not None:
            result = self.bearer_validator(token)
            if isawaitable(result):
                result = await cast(Awaitable[AuthResult | dict[str, Any] | None], result)
            if not result:
                raise AuthenticationError("Invalid bearer token", status_code=401)
            return _coerce_auth_result(result)

        return self._authenticate_jwt(token)

    def _authenticate_jwt(self, token: str) -> AuthResult:
        auth = self.config.auth
        if not auth.jwks_url:
            raise AuthenticationError(
                "Bearer token verification is not configured",
                status_code=401,
            )

        try:
            import jwt
        except ImportError as exc:  # pragma: no cover
            raise AuthenticationError("JWT support is not installed", status_code=500) from exc

        try:
            signing_key = jwt.PyJWKClient(auth.jwks_url).get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=auth.jwt_algorithms,
                audience=auth.audience,
                issuer=auth.issuer,
                options={"verify_aud": auth.audience is not None},
            )
        except Exception as exc:
            raise AuthenticationError("Invalid bearer token", status_code=401) from exc

        principal = claims.get(auth.principal_claim)
        if not principal:
            raise AuthenticationError("Bearer token is missing a principal claim", status_code=401)

        return AuthResult(
            principal_id=str(principal),
            tenant_id=(
                _claim_as_optional_str(claims.get(auth.tenant_claim)) if auth.tenant_claim else None
            ),
            roles=_claim_as_set(claims.get(auth.roles_claim)),
            resource_scopes=_claim_as_set(claims.get(auth.scopes_claim)),
        )

    def _authenticate_trusted_headers(self, request: Request) -> AuthResult:
        client_host = request.client.host if request.client else None
        if not client_host or not self._trusted_proxy(client_host):
            raise AuthenticationError(
                "Trusted-header authentication requires a trusted proxy", status_code=403
            )

        auth = self.config.auth
        principal_header = (
            auth.trusted_identity_headers[0]
            if auth.trusted_identity_headers
            else auth.trusted_principal_header
        )
        principal = request.headers.get(principal_header)
        if not principal:
            raise AuthenticationError("Missing trusted identity header", status_code=401)

        return AuthResult(
            principal_id=principal,
            tenant_id=request.headers.get(auth.trusted_tenant_header),
            roles=_claim_as_set(request.headers.get(auth.trusted_roles_header)),
            resource_scopes=_claim_as_set(request.headers.get(auth.trusted_scopes_header)),
        )

    def _trusted_proxy(self, host: str) -> bool:
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            return False

        for raw_network in self.config.auth.trusted_proxy_networks:
            try:
                if address in ipaddress.ip_network(raw_network, strict=False):
                    return True
            except ValueError:
                continue
        return False


def _coerce_auth_result(value: AuthResult | dict[str, Any]) -> AuthResult:
    if isinstance(value, AuthResult):
        return value
    return AuthResult(
        principal_id=str(value["principal_id"]),
        tenant_id=_claim_as_optional_str(value.get("tenant_id")),
        roles=_claim_as_set(value.get("roles")),
        resource_scopes=_claim_as_set(value.get("resource_scopes")),
    )


def _claim_as_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _claim_as_set(value: Any) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, str):
        return {item for item in value.replace(",", " ").split() if item}
    if isinstance(value, (list, tuple, set)):
        return {str(item) for item in value if str(item)}
    return {str(value)}
