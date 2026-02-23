"""Configuration management for ROOT-MCP server."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version as _dist_version
import os
from pathlib import Path
import re

import yaml
from pydantic import BaseModel, Field, field_validator


def _package_version() -> str:
    try:
        return _dist_version("root-mcp")
    except PackageNotFoundError:
        return "0.0.0"


class ServerConfig(BaseModel):
    """Server-level settings."""

    name: str = "root-mcp"
    version: str = Field(default_factory=_package_version)
    mode: str = Field("extended", pattern="^(core|extended)$")


class LimitsConfig(BaseModel):
    """Resource limits for safety."""

    max_rows_per_call: int = Field(1_000_000, gt=0)
    max_export_rows: int = Field(10_000_000, gt=0)


class CacheConfig(BaseModel):
    """Caching configuration."""

    enabled: bool = True
    file_cache_size: int = Field(50, gt=0)


class ResourceConfig(BaseModel):
    """Configuration for a data resource (MCP root)."""

    name: str
    uri: str
    description: str = ""
    allowed_patterns: list[str] = Field(default_factory=lambda: ["*.root"])
    excluded_patterns: list[str] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Ensure resource name is valid."""
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Resource name must be alphanumeric (with _ or -)")
        return v


class SecurityConfig(BaseModel):
    """Security and access control settings."""

    allowed_roots: list[str] = Field(default_factory=list)
    allow_remote: bool = False
    allowed_protocols: list[str] = Field(default_factory=lambda: ["file"])
    max_path_depth: int = Field(10, gt=0)

    def effective_protocols(self, resources: list) -> list[str]:
        """Return the union of explicitly allowed protocols and protocols
        inferred from the URI scheme of declared resources.

        This means a resource with ``uri: "root://…"`` automatically permits
        the ``root`` protocol without requiring ``allow_remote: true`` or
        manually adding ``root`` to ``allowed_protocols``.

        Args:
            resources: List of :class:`ResourceConfig` objects (pass
                ``config.resources``).

        Returns:
            Deduplicated list of permitted protocol strings.
        """
        from urllib.parse import urlparse

        auto = {urlparse(r.uri).scheme.lower() for r in resources if r.uri}
        return list(set(self.allowed_protocols) | auto)

    @field_validator("allowed_roots")
    @classmethod
    def validate_roots(cls, v: list[str]) -> list[str]:
        """Ensure allowed roots are absolute paths.

        An empty list is valid and means permissive / zero-config mode:
        the server will allow access to any path the OS permits.
        """
        if not v:
            return v  # Empty = permissive mode; nothing to validate
        validated = []
        for root in v:
            path = Path(root).resolve()
            if not path.is_absolute():
                raise ValueError(f"Allowed root must be absolute: {root}")
            validated.append(str(path))
        return validated


class OutputConfig(BaseModel):
    """Output and export settings."""

    export_base_path: str = "/tmp/root_mcp_output"
    allowed_formats: list[str] = Field(default_factory=lambda: ["json", "csv", "parquet"])

    @field_validator("export_base_path")
    @classmethod
    def validate_export_path(cls, v: str) -> str:
        """Ensure export path is absolute."""
        path = Path(v).resolve()
        return str(path)


class HistogramConfig(BaseModel):
    """Histogram-specific settings."""

    max_bins_1d: int = Field(10_000, gt=0)
    max_bins_2d: int = Field(1_000, gt=0)


class PlottingConfig(BaseModel):
    """Plotting and visualization settings."""

    # Figure settings
    figure_width: float = Field(10.0, gt=0)
    figure_height: float = Field(6.0, gt=0)
    dpi: int = Field(100, gt=0)

    # Data point settings
    marker_size: float = Field(4.0, gt=0)
    marker_style: str = "o"
    error_bar_cap_size: float = Field(2.0, ge=0)

    # Line settings
    line_width: float = Field(2.0, gt=0)
    fit_line_color: str = "red"
    fit_line_style: str = "-"

    # Histogram settings
    hist_fill_alpha: float = Field(0.2, ge=0, le=1)
    hist_fill_color: str = "blue"
    data_color: str = "black"

    # Grid settings
    grid_alpha: float = Field(0.3, ge=0, le=1)
    grid_enabled: bool = True

    # Output format
    default_format: str = "png"
    allowed_formats: list[str] = Field(default_factory=lambda: ["png", "pdf", "svg"])


class CoreConfig(BaseModel):
    """Core mode configuration."""

    cache: CacheConfig = Field(default_factory=CacheConfig)
    limits: LimitsConfig = Field(default_factory=LimitsConfig)


