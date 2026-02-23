"""Configuration management for ROOT-MCP server."""

from __future__ import annotations

import argparse
from importlib.metadata import PackageNotFoundError, version as _dist_version
import logging
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
    """File-handle cache settings."""

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


#: Log levels accepted by :func:`apply_log_level`.
_VALID_LOG_LEVELS: tuple[str, ...] = ("DEBUG", "INFO", "WARNING", "ERROR")


def apply_log_level(level_str: str) -> None:
    """Set the Python root logger's level.

    This is called in ``main()`` **before** :func:`load_config` so that log
    messages emitted during configuration loading and all subsequent startup
    already respect the requested verbosity.

    Args:
        level_str: Case-insensitive level name. Accepted values:
            ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``.

    Raises:
        ValueError: When *level_str* is not one of the accepted names.
    """
    normalised = level_str.strip().upper()
    if normalised not in _VALID_LOG_LEVELS:
        raise ValueError(f"Log level must be one of {_VALID_LOG_LEVELS}, got: {level_str!r}")
    logging.getLogger().setLevel(normalised)


def _parse_resource_spec(spec: str) -> ResourceConfig:
    """Parse a resource specification string into a :class:`ResourceConfig`.

    The specification format is ``NAME=URI`` or ``NAME=URI|DESCRIPTION``.
    The ``|`` separator is used (rather than ``:``) because URIs routinely
    contain colons (``root://``, ``file:///``, ``https://``).

    Args:
        spec: The raw resource spec string, e.g. ``cms=root://host//path``
              or ``cms=root://host//path|CMS open data``.

    Returns:
        A new :class:`ResourceConfig` instance.

    Raises:
        ValueError: When the spec is malformed or the resource name is invalid.
    """
    if "=" not in spec:
        raise ValueError(f"Resource spec must be NAME=URI or NAME=URI|DESCRIPTION, got: {spec!r}")
    name, rest = spec.split("=", 1)
    name = name.strip()
    if not name:
        raise ValueError(f"Resource name is empty in spec: {spec!r}")
    if "|" in rest:
        uri, description = rest.split("|", 1)
        uri = uri.strip()
        description = description.strip()
    else:
        uri = rest.strip()
        description = ""
    if not uri:
        raise ValueError(f"Resource URI is empty in spec: {spec!r}")
    # ResourceConfig.validate_name will raise if the name contains bad chars.
    return ResourceConfig(name=name, uri=uri, description=description)


