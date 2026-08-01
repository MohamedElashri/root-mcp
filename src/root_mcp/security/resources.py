"""Named resource resolution and ACL checks for central deployments."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Any, Literal
from urllib.parse import urlparse

from root_mcp.config import Config, ResourceConfig
from root_mcp.security.context import RequestContext

if TYPE_CHECKING:
    from root_mcp.core.io.validators import PathValidator

ResourcePermission = Literal["listing", "read", "export"]


class ResourceAccessDenied(Exception):
    """Raised when a resource reference is unavailable to the caller."""

    def __init__(self, code: str, message: str, detail: str | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.detail = detail


@dataclass(frozen=True)
class ResolvedResourcePath:
    """A validated resource reference ready for ROOT file access."""

    path: Path
    resource: ResourceConfig | None = None
    reference: str | None = None


class ResourceResolver:
    """Resolve tool path arguments through resource ACLs and path validation."""

    def __init__(self, config: Config, path_validator: PathValidator):
        self.config = config
        self.path_validator = path_validator

    def accessible_resources(
        self,
        ctx: RequestContext | None,
        permission: ResourcePermission = "listing",
    ) -> list[ResourceConfig]:
        """Return configured resources the caller may use for *permission*."""
        request_ctx = self._ctx(ctx)
        resources: list[ResourceConfig] = []
        for resource in self.config.resources:
            try:
                self.require_access(resource, request_ctx, permission)
            except ResourceAccessDenied:
                continue
            resources.append(resource)
        return resources

    def get_accessible_resource(
        self,
        name: str | None,
        ctx: RequestContext | None,
        permission: ResourcePermission = "listing",
    ) -> ResourceConfig:
        """Look up a resource by name, applying central ACLs."""
        request_ctx = self._ctx(ctx)
        if name:
            resource = self.config.get_resource(name)
            if resource is None:
                available = [r.name for r in self.accessible_resources(request_ctx, permission)]
                raise ResourceAccessDenied(
                    "resource_not_found",
                    f"Resource '{name}' is not available",
                    f"available resources: {available}",
                )
            self.require_access(resource, request_ctx, permission)
            return resource

        resources = self.accessible_resources(request_ctx, permission)
        if not resources:
            raise ResourceAccessDenied(
                "no_accessible_resources",
                "No resources are available to this caller",
            )
        return resources[0]

    def resolve_path(
        self,
        reference: str | dict[str, Any],
        ctx: RequestContext | None,
        permission: ResourcePermission = "read",
    ) -> ResolvedResourcePath:
        """Resolve a tool path argument into a validated local path."""
        request_ctx = self._ctx(ctx)

        if isinstance(reference, dict):
            return self._resolve_structured_reference(reference, request_ctx, permission)

        if not isinstance(reference, str) or not reference.strip():
            raise ResourceAccessDenied("invalid_resource_reference", "Path reference is required")

        value = reference.strip()
        if value.startswith("@"):
            return self._resolve_alias(value, request_ctx, permission)

        if request_ctx.deployment_profile == "central":
            return self._resolve_central_compat_path(value, request_ctx, permission)

        validated = self.path_validator.validate_path(value)
        return ResolvedResourcePath(path=validated, reference=str(validated))

    def reference_for(
        self,
        path: Path,
        resource: ResourceConfig,
        ctx: RequestContext | None,
    ) -> str:
        """Return the caller-facing reference for a resolved file path."""
        request_ctx = self._ctx(ctx)
        if request_ctx.deployment_profile != "central":
            return str(path)

        base = self._file_resource_base(resource)
        if base is None:
            return f"@{resource.name}/{path.name}"
        try:
            relative = path.resolve(strict=False).relative_to(base)
        except ValueError:
            return f"@{resource.name}/{path.name}"
        return f"@{resource.name}/{relative.as_posix()}"

    def require_access(
        self,
        resource: ResourceConfig,
        ctx: RequestContext,
        permission: ResourcePermission,
    ) -> None:
        """Raise when *ctx* cannot use *resource* for *permission*."""
        if ctx.deployment_profile != "central":
            return

        if permission == "listing" and not resource.allow_listing:
            raise ResourceAccessDenied(
                "resource_listing_denied",
                "Resource is not available to this caller",
            )
        if permission == "read" and not resource.allow_read:
            raise ResourceAccessDenied(
                "resource_read_denied",
                "Resource is not available to this caller",
            )
        if permission == "export" and (not resource.allow_read or not resource.allow_export):
            raise ResourceAccessDenied(
                "resource_export_denied",
                "Resource export is not allowed for this caller",
            )

        if self._identity_allowed(resource, ctx):
            return

        raise ResourceAccessDenied(
            "resource_acl_denied",
            "Resource is not available to this caller",
        )

    def _resolve_structured_reference(
        self,
        reference: dict[str, Any],
        ctx: RequestContext,
        permission: ResourcePermission,
    ) -> ResolvedResourcePath:
        resource_name = reference.get("resource")
        relative_path = reference.get("path")
        if not isinstance(resource_name, str) or not isinstance(relative_path, str):
            raise ResourceAccessDenied(
                "invalid_resource_reference",
                "Structured path references require 'resource' and 'path' strings",
            )
        return self._resolve_resource_relative(resource_name, relative_path, ctx, permission)

    def _resolve_alias(
        self,
        alias: str,
        ctx: RequestContext,
        permission: ResourcePermission,
    ) -> ResolvedResourcePath:
        parts = alias[1:].split("/", 1)
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise ResourceAccessDenied(
                "invalid_resource_reference",
                "Use @resource/relative/path.root",
            )
        return self._resolve_resource_relative(parts[0], parts[1], ctx, permission)

    def _resolve_resource_relative(
        self,
        resource_name: str,
        relative_path: str,
        ctx: RequestContext,
        permission: ResourcePermission,
    ) -> ResolvedResourcePath:
        resource = self.get_accessible_resource(resource_name, ctx, permission)
        relative = self._validate_relative_path(relative_path)
        base = self._file_resource_base(resource)

        if base is None:
            full_uri = f"{resource.uri.rstrip('/')}/{relative.as_posix()}"
            validated = self.path_validator.validate_path(full_uri, resource)
            return ResolvedResourcePath(
                path=validated,
                resource=resource,
                reference=f"@{resource.name}/{relative.as_posix()}",
            )

        candidate = (base / relative.as_posix()).resolve(strict=False)
        try:
            candidate.relative_to(base)
        except ValueError as e:
            raise ResourceAccessDenied(
                "resource_path_escape",
                "Resource path must stay inside the named resource",
            ) from e

        if not self.path_validator.check_file_pattern(candidate, resource):
            raise ResourceAccessDenied(
                "resource_pattern_denied",
                "Resource path is not allowed by the resource file patterns",
            )

        try:
            validated = self.path_validator.validate_path(str(candidate), resource)
        except Exception as e:
            raise ResourceAccessDenied(
                "resource_path_denied",
                "Resource path is not allowed by server policy",
                str(e),
            ) from e

        return ResolvedResourcePath(
            path=validated,
            resource=resource,
            reference=f"@{resource.name}/{relative.as_posix()}",
        )

    def _resolve_central_compat_path(
        self,
        value: str,
        ctx: RequestContext,
        permission: ResourcePermission,
    ) -> ResolvedResourcePath:
        if not self.config.policy.allow_central_absolute_paths:
            raise ResourceAccessDenied(
                "raw_local_path_denied",
                "Raw local file paths are not allowed by server policy",
            )

        if not self.config.security.allowed_roots:
            raise ResourceAccessDenied(
                "raw_local_path_denied",
                "Central absolute paths require configured allowed roots",
            )

        try:
            validated = self.path_validator.validate_path(value)
        except Exception as e:
            raise ResourceAccessDenied(
                "raw_local_path_denied",
                "Raw local file path is not allowed by server policy",
                str(e),
            ) from e

        resource = self._resource_for_local_path(validated)
        if resource is not None:
            self.require_access(resource, ctx, permission)
        return ResolvedResourcePath(path=validated, resource=resource, reference=str(validated))

    def _identity_allowed(self, resource: ResourceConfig, ctx: RequestContext) -> bool:
        if not resource.allowed_roles and not resource.allowed_principals:
            return True

        if ctx.principal_id and ctx.principal_id in resource.allowed_principals:
            return True
        if set(resource.allowed_roles) & ctx.roles:
            return True
        return bool(self._scope_allows(resource, ctx))

    @staticmethod
    def _scope_allows(resource: ResourceConfig, ctx: RequestContext) -> bool:
        accepted = {
            resource.name,
            f"resource:{resource.name}",
            f"resource:{resource.name}:read",
            f"{resource.name}:read",
        }
        return bool(ctx.resource_scopes & accepted)

    @staticmethod
    def _validate_relative_path(path: str) -> PurePosixPath:
        relative = PurePosixPath(path)
        if relative.is_absolute() or ".." in relative.parts:
            raise ResourceAccessDenied(
                "invalid_resource_reference",
                "Resource paths must be relative and must not contain '..'",
            )
        if not relative.parts:
            raise ResourceAccessDenied("invalid_resource_reference", "Resource path is required")
        return relative

    @staticmethod
    def _file_resource_base(resource: ResourceConfig) -> Path | None:
        parsed = urlparse(resource.uri)
        if parsed.scheme and parsed.scheme.lower() != "file":
            return None
        if parsed.scheme.lower() == "file":
            return Path(parsed.path).resolve(strict=False)
        return Path(resource.uri).resolve(strict=False)

    def _resource_for_local_path(self, path: Path) -> ResourceConfig | None:
        for resource in self.config.resources:
            base = self._file_resource_base(resource)
            if base is None:
                continue
            try:
                path.relative_to(base)
            except ValueError:
                continue
            return resource
        return None

    def _ctx(self, ctx: RequestContext | None) -> RequestContext:
        if ctx is not None:
            return ctx
        return RequestContext(
            deployment_profile=self.config.deployment.profile,
            transport=self.config.deployment.transport,
            request_id="local",
        )