class ExtendedConfig(BaseModel):
    """Extended mode configuration."""

    histogram: HistogramConfig = Field(default_factory=HistogramConfig)
    plotting: PlottingConfig = Field(default_factory=PlottingConfig)
    fitting_max_iterations: int = Field(10_000, gt=0)


class AnalysisConfig(BaseModel):
    """Analysis operation settings."""

    default_chunk_size: int = Field(10_000, gt=0)
    default_read_limit: int = Field(1_000, gt=0)
    histogram: HistogramConfig = Field(default_factory=HistogramConfig)
    plotting: PlottingConfig = Field(default_factory=PlottingConfig)


class RootNativeConfig(BaseModel):
    """Configuration for native ROOT/PyROOT execution."""

    execution_timeout: int = Field(60, gt=0)
    max_output_size: int = Field(10_000_000, gt=0)
    allowed_output_formats: list[str] = Field(
        default_factory=lambda: ["png", "pdf", "svg", "root", "json", "csv"]
    )
    working_directory: str = "/tmp/root_mcp_native"
    max_code_length: int = Field(100_000, gt=0)


class FeatureFlags(BaseModel):
    """Feature toggles."""

    enable_export: bool = True
    enable_root: bool = False


class Config(BaseModel):
    """Root configuration for ROOT-MCP server."""

    server: ServerConfig = Field(default_factory=ServerConfig)
    core: CoreConfig = Field(default_factory=CoreConfig)
    extended: ExtendedConfig = Field(default_factory=ExtendedConfig)
    limits: LimitsConfig = Field(default_factory=LimitsConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    resources: list[ResourceConfig] = Field(default_factory=list)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    analysis: AnalysisConfig = Field(default_factory=AnalysisConfig)
    root_native: RootNativeConfig = Field(default_factory=RootNativeConfig)
    features: FeatureFlags = Field(default_factory=FeatureFlags)

    def get_resource(self, name: str) -> ResourceConfig | None:
        """Get resource configuration by name."""
        for resource in self.resources:
            if resource.name == name:
                return resource
        return None

    def get_default_resource(self) -> ResourceConfig | None:
        """Get the first configured resource (default)."""
        return self.resources[0] if self.resources else None


def load_config(config_path: str | Path | None = None) -> Config:
    """
    Load configuration from YAML file.

    After loading (or using built-in defaults when no file is found), the
    ``ROOT_MCP_DATA_PATH`` environment variable is checked.  Any
    colon-separated directory paths it contains are merged into the config as
    resources via :func:`apply_data_paths`, exactly as if those directories had
    been passed via ``--data-path`` on the CLI.  YAML-declared resources always
    take precedence over env-var paths; CLI ``--data-path`` flags (applied in
    ``main()``) take precedence over both.

    **Config merge priority** (ascending — later wins):

    1. Built-in Pydantic defaults
    2. ``ROOT_MCP_DATA_PATH`` environment variable
    3. ``--data-path`` CLI flags  (applied in ``main()``)
    4. YAML config file values

    Args:
        config_path: Path to config file. If None, looks for:
                    1. ROOT_MCP_CONFIG env var
                    2. ./config.yaml
                    3. ~/.config/root-mcp/config.yaml

    Returns:
        Validated Config object
    """
    if config_path is None:
        # Try environment variable
        if "ROOT_MCP_CONFIG" in os.environ:
            config_path = Path(os.environ["ROOT_MCP_CONFIG"])
        # Try current directory
        elif Path("config.yaml").exists():
            config_path = Path("config.yaml")
        # Try user config directory
        elif Path.home().joinpath(".config/root-mcp/config.yaml").exists():
            config_path = Path.home() / ".config/root-mcp/config.yaml"
        else:
            # Use defaults
            config = Config()
            _apply_data_path_env(config)
            return config

    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path) as f:
        data = yaml.safe_load(f)

    config = Config(**data)
    _apply_data_path_env(config)
    return config


def _apply_data_path_env(config: Config) -> None:
    """Merge ``ROOT_MCP_DATA_PATH`` env var into *config* (in-place).

    The variable accepts colon-separated absolute directory paths, identical in
    semantics to passing each directory via ``--data-path``.  Silently ignores
    empty segments and paths that are already declared as resources in the
    config (YAML values take precedence).
    """
    raw = os.environ.get("ROOT_MCP_DATA_PATH", "").strip()
    if not raw:
        return
    paths = [p.strip() for p in raw.split(":") if p.strip()]
    if paths:
        apply_data_paths(config, paths)


