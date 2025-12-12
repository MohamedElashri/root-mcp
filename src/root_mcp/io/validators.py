"""Path validation and security checks."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlparse

if TYPE_CHECKING:
    from root_mcp.config import Config, ResourceConfig


class SecurityError(Exception):
    """Raised when a security constraint is violated."""

    pass


class PathValidator:
    """Validates file paths against security constraints."""

    def __init__(self, config: Config):
        """
        Initialize validator with configuration.

        Args:
            config: Server configuration
        """
        self.config = config
        self.allowed_roots = [Path(root).resolve() for root in config.security.allowed_roots]
        self.allowed_protocols = set(config.security.allowed_protocols)
        self.max_depth = config.security.max_path_depth

    def validate_path(self, path: str, resource: ResourceConfig | None = None) -> Path:
        """
        Validate a file path against security constraints.

        Args:
            path: File path or URI to validate
            resource: Optional resource context

        Returns:
            Resolved, validated Path object

        Raises:
            SecurityError: If path violates security constraints
        """
        # Parse URI if it looks like one
        if "://" in path:
            return self._validate_uri(path, resource)

        # Handle resource-relative paths (e.g., "local_data://file.root")
        if path.startswith("@"):
            return self._validate_dataset_alias(path)

        # Local file path
        return self._validate_local_path(path)

    def _validate_local_path(self, path: str) -> Path:
        """Validate a local file path."""
        # Resolve to absolute path
        try:
            resolved = Path(path).resolve(strict=False)
        except (OSError, RuntimeError) as e:
            raise SecurityError(f"Invalid path: {path}") from e

        # Check if path is absolute
        if not resolved.is_absolute():
            raise SecurityError(f"Path must be absolute: {path}")

        # Check path depth (prevent excessively deep paths)
        depth = len(resolved.parts)
        if depth > self.max_depth:
            raise SecurityError(f"Path depth {depth} exceeds maximum {self.max_depth}: {path}")

        # Check if path is under any allowed root
        for allowed_root in self.allowed_roots:
            try:
                resolved.relative_to(allowed_root)
                return resolved  # Path is valid
            except ValueError:
                continue  # Try next root

        raise SecurityError(
            f"Path '{path}' is not under any allowed root. "
            f"Allowed roots: {[str(r) for r in self.allowed_roots]}"
        )

    def _validate_uri(self, uri: str, resource: ResourceConfig | None) -> Path:
        """Validate a URI (file://, root://, http://, etc.)."""
        parsed = urlparse(uri)
        protocol = parsed.scheme.lower()

        # Check if protocol is allowed
        if protocol not in self.allowed_protocols:
            raise SecurityError(
                f"Protocol '{protocol}' not allowed. "
                f"Allowed protocols: {list(self.allowed_protocols)}"
            )

        # For file:// URIs, validate as local path
        if protocol == "file":
            local_path = parsed.path
            return self._validate_local_path(local_path)

        # For remote protocols (root://, http://, etc.)
        if not self.config.security.allow_remote:
            raise SecurityError("Remote file access is disabled")

        # If resource is provided, check if URI matches resource pattern
        if resource:
            if not uri.startswith(resource.uri):
                raise SecurityError(f"URI '{uri}' does not match resource URI '{resource.uri}'")

        # Return a Path-like object (will be handled specially by file manager)
        # For remote URIs, we don't return a local Path
        return Path(uri)  # This is a placeholder; actual handling is in FileManager

    def _validate_dataset_alias(self, alias: str) -> Path:
        """
        Validate and resolve a dataset alias.

        Dataset aliases are configured shortcuts like "@atlas_2024/signal"
        that map to actual file paths.

        Args:
            alias: Dataset alias starting with @

        Returns:
            Resolved path

        Raises:
            SecurityError: If alias is not configured
        """
        # Extract alias name
        # Format: @resource_name/file_path or @alias
        parts = alias[1:].split("/", 1)
        resource_name = parts[0]

        # Find resource
        resource = self.config.get_resource(resource_name)
        if not resource:
            available = [r.name for r in self.config.resources]
            raise SecurityError(f"Unknown resource '{resource_name}'. Available: {available}")

        # Get file path from alias
        if len(parts) > 1:
            file_path = parts[1]
        else:
            raise SecurityError(f"Invalid alias format: {alias}. Use @resource/file")

        # Combine resource URI with file path
        full_path = f"{resource.uri}/{file_path}"
        return self.validate_path(full_path, resource)

    def check_file_pattern(self, path: Path, resource: ResourceConfig) -> bool:
        """
        Check if a file matches resource patterns.

        Args:
            path: File path
            resource: Resource configuration

        Returns:
            True if file matches allowed patterns and not excluded
        """
        filename = path.name

        # Check excluded patterns first
        for pattern in resource.excluded_patterns:
            if self._matches_pattern(filename, pattern):
                return False

        # Check allowed patterns
        for pattern in resource.allowed_patterns:
            if self._matches_pattern(filename, pattern):
                return True

        return False

    @staticmethod
    def _matches_pattern(filename: str, pattern: str) -> bool:
        """Check if filename matches a glob pattern."""
        # Convert glob pattern to regex
        regex = re.escape(pattern).replace(r"\*", ".*").replace(r"\?", ".")
        return re.fullmatch(regex, filename) is not None

    def validate_output_path(self, path: str) -> Path:
        """
        Validate an output path for exports.

        Args:
            path: Destination path for export

        Returns:
            Validated path

        Raises:
            SecurityError: If path is not allowed for output
        """
        resolved = Path(path).resolve()

        # Check if under export base path
        export_base = Path(self.config.output.export_base_path).resolve()
        try:
            resolved.relative_to(export_base)
        except ValueError as e:
            raise SecurityError(f"Output path must be under {export_base}: {path}") from e

        return resolved