def apply_env_overrides(config: Config) -> Config:
    """Read ``ROOT_MCP_*`` environment variables and merge into *config* in-place.

    Env vars sit between the YAML file (priority 2) and CLI flags (priority 4)
    in the merge chain — i.e. an env var overrides the YAML but is itself
    overridden by an explicit ``--flag`` on the command line.

    Only non-empty env vars are applied; missing or empty vars leave the
    corresponding field untouched.

    ** Server & Mode**:

    * ``ROOT_MCP_MODE`` → :attr:`Config.server.mode` (``core`` or ``extended``)
    * ``ROOT_MCP_SERVER_NAME`` → :attr:`Config.server.name`

    ** Security**:

    * ``ROOT_MCP_ALLOWED_ROOTS`` → :attr:`Config.security.allowed_roots`
      (colon-separated paths; replaces the YAML list)
    * ``ROOT_MCP_ALLOW_REMOTE`` → :attr:`Config.security.allow_remote`
      (``1``/``true``/``yes`` → ``True``)
    * ``ROOT_MCP_ALLOWED_PROTOCOLS`` → :attr:`Config.security.allowed_protocols`
      (comma-separated; replaces the YAML list)
    * ``ROOT_MCP_MAX_PATH_DEPTH`` → :attr:`Config.security.max_path_depth`
      (positive integer)

    **Output / Export**:

    * ``ROOT_MCP_EXPORT_PATH`` → :attr:`Config.output.export_base_path` (directory string)
    * ``ROOT_MCP_EXPORT_FORMATS`` → :attr:`Config.output.allowed_formats`
      (comma-separated; replaces the YAML list)
    * ``ROOT_MCP_ENABLE_EXPORT`` → :attr:`Config.features.enable_export`
      (``1``/``true``/``yes`` → ``True``, anything else → ``False``)

    ** Core Limits & Cache**:

    * ``ROOT_MCP_MAX_ROWS`` → :attr:`Config.core.limits.max_rows_per_call` (positive int)
    * ``ROOT_MCP_MAX_EXPORT_ROWS`` → :attr:`Config.core.limits.max_export_rows` (positive int)
    * ``ROOT_MCP_CACHE`` → :attr:`Config.core.cache.enabled`
      (``1``/``true``/``yes`` → ``True``, anything else → ``False``)
    * ``ROOT_MCP_CACHE_SIZE`` → :attr:`Config.core.cache.file_cache_size` (positive int)

    ** Extended Analysis**:

    * ``ROOT_MCP_MAX_BINS_1D`` → :attr:`Config.extended.histogram.max_bins_1d` (positive int)
    * ``ROOT_MCP_MAX_BINS_2D`` → :attr:`Config.extended.histogram.max_bins_2d` (positive int)
    * ``ROOT_MCP_FITTING_ITERATIONS`` → :attr:`Config.extended.fitting_max_iterations` (positive int)
    * ``ROOT_MCP_PLOT_DPI`` → :attr:`Config.extended.plotting.dpi` (positive int)
    * ``ROOT_MCP_PLOT_FORMAT`` → :attr:`Config.extended.plotting.default_format`
      (``png``, ``pdf``, or ``svg``)
    * ``ROOT_MCP_PLOT_WIDTH`` → :attr:`Config.extended.plotting.figure_width` (positive float)
    * ``ROOT_MCP_PLOT_HEIGHT`` → :attr:`Config.extended.plotting.figure_height` (positive float)

    ** Native ROOT Execution**:

    * ``ROOT_MCP_ROOT_TIMEOUT`` → :attr:`Config.root_native.execution_timeout` (positive int, seconds)
    * ``ROOT_MCP_ROOT_WORKDIR`` → :attr:`Config.root_native.working_directory` (path string)
    * ``ROOT_MCP_ROOT_MAX_OUTPUT`` → :attr:`Config.root_native.max_output_size` (positive int, bytes)
    * ``ROOT_MCP_ROOT_MAX_CODE`` → :attr:`Config.root_native.max_code_length` (positive int, chars)

    ** Remote Resources**:

    * ``ROOT_MCP_RESOURCES`` → :attr:`Config.resources` (semicolon-sep list of
      ``NAME=URI`` or ``NAME=URI|DESCRIPTION`` specs; YAML-declared URIs take
      precedence via deduplication)

    Args:
        config: The :class:`Config` to update in-place.

    Returns:
        The same *config* object (mutated) for convenience.

    Raises:
        ValueError: When an env var contains an invalid value (e.g. an
            unrecognised mode string).
    """
    # --- : Server & Mode ---
    _env_mode = os.environ.get("ROOT_MCP_MODE", "").strip()
    if _env_mode:
        if _env_mode not in ("core", "extended"):
            raise ValueError(f"ROOT_MCP_MODE must be 'core' or 'extended', got: {_env_mode!r}")
        config.server.mode = _env_mode

    _env_name = os.environ.get("ROOT_MCP_SERVER_NAME", "").strip()
    if _env_name:
        config.server.name = _env_name

    # --- : Security ---
    _env_allowed_roots = os.environ.get("ROOT_MCP_ALLOWED_ROOTS", "").strip()
    if _env_allowed_roots:
        roots = [r.strip() for r in _env_allowed_roots.split(":") if r.strip()]
        config.security.allowed_roots = roots

    _env_allow_remote = os.environ.get("ROOT_MCP_ALLOW_REMOTE", "").strip().lower()
    if _env_allow_remote:
        config.security.allow_remote = _env_allow_remote in ("1", "true", "yes")

    _env_allowed_protocols = os.environ.get("ROOT_MCP_ALLOWED_PROTOCOLS", "").strip()
    if _env_allowed_protocols:
        protocols = [p.strip().lower() for p in _env_allowed_protocols.split(",") if p.strip()]
        config.security.allowed_protocols = protocols

    _env_max_depth = os.environ.get("ROOT_MCP_MAX_PATH_DEPTH", "").strip()
    if _env_max_depth:
        try:
            depth = int(_env_max_depth)
        except ValueError:
            raise ValueError(f"ROOT_MCP_MAX_PATH_DEPTH must be an integer, got: {_env_max_depth!r}")
        if depth <= 0:
            raise ValueError(f"ROOT_MCP_MAX_PATH_DEPTH must be > 0, got: {depth}")
        config.security.max_path_depth = depth

    # --- : Output / Export ---
    _env_export_path = os.environ.get("ROOT_MCP_EXPORT_PATH", "").strip()
    if _env_export_path:
        config.output.export_base_path = str(Path(_env_export_path).resolve())

    _env_export_formats = os.environ.get("ROOT_MCP_EXPORT_FORMATS", "").strip()
    if _env_export_formats:
        formats = [f.strip().lower() for f in _env_export_formats.split(",") if f.strip()]
        config.output.allowed_formats = formats

    _env_enable_export = os.environ.get("ROOT_MCP_ENABLE_EXPORT", "").strip().lower()
    if _env_enable_export:
        config.features.enable_export = _env_enable_export in ("1", "true", "yes")

    # --- : Core Limits & Cache ---
    def _parse_positive_int(val: str, var_name: str) -> int:
        try:
            n = int(val)
        except ValueError:
            raise ValueError(f"{var_name} must be an integer, got: {val!r}")
        if n <= 0:
            raise ValueError(f"{var_name} must be > 0, got: {n}")
        return n

    _env_max_rows = os.environ.get("ROOT_MCP_MAX_ROWS", "").strip()
    if _env_max_rows:
        config.core.limits.max_rows_per_call = _parse_positive_int(
            _env_max_rows, "ROOT_MCP_MAX_ROWS"
        )

    _env_max_export_rows = os.environ.get("ROOT_MCP_MAX_EXPORT_ROWS", "").strip()
    if _env_max_export_rows:
        config.core.limits.max_export_rows = _parse_positive_int(
            _env_max_export_rows, "ROOT_MCP_MAX_EXPORT_ROWS"
        )

    _env_cache = os.environ.get("ROOT_MCP_CACHE", "").strip().lower()
    if _env_cache:
        config.core.cache.enabled = _env_cache in ("1", "true", "yes")

    _env_cache_size = os.environ.get("ROOT_MCP_CACHE_SIZE", "").strip()
    if _env_cache_size:
        config.core.cache.file_cache_size = _parse_positive_int(
            _env_cache_size, "ROOT_MCP_CACHE_SIZE"
        )

    # --- : Extended Analysis ---
    def _parse_positive_float(val: str, var_name: str) -> float:
        try:
            n = float(val)
        except ValueError:
            raise ValueError(f"{var_name} must be a number, got: {val!r}")
        if n <= 0:
            raise ValueError(f"{var_name} must be > 0, got: {n}")
        return n

    _env_max_bins_1d = os.environ.get("ROOT_MCP_MAX_BINS_1D", "").strip()
    if _env_max_bins_1d:
        config.extended.histogram.max_bins_1d = _parse_positive_int(
            _env_max_bins_1d, "ROOT_MCP_MAX_BINS_1D"
        )

    _env_max_bins_2d = os.environ.get("ROOT_MCP_MAX_BINS_2D", "").strip()
    if _env_max_bins_2d:
        config.extended.histogram.max_bins_2d = _parse_positive_int(
            _env_max_bins_2d, "ROOT_MCP_MAX_BINS_2D"
        )

    _env_fitting_iters = os.environ.get("ROOT_MCP_FITTING_ITERATIONS", "").strip()
    if _env_fitting_iters:
        config.extended.fitting_max_iterations = _parse_positive_int(
            _env_fitting_iters, "ROOT_MCP_FITTING_ITERATIONS"
        )

    _env_plot_dpi = os.environ.get("ROOT_MCP_PLOT_DPI", "").strip()
    if _env_plot_dpi:
        config.extended.plotting.dpi = _parse_positive_int(_env_plot_dpi, "ROOT_MCP_PLOT_DPI")

    _env_plot_format = os.environ.get("ROOT_MCP_PLOT_FORMAT", "").strip().lower()
    if _env_plot_format:
        if _env_plot_format not in ("png", "pdf", "svg"):
            raise ValueError(
                f"ROOT_MCP_PLOT_FORMAT must be 'png', 'pdf', or 'svg', got: {_env_plot_format!r}"
            )
        config.extended.plotting.default_format = _env_plot_format

    _env_plot_width = os.environ.get("ROOT_MCP_PLOT_WIDTH", "").strip()
    if _env_plot_width:
        config.extended.plotting.figure_width = _parse_positive_float(
            _env_plot_width, "ROOT_MCP_PLOT_WIDTH"
        )

    _env_plot_height = os.environ.get("ROOT_MCP_PLOT_HEIGHT", "").strip()
    if _env_plot_height:
        config.extended.plotting.figure_height = _parse_positive_float(
            _env_plot_height, "ROOT_MCP_PLOT_HEIGHT"
        )

    # --- : Native ROOT Execution ---
    _env_root_timeout = os.environ.get("ROOT_MCP_ROOT_TIMEOUT", "").strip()
    if _env_root_timeout:
        config.root_native.execution_timeout = _parse_positive_int(
            _env_root_timeout, "ROOT_MCP_ROOT_TIMEOUT"
        )

    _env_root_workdir = os.environ.get("ROOT_MCP_ROOT_WORKDIR", "").strip()
    if _env_root_workdir:
        config.root_native.working_directory = _env_root_workdir

    _env_root_max_output = os.environ.get("ROOT_MCP_ROOT_MAX_OUTPUT", "").strip()
    if _env_root_max_output:
        config.root_native.max_output_size = _parse_positive_int(
            _env_root_max_output, "ROOT_MCP_ROOT_MAX_OUTPUT"
        )

    _env_root_max_code = os.environ.get("ROOT_MCP_ROOT_MAX_CODE", "").strip()
    if _env_root_max_code:
        config.root_native.max_code_length = _parse_positive_int(
            _env_root_max_code, "ROOT_MCP_ROOT_MAX_CODE"
        )

    # --- : Remote Resources ---
    _env_resources = os.environ.get("ROOT_MCP_RESOURCES", "").strip()
    if _env_resources:
        _existing_uris = {r.uri for r in config.resources}
        _existing_names = {r.name for r in config.resources}
        for _spec in _env_resources.split(";"):
            _spec = _spec.strip()
            if not _spec:
                continue
            _res = _parse_resource_spec(_spec)
            if _res.uri in _existing_uris:
                continue  # YAML-declared resource takes precedence
            _base = _res.name
            _ctr = 1
            while _res.name in _existing_names:
                _res = ResourceConfig(
                    name=f"{_base}_{_ctr}", uri=_res.uri, description=_res.description
                )
                _ctr += 1
            config.resources.append(_res)
            _existing_uris.add(_res.uri)
            _existing_names.add(_res.name)

    return config


