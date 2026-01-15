"""Configuration management for ROOT-MCP server."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version as _dist_version
import os
from pathlib import Path

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

    @field_validator("allowed_roots")
    @classmethod
    def validate_roots(cls, v: list[str]) -> list[str]:
        """Ensure allowed roots are absolute paths."""
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


class FeatureFlags(BaseModel):
    """Feature toggles."""

    enable_export: bool = True


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
            return Config()

    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path) as f:
        data = yaml.safe_load(f)

    return Config(**data)


def create_default_config(output_path: str | Path) -> None:
    """
    Create a default configuration file.

    Args:
        output_path: Where to write the config file
    """
    config = Config(
        resources=[
            ResourceConfig(
                name="local_data",
                uri="file:///data/root_files",
                description="Local ROOT files for analysis",
            )
        ],
        security=SecurityConfig(
            allowed_roots=["/data/root_files", "/tmp/root_mcp_output"],
        ),
    )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert to dict and write as YAML
    with open(output_path, "w") as f:
        yaml.safe_dump(config.model_dump(), f, default_flow_style=False, sort_keys=False)

    print(f"Created default config at: {output_path}")