# Two-tier YAML template used by both create_default_config() and
# `root-mcp init`.  Placeholders: {uri}, {enable_root}.
_CONFIG_TEMPLATE = """\
# ROOT-MCP configuration
# ══════════════════════════════════════════════════════
# QUICK START — edit only this section to get started
# ══════════════════════════════════════════════════════

server:
  mode: "extended"

resources:
  - name: "local_data"
    uri: "{uri}"
    description: "Local ROOT files"

# Leave allowed_roots empty to allow any directory (permissive / zero-config mode).
# Add explicit absolute paths here to restrict access.
security:
  allowed_roots: []

features:
  enable_root: {enable_root}  # set true if ROOT/PyROOT is installed

# ══════════════════════════════════════════════════════
# ADVANCED — change only if you need fine-tuning
# ══════════════════════════════════════════════════════

core:
  cache:
    enabled: true
    file_cache_size: 50
  limits:
    max_rows_per_call: 1_000_000
    max_export_rows: 10_000_000

extended:
  histogram:
    max_bins_1d: 10_000
    max_bins_2d: 1_000
  plotting:
    figure_width: 10.0
    figure_height: 6.0
    dpi: 100
    default_format: "png"
    allowed_formats: ["png", "pdf", "svg"]
  fitting_max_iterations: 10_000

output:
  export_base_path: "/tmp/root_mcp_output"
  allowed_formats: ["json", "csv", "parquet"]

root_native:
  execution_timeout: 60
  working_directory: "/tmp/root_mcp_native"
"""


def create_default_config(
    output_path: str | Path,
    data_path: Path | None = None,
    permissive: bool = True,
) -> None:
    """Generate a minimal, human-readable ``config.yaml``.

    The output uses the same two-tier format as ``root-mcp init``: a short
    **QUICK START** section with the only field most users need to change,
    followed by an **ADVANCED** section with fine-tuning knobs.

    Args:
        output_path: Destination file path.
        data_path:  Local directory to use as the resource URI.
                    When ``None`` and ``permissive`` is ``True``, defaults to
                    the current working directory.
                    When ``None`` and ``permissive`` is ``False``, writes a
                    placeholder that the user must edit before use.
        permissive: When ``True`` (default), ``security.allowed_roots`` is
                    left empty (allow any OS-readable path).  Ignored when
                    ``data_path`` is ``None`` and ``permissive`` is ``False``.
    """
    if data_path is not None:
        uri = f"file://{Path(data_path).resolve()}"
    elif permissive:
        uri = f"file://{Path.cwd()}"
    else:
        uri = "file:///REPLACE_WITH_YOUR_DATA_PATH"

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(_CONFIG_TEMPLATE.format(uri=uri, enable_root="false"))
    print(f"Created default config at: {output_path}")


def apply_data_paths(config: Config, paths: list[str]) -> Config:
    """Merge a list of local directory paths into *config* as resources.

    Each path is added as a new :class:`ResourceConfig` only when no existing
    resource already points to the same URI (YAML-declared resources take
    precedence). When ``security.allowed_roots`` is non-empty (restrictive
    mode), the path is also appended there so the validator permits access.

    This is the shared building block used by both the ``--data-path`` CLI
    flag (Task 3) and the ``ROOT_MCP_DATA_PATH`` environment variable (Task 5).

    Args:
        config: The :class:`Config` to update in-place.
        paths:  List of local directory paths (resolved to absolute).

    Returns:
        The same *config* object (mutated) for convenience.
    """
    existing_uris = {r.uri for r in config.resources}
    existing_names = {r.name for r in config.resources}

    for raw_path in paths:
        path = Path(raw_path).resolve()
        uri = f"file://{path}"

        if uri in existing_uris:
            # Already declared in YAML — don't duplicate; YAML wins.
            continue

        # Derive a unique, valid resource name from the directory basename.
        base = re.sub(r"[^a-zA-Z0-9_-]", "_", path.name).strip("_") or "data"
        if base[0].isdigit():
            base = f"data_{base}"
        name = base
        counter = 1
        while name in existing_names:
            name = f"{base}_{counter}"
            counter += 1

        resource = ResourceConfig(
            name=name,
            uri=uri,
            description=f"Data directory: {path}",
        )
        config.resources.append(resource)
        existing_uris.add(uri)
        existing_names.add(name)

        # In restrictive mode (allowed_roots explicitly set), also whitelist
        # the path so the path validator allows access to it.
        if config.security.allowed_roots:
            str_path = str(path)
            if str_path not in config.security.allowed_roots:
                config.security.allowed_roots.append(str_path)

    return config