def apply_cli_overrides(config: Config, args: "argparse.Namespace") -> Config:
    """Apply parsed CLI arguments onto *config* in-place.

    CLI flags are the highest-priority source — they override both YAML and
    env vars.  This function only mutates a field when the corresponding
    ``args`` attribute is explicitly set (not ``None``).

    ** Server & Mode**:

    * ``args.mode`` → :attr:`Config.server.mode`
    * ``args.server_name`` → :attr:`Config.server.name`

    ** Security**:

    * ``args.allowed_root`` → :attr:`Config.security.allowed_roots` (list; replaces)
    * ``args.allow_remote`` → :attr:`Config.security.allow_remote` (True/False/None)
    * ``args.allowed_protocols`` → :attr:`Config.security.allowed_protocols`
      (comma-string, split on parse)
    * ``args.max_path_depth`` → :attr:`Config.security.max_path_depth`

    ** Output / Export**:

    * ``args.export_path`` → :attr:`Config.output.export_base_path`
    * ``args.export_formats`` → :attr:`Config.output.allowed_formats` (comma-string)
    * ``args.enable_export`` → :attr:`Config.features.enable_export` (False when
      ``--no-export`` is given, ``None`` when not specified)

    ** Core Limits & Cache**:

    * ``args.max_rows`` → :attr:`Config.core.limits.max_rows_per_call`
    * ``args.max_export_rows`` → :attr:`Config.core.limits.max_export_rows`
    * ``args.cache_enabled`` → :attr:`Config.core.cache.enabled` (False when
      ``--no-cache`` is given, ``None`` when not specified)
    * ``args.cache_size`` → :attr:`Config.core.cache.file_cache_size`

    ** Extended Analysis**:

    * ``args.max_bins_1d`` → :attr:`Config.extended.histogram.max_bins_1d`
    * ``args.max_bins_2d`` → :attr:`Config.extended.histogram.max_bins_2d`
    * ``args.fitting_iterations`` → :attr:`Config.extended.fitting_max_iterations`
    * ``args.plot_dpi`` → :attr:`Config.extended.plotting.dpi`
    * ``args.plot_format`` → :attr:`Config.extended.plotting.default_format`
    * ``args.plot_width`` → :attr:`Config.extended.plotting.figure_width`
    * ``args.plot_height`` → :attr:`Config.extended.plotting.figure_height`

    ** Native ROOT Execution**:

    * ``args.root_timeout`` → :attr:`Config.root_native.execution_timeout`
    * ``args.root_workdir`` → :attr:`Config.root_native.working_directory`
    * ``args.root_max_output`` → :attr:`Config.root_native.max_output_size`
    * ``args.root_max_code`` → :attr:`Config.root_native.max_code_length`

    ** Remote Resources**:

    * ``args.resource`` → :attr:`Config.resources` (repeated ``NAME=URI[|DESCRIPTION]``
      specs; YAML-declared URIs take precedence via deduplication)

    Args:
        config: The :class:`Config` to update in-place.
        args:   Parsed :class:`argparse.Namespace` from the server's argument
                parser.

    Returns:
        The same *config* object (mutated) for convenience.

    Raises:
        ValueError: When a CLI flag contains an invalid value.
    """

    # --- Server & Mode ---
    _cli_mode = getattr(args, "mode", None)
    if _cli_mode is not None:
        if _cli_mode not in ("core", "extended"):
            raise ValueError(f"--mode must be 'core' or 'extended', got: {_cli_mode!r}")
        config.server.mode = _cli_mode

    _cli_name = getattr(args, "server_name", None)
    if _cli_name is not None:
        config.server.name = _cli_name

    # --- Security ---
    _cli_allowed_roots = getattr(args, "allowed_root", None)  # list from action="append"
    if _cli_allowed_roots:
        config.security.allowed_roots = list(_cli_allowed_roots)

    _cli_allow_remote = getattr(args, "allow_remote", None)  # True / False / None
    if _cli_allow_remote is not None:
        config.security.allow_remote = _cli_allow_remote

    _cli_protocols = getattr(args, "allowed_protocols", None)  # comma-string
    if _cli_protocols is not None:
        protocols = [p.strip().lower() for p in _cli_protocols.split(",") if p.strip()]
        config.security.allowed_protocols = protocols

    _cli_depth = getattr(args, "max_path_depth", None)  # int from type=int
    if _cli_depth is not None:
        if _cli_depth <= 0:
            raise ValueError(f"--max-path-depth must be > 0, got: {_cli_depth}")
        config.security.max_path_depth = _cli_depth

    # --- Output / Export ---
    _cli_export_path = getattr(args, "export_path", None)
    if _cli_export_path is not None:
        config.output.export_base_path = str(Path(_cli_export_path).resolve())

    _cli_export_formats = getattr(args, "export_formats", None)  # comma-string
    if _cli_export_formats is not None:
        formats = [f.strip().lower() for f in _cli_export_formats.split(",") if f.strip()]
        config.output.allowed_formats = formats

    _cli_enable_export = getattr(args, "enable_export", None)  # False or None
    if _cli_enable_export is not None:
        config.features.enable_export = _cli_enable_export

    # --- Core Limits & Cache ---
    def _cli_positive_int(value: int, flag_name: str) -> int:
        if value <= 0:
            raise ValueError(f"{flag_name} must be > 0, got: {value}")
        return value

    _cli_max_rows = getattr(args, "max_rows", None)
    if _cli_max_rows is not None:
        config.core.limits.max_rows_per_call = _cli_positive_int(_cli_max_rows, "--max-rows")

    _cli_max_export_rows = getattr(args, "max_export_rows", None)
    if _cli_max_export_rows is not None:
        config.core.limits.max_export_rows = _cli_positive_int(
            _cli_max_export_rows, "--max-export-rows"
        )

    _cli_cache_enabled = getattr(args, "cache_enabled", None)  # False or None
    if _cli_cache_enabled is not None:
        config.core.cache.enabled = _cli_cache_enabled

    _cli_cache_size = getattr(args, "cache_size", None)
    if _cli_cache_size is not None:
        config.core.cache.file_cache_size = _cli_positive_int(_cli_cache_size, "--cache-size")

    # --- Extended Analysis ---
    def _cli_positive_float(value: float, flag_name: str) -> float:
        if value <= 0:
            raise ValueError(f"{flag_name} must be > 0, got: {value}")
        return value

    _cli_max_bins_1d = getattr(args, "max_bins_1d", None)
    if _cli_max_bins_1d is not None:
        config.extended.histogram.max_bins_1d = _cli_positive_int(_cli_max_bins_1d, "--max-bins-1d")

    _cli_max_bins_2d = getattr(args, "max_bins_2d", None)
    if _cli_max_bins_2d is not None:
        config.extended.histogram.max_bins_2d = _cli_positive_int(_cli_max_bins_2d, "--max-bins-2d")

    _cli_fitting_iters = getattr(args, "fitting_iterations", None)
    if _cli_fitting_iters is not None:
        config.extended.fitting_max_iterations = _cli_positive_int(
            _cli_fitting_iters, "--fitting-iterations"
        )

    _cli_plot_dpi = getattr(args, "plot_dpi", None)
    if _cli_plot_dpi is not None:
        config.extended.plotting.dpi = _cli_positive_int(_cli_plot_dpi, "--plot-dpi")

    _cli_plot_format = getattr(args, "plot_format", None)
    if _cli_plot_format is not None:
        if _cli_plot_format not in ("png", "pdf", "svg"):
            raise ValueError(
                f"--plot-format must be 'png', 'pdf', or 'svg', got: {_cli_plot_format!r}"
            )
        config.extended.plotting.default_format = _cli_plot_format

    _cli_plot_width = getattr(args, "plot_width", None)
    if _cli_plot_width is not None:
        config.extended.plotting.figure_width = _cli_positive_float(_cli_plot_width, "--plot-width")

    _cli_plot_height = getattr(args, "plot_height", None)
    if _cli_plot_height is not None:
        config.extended.plotting.figure_height = _cli_positive_float(
            _cli_plot_height, "--plot-height"
        )

    # --- Native ROOT Execution ---
    _cli_root_timeout = getattr(args, "root_timeout", None)
    if _cli_root_timeout is not None:
        config.root_native.execution_timeout = _cli_positive_int(
            _cli_root_timeout, "--root-timeout"
        )

    _cli_root_workdir = getattr(args, "root_workdir", None)
    if _cli_root_workdir is not None:
        config.root_native.working_directory = _cli_root_workdir

    _cli_root_max_output = getattr(args, "root_max_output", None)
    if _cli_root_max_output is not None:
        config.root_native.max_output_size = _cli_positive_int(
            _cli_root_max_output, "--root-max-output"
        )

    _cli_root_max_code = getattr(args, "root_max_code", None)
    if _cli_root_max_code is not None:
        config.root_native.max_code_length = _cli_positive_int(
            _cli_root_max_code, "--root-max-code"
        )

    # --- Remote Resources ---
    _cli_resource_specs = getattr(args, "resource", None)  # list from action="append"
    if _cli_resource_specs:
        _existing_uris = {r.uri for r in config.resources}
        _existing_names = {r.name for r in config.resources}
        for _spec in _cli_resource_specs:
            _res = _parse_resource_spec(_spec)
            if _res.uri in _existing_uris:
                continue  # YAML-declared or earlier env-var resource wins
            _base = _res.name
            _ctr = 1
            while _res.name in _existing_names:
                _res = ResourceConfig(
                    name=f"{_base}_{_ctr}", uri=_res.uri, description=_res.description
                )
                _ctr += 1
            config.resources.append(_res)
            _existing_uris.add(_res.uri)
            _existing_names.add(_res.name)

    return config


def apply_data_paths(config: Config, paths: list[str]) -> Config:
    """Merge a list of local directory paths into *config* as resources.

    Each path is added as a new :class:`ResourceConfig` only when no existing
    resource already points to the same URI (YAML-declared resources take
    precedence). When ``security.allowed_roots`` is non-empty (restrictive
    mode), the path is also appended there so the validator permits access.

    This is the shared building block used by both the ``--data-path`` CLI
    flag and the ``ROOT_MCP_DATA_PATH`` environment variable.

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
