"""Tests for apply_env_overrides() and apply_cli_overrides().

Step 1: server.mode and server.name overrides.
Step 2: security overrides (allowed_roots, allow_remote, allowed_protocols, max_path_depth).
Each test uses a fresh default Config so the functions receive a clean,
YAML-independent baseline.
"""

from __future__ import annotations

import argparse
import logging as _logging
import os
import pytest

from root_mcp.config import (
    Config,
    _parse_resource_spec,
    apply_cli_overrides,
    apply_env_overrides,
    apply_log_level,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _default_config() -> Config:
    """Return a Config built entirely from Pydantic defaults (no YAML)."""
    return Config()


def _make_args(**kwargs) -> argparse.Namespace:
    """Build a minimal Namespace with all attributes set to None,
    then override with any kwargs supplied by the caller."""
    defaults = dict(
        mode=None,
        server_name=None,
        allowed_root=None,
        allow_remote=None,
        allowed_protocols=None,
        max_path_depth=None,
        export_path=None,
        export_formats=None,
        enable_export=None,
        max_rows=None,
        max_export_rows=None,
        cache_enabled=None,
        cache_size=None,
        max_bins_1d=None,
        max_bins_2d=None,
        fitting_iterations=None,
        plot_dpi=None,
        plot_format=None,
        plot_width=None,
        plot_height=None,
        root_timeout=None,
        root_workdir=None,
        root_max_output=None,
        root_max_code=None,
        resource=None,
        log_level=None,
    )
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


# ---------------------------------------------------------------------------
# apply_env_overrides : server.mode
# ---------------------------------------------------------------------------


def test_env_mode_core(monkeypatch):
    """ROOT_MCP_MODE=core → config.server.mode == 'core'."""
    monkeypatch.setenv("ROOT_MCP_MODE", "core")
    config = _default_config()
    apply_env_overrides(config)
    assert config.server.mode == "core"


def test_env_mode_extended(monkeypatch):
    """ROOT_MCP_MODE=extended → config.server.mode == 'extended'."""
    monkeypatch.setenv("ROOT_MCP_MODE", "extended")
    config = _default_config()
    apply_env_overrides(config)
    assert config.server.mode == "extended"


def test_env_mode_invalid(monkeypatch):
    """An unrecognised mode value raises ValueError."""
    monkeypatch.setenv("ROOT_MCP_MODE", "invalid")
    config = _default_config()
    with pytest.raises(ValueError, match="ROOT_MCP_MODE"):
        apply_env_overrides(config)


def test_env_mode_empty_is_noop(monkeypatch):
    """An empty ROOT_MCP_MODE leaves the default ('extended') untouched."""
    monkeypatch.setenv("ROOT_MCP_MODE", "")
    config = _default_config()
    apply_env_overrides(config)
    assert config.server.mode == "extended"


def test_env_mode_unset_is_noop(monkeypatch):
    """A missing ROOT_MCP_MODE leaves the default ('extended') untouched."""
    monkeypatch.delenv("ROOT_MCP_MODE", raising=False)
    config = _default_config()
    apply_env_overrides(config)
    assert config.server.mode == "extended"


def test_env_mode_whitespace_stripped(monkeypatch):
    """Leading/trailing whitespace around the value is stripped."""
    monkeypatch.setenv("ROOT_MCP_MODE", "  core  ")
    config = _default_config()
    apply_env_overrides(config)
    assert config.server.mode == "core"


# ---------------------------------------------------------------------------
# apply_env_overrides : server.name
# ---------------------------------------------------------------------------


def test_env_server_name(monkeypatch):
    """ROOT_MCP_SERVER_NAME sets config.server.name."""
    monkeypatch.setenv("ROOT_MCP_SERVER_NAME", "my-server")
    config = _default_config()
    apply_env_overrides(config)
    assert config.server.name == "my-server"


def test_env_server_name_empty_is_noop(monkeypatch):
    """An empty ROOT_MCP_SERVER_NAME leaves the default name unchanged."""
    monkeypatch.setenv("ROOT_MCP_SERVER_NAME", "")
    config = _default_config()
    apply_env_overrides(config)
    assert config.server.name == "root-mcp"


def test_env_server_name_unset_is_noop(monkeypatch):
    """A missing ROOT_MCP_SERVER_NAME leaves the default name unchanged."""
    monkeypatch.delenv("ROOT_MCP_SERVER_NAME", raising=False)
    config = _default_config()
    apply_env_overrides(config)
    assert config.server.name == "root-mcp"


def test_env_server_name_whitespace_stripped(monkeypatch):
    """Leading/trailing whitespace is stripped from ROOT_MCP_SERVER_NAME."""
    monkeypatch.setenv("ROOT_MCP_SERVER_NAME", "  trimmed-name  ")
    config = _default_config()
    apply_env_overrides(config)
    assert config.server.name == "trimmed-name"


# ---------------------------------------------------------------------------
# apply_env_overrides — returns the same Config object
# ---------------------------------------------------------------------------


def test_env_overrides_returns_same_object(monkeypatch):
    """`apply_env_overrides` returns the identical Config instance."""
    monkeypatch.delenv("ROOT_MCP_MODE", raising=False)
    monkeypatch.delenv("ROOT_MCP_SERVER_NAME", raising=False)
    config = _default_config()
    result = apply_env_overrides(config)
    assert result is config


# ---------------------------------------------------------------------------
# apply_cli_overrides : server.mode
# ---------------------------------------------------------------------------


def test_cli_mode_core():
    """--mode core → config.server.mode == 'core'."""
    config = _default_config()
    apply_cli_overrides(config, _make_args(mode="core"))
    assert config.server.mode == "core"


def test_cli_mode_extended():
    """--mode extended → config.server.mode == 'extended'."""
    config = _default_config()
    apply_cli_overrides(config, _make_args(mode="extended"))
    assert config.server.mode == "extended"


def test_cli_mode_none_is_noop():
    """args.mode=None (not supplied) leaves mode unchanged."""
    config = _default_config()
    apply_cli_overrides(config, _make_args(mode=None))
    assert config.server.mode == "extended"  # Pydantic default


def test_cli_mode_invalid():
    """An invalid --mode value raises ValueError."""
    config = _default_config()
    with pytest.raises(ValueError, match="--mode"):
        apply_cli_overrides(config, _make_args(mode="turbo"))


# ---------------------------------------------------------------------------
# apply_cli_overrides : server.name
# ---------------------------------------------------------------------------


def test_cli_server_name():
    """--server-name sets config.server.name."""
    config = _default_config()
    apply_cli_overrides(config, _make_args(server_name="custom-name"))
    assert config.server.name == "custom-name"


def test_cli_server_name_none_is_noop():
    """args.server_name=None (not supplied) leaves name unchanged."""
    config = _default_config()
    apply_cli_overrides(config, _make_args(server_name=None))
    assert config.server.name == "root-mcp"


# ---------------------------------------------------------------------------
# Priority: CLI beats env var
# ---------------------------------------------------------------------------


def test_cli_mode_overrides_env(monkeypatch):
    """CLI --mode wins over ROOT_MCP_MODE when both are supplied."""
    monkeypatch.setenv("ROOT_MCP_MODE", "core")
    config = _default_config()
    apply_env_overrides(config)  # env sets 'core'
    apply_cli_overrides(config, _make_args(mode="extended"))  # CLI overrides
    assert config.server.mode == "extended"


def test_cli_server_name_overrides_env(monkeypatch):
    """CLI --server-name wins over ROOT_MCP_SERVER_NAME."""
    monkeypatch.setenv("ROOT_MCP_SERVER_NAME", "env-name")
    config = _default_config()
    apply_env_overrides(config)
    apply_cli_overrides(config, _make_args(server_name="cli-name"))
    assert config.server.name == "cli-name"


def test_env_overrides_yaml_default(monkeypatch):
    """Env var wins over the built-in Pydantic default (simulates YAML < env)."""
    monkeypatch.setenv("ROOT_MCP_MODE", "core")
    config = _default_config()
    # Simulate a YAML that set mode=extended (same as default here)
    assert config.server.mode == "extended"
    apply_env_overrides(config)
    assert config.server.mode == "core"


# ---------------------------------------------------------------------------
# apply_cli_overrides — returns the same Config object
# ---------------------------------------------------------------------------


def test_cli_overrides_returns_same_object():
    """`apply_cli_overrides` returns the identical Config instance."""
    config = _default_config()
    result = apply_cli_overrides(config, _make_args())
    assert result is config


# ===========================================================================
# Security
# ===========================================================================

# ---------------------------------------------------------------------------
# apply_env_overrides — allowed_roots
# ---------------------------------------------------------------------------


def test_env_allowed_roots_single(monkeypatch, tmp_path):
    """A single path in ROOT_MCP_ALLOWED_ROOTS is parsed correctly."""
    monkeypatch.setenv("ROOT_MCP_ALLOWED_ROOTS", str(tmp_path))
    config = _default_config()
    apply_env_overrides(config)
    assert config.security.allowed_roots == [str(tmp_path)]


def test_env_allowed_roots_colon_separated(monkeypatch, tmp_path):
    """Colon-separated paths in ROOT_MCP_ALLOWED_ROOTS are split into a list."""
    p1, p2 = str(tmp_path / "a"), str(tmp_path / "b")
    monkeypatch.setenv("ROOT_MCP_ALLOWED_ROOTS", f"{p1}:{p2}")
    config = _default_config()
    apply_env_overrides(config)
    assert config.security.allowed_roots == [p1, p2]


def test_env_allowed_roots_replaces_existing(monkeypatch, tmp_path):
    """ROOT_MCP_ALLOWED_ROOTS replaces any pre-existing allowed_roots value."""
    old = str(tmp_path / "old")
    new = str(tmp_path / "new")
    monkeypatch.setenv("ROOT_MCP_ALLOWED_ROOTS", new)
    config = _default_config()
    config.security.allowed_roots = [old]  # simulate YAML-set value
    apply_env_overrides(config)
    assert config.security.allowed_roots == [new]


def test_env_allowed_roots_empty_items_skipped(monkeypatch, tmp_path):
    """Empty items between colons are silently skipped."""
    p = str(tmp_path)
    monkeypatch.setenv("ROOT_MCP_ALLOWED_ROOTS", f":{p}::")
    config = _default_config()
    apply_env_overrides(config)
    assert config.security.allowed_roots == [p]


def test_env_allowed_roots_unset_is_noop(monkeypatch):
    """Missing ROOT_MCP_ALLOWED_ROOTS leaves allowed_roots unchanged."""
    monkeypatch.delenv("ROOT_MCP_ALLOWED_ROOTS", raising=False)
    config = _default_config()
    apply_env_overrides(config)
    assert config.security.allowed_roots == []


# ---------------------------------------------------------------------------
# apply_env_overrides — allow_remote
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("val", ["1", "true", "yes", "True", "TRUE", "YES"])
def test_env_allow_remote_true_values(monkeypatch, val):
    """All recognised truthy strings for ROOT_MCP_ALLOW_REMOTE set allow_remote=True."""
    monkeypatch.setenv("ROOT_MCP_ALLOW_REMOTE", val)
    config = _default_config()
    apply_env_overrides(config)
    assert config.security.allow_remote is True


@pytest.mark.parametrize("val", ["0", "false", "no", "False", "off", "anything"])
def test_env_allow_remote_false_values(monkeypatch, val):
    """Non-truthy strings set allow_remote=False."""
    monkeypatch.setenv("ROOT_MCP_ALLOW_REMOTE", val)
    config = _default_config()
    config.security.allow_remote = True  # ensure it changes
    apply_env_overrides(config)
    assert config.security.allow_remote is False


def test_env_allow_remote_unset_is_noop(monkeypatch):
    """Missing ROOT_MCP_ALLOW_REMOTE leaves allow_remote unchanged."""
    monkeypatch.delenv("ROOT_MCP_ALLOW_REMOTE", raising=False)
    config = _default_config()
    apply_env_overrides(config)
    assert config.security.allow_remote is False


# ---------------------------------------------------------------------------
# apply_env_overrides — allowed_protocols
# ---------------------------------------------------------------------------


def test_env_allowed_protocols_comma_separated(monkeypatch):
    """Comma-separated protocols are parsed into a list."""
    monkeypatch.setenv("ROOT_MCP_ALLOWED_PROTOCOLS", "file,root,http")
    config = _default_config()
    apply_env_overrides(config)
    assert config.security.allowed_protocols == ["file", "root", "http"]


def test_env_allowed_protocols_uppercased_are_lowercased(monkeypatch):
    """Protocol names are lowercased during parsing."""
    monkeypatch.setenv("ROOT_MCP_ALLOWED_PROTOCOLS", "FILE,ROOT")
    config = _default_config()
    apply_env_overrides(config)
    assert config.security.allowed_protocols == ["file", "root"]


def test_env_allowed_protocols_replaces_existing(monkeypatch):
    """ROOT_MCP_ALLOWED_PROTOCOLS replaces the YAML-set list."""
    monkeypatch.setenv("ROOT_MCP_ALLOWED_PROTOCOLS", "root")
    config = _default_config()
    assert config.security.allowed_protocols == ["file"]  # default
    apply_env_overrides(config)
    assert config.security.allowed_protocols == ["root"]


def test_env_allowed_protocols_unset_is_noop(monkeypatch):
    """Missing ROOT_MCP_ALLOWED_PROTOCOLS leaves allowed_protocols unchanged."""
    monkeypatch.delenv("ROOT_MCP_ALLOWED_PROTOCOLS", raising=False)
    config = _default_config()
    apply_env_overrides(config)
    assert config.security.allowed_protocols == ["file"]


# ---------------------------------------------------------------------------
# apply_env_overrides — max_path_depth
# ---------------------------------------------------------------------------


def test_env_max_path_depth_integer(monkeypatch):
    """ROOT_MCP_MAX_PATH_DEPTH parses a valid integer."""
    monkeypatch.setenv("ROOT_MCP_MAX_PATH_DEPTH", "5")
    config = _default_config()
    apply_env_overrides(config)
    assert config.security.max_path_depth == 5


def test_env_max_path_depth_non_integer_raises(monkeypatch):
    """A non-integer ROOT_MCP_MAX_PATH_DEPTH raises ValueError."""
    monkeypatch.setenv("ROOT_MCP_MAX_PATH_DEPTH", "abc")
    config = _default_config()
    with pytest.raises(ValueError, match="ROOT_MCP_MAX_PATH_DEPTH"):
        apply_env_overrides(config)


def test_env_max_path_depth_zero_raises(monkeypatch):
    """ROOT_MCP_MAX_PATH_DEPTH=0 raises ValueError (must be > 0)."""
    monkeypatch.setenv("ROOT_MCP_MAX_PATH_DEPTH", "0")
    config = _default_config()
    with pytest.raises(ValueError, match="> 0"):
        apply_env_overrides(config)


def test_env_max_path_depth_unset_is_noop(monkeypatch):
    """Missing ROOT_MCP_MAX_PATH_DEPTH leaves max_path_depth at its default (10)."""
    monkeypatch.delenv("ROOT_MCP_MAX_PATH_DEPTH", raising=False)
    config = _default_config()
    apply_env_overrides(config)
    assert config.security.max_path_depth == 10


# ---------------------------------------------------------------------------
# apply_cli_overrides
# ---------------------------------------------------------------------------


def test_cli_allowed_root_single(tmp_path):
    """--allowed-root sets allowed_roots from a single-element list."""
    config = _default_config()
    apply_cli_overrides(config, _make_args(allowed_root=[str(tmp_path)]))
    assert config.security.allowed_roots == [str(tmp_path)]


def test_cli_allowed_root_multiple(tmp_path):
    """--allowed-root (repeated) builds a list of allowed roots."""
    p1, p2 = str(tmp_path / "a"), str(tmp_path / "b")
    config = _default_config()
    apply_cli_overrides(config, _make_args(allowed_root=[p1, p2]))
    assert config.security.allowed_roots == [p1, p2]


def test_cli_allowed_root_none_is_noop():
    """args.allowed_root=None (not provided) leaves allowed_roots unchanged."""
    config = _default_config()
    apply_cli_overrides(config, _make_args(allowed_root=None))
    assert config.security.allowed_roots == []


def test_cli_allow_remote_true():
    """--allow-remote sets allow_remote=True."""
    config = _default_config()
    apply_cli_overrides(config, _make_args(allow_remote=True))
    assert config.security.allow_remote is True


def test_cli_no_allow_remote_false():
    """--no-allow-remote sets allow_remote=False."""
    config = _default_config()
    config.security.allow_remote = True  # set to True first
    apply_cli_overrides(config, _make_args(allow_remote=False))
    assert config.security.allow_remote is False


def test_cli_allow_remote_none_is_noop():
    """args.allow_remote=None (neither flag) leaves allow_remote unchanged."""
    config = _default_config()
    apply_cli_overrides(config, _make_args(allow_remote=None))
    assert config.security.allow_remote is False


def test_cli_allowed_protocols_comma(monkeypatch):
    """--allowed-protocols with a comma-string is split and lowercased."""
    config = _default_config()
    apply_cli_overrides(config, _make_args(allowed_protocols="file,root,xrootd"))
    assert config.security.allowed_protocols == ["file", "root", "xrootd"]


def test_cli_allowed_protocols_none_is_noop():
    """args.allowed_protocols=None leaves allowed_protocols unchanged."""
    config = _default_config()
    apply_cli_overrides(config, _make_args(allowed_protocols=None))
    assert config.security.allowed_protocols == ["file"]


def test_cli_max_path_depth():
    """--max-path-depth sets max_path_depth."""
    config = _default_config()
    apply_cli_overrides(config, _make_args(max_path_depth=3))
    assert config.security.max_path_depth == 3


def test_cli_max_path_depth_zero_raises():
    """--max-path-depth 0 raises ValueError."""
    config = _default_config()
    with pytest.raises(ValueError, match="> 0"):
        apply_cli_overrides(config, _make_args(max_path_depth=0))


def test_cli_max_path_depth_none_is_noop():
    """args.max_path_depth=None leaves max_path_depth at its default (10)."""
    config = _default_config()
    apply_cli_overrides(config, _make_args(max_path_depth=None))
    assert config.security.max_path_depth == 10


# ---------------------------------------------------------------------------
# Priority: CLI beats env var
# ---------------------------------------------------------------------------


def test_cli_allowed_root_overrides_env(monkeypatch, tmp_path):
    """CLI --allowed-root wins over ROOT_MCP_ALLOWED_ROOTS."""
    env_path = str(tmp_path / "env")
    cli_path = str(tmp_path / "cli")
    monkeypatch.setenv("ROOT_MCP_ALLOWED_ROOTS", env_path)
    config = _default_config()
    apply_env_overrides(config)
    assert config.security.allowed_roots == [env_path]
    apply_cli_overrides(config, _make_args(allowed_root=[cli_path]))
    assert config.security.allowed_roots == [cli_path]


def test_cli_allow_remote_overrides_env(monkeypatch):
    """CLI --no-allow-remote wins over ROOT_MCP_ALLOW_REMOTE=true."""
    monkeypatch.setenv("ROOT_MCP_ALLOW_REMOTE", "true")
    config = _default_config()
    apply_env_overrides(config)
    assert config.security.allow_remote is True
    apply_cli_overrides(config, _make_args(allow_remote=False))
    assert config.security.allow_remote is False


def test_cli_protocols_override_env(monkeypatch):
    """CLI --allowed-protocols wins over ROOT_MCP_ALLOWED_PROTOCOLS."""
    monkeypatch.setenv("ROOT_MCP_ALLOWED_PROTOCOLS", "file,root")
    config = _default_config()
    apply_env_overrides(config)
    assert config.security.allowed_protocols == ["file", "root"]
    apply_cli_overrides(config, _make_args(allowed_protocols="file"))
    assert config.security.allowed_protocols == ["file"]


# ===========================================================================
# Output / Export
# ===========================================================================

# ---------------------------------------------------------------------------
# apply_env_overrides — export_base_path
# ---------------------------------------------------------------------------


def test_env_export_path(monkeypatch, tmp_path):
    """ROOT_MCP_EXPORT_PATH sets output.export_base_path (resolved to absolute)."""
    monkeypatch.setenv("ROOT_MCP_EXPORT_PATH", str(tmp_path))
    config = _default_config()
    apply_env_overrides(config)
    assert config.output.export_base_path == str(tmp_path.resolve())


def test_env_export_path_relative_resolved(monkeypatch, tmp_path, monkeypatch_cwd=None):
    """A relative ROOT_MCP_EXPORT_PATH is resolved to an absolute path."""
    monkeypatch.setenv("ROOT_MCP_EXPORT_PATH", "relative/dir")
    config = _default_config()
    apply_env_overrides(config)
    import pathlib

    assert pathlib.Path(config.output.export_base_path).is_absolute()


def test_env_export_path_unset_is_noop(monkeypatch):
    """Missing ROOT_MCP_EXPORT_PATH leaves default unchanged."""
    monkeypatch.delenv("ROOT_MCP_EXPORT_PATH", raising=False)
    config = _default_config()
    default = config.output.export_base_path
    apply_env_overrides(config)
    assert config.output.export_base_path == default


def test_env_export_path_empty_is_noop(monkeypatch):
    """An empty ROOT_MCP_EXPORT_PATH leaves the default unchanged."""
    monkeypatch.setenv("ROOT_MCP_EXPORT_PATH", "")
    config = _default_config()
    default = config.output.export_base_path
    apply_env_overrides(config)
    assert config.output.export_base_path == default


# ---------------------------------------------------------------------------
# apply_env_overrides — allowed_formats
# ---------------------------------------------------------------------------


def test_env_export_formats_comma_separated(monkeypatch):
    """Comma-separated ROOT_MCP_EXPORT_FORMATS replaces allowed_formats."""
    monkeypatch.setenv("ROOT_MCP_EXPORT_FORMATS", "json,csv")
    config = _default_config()
    apply_env_overrides(config)
    assert config.output.allowed_formats == ["json", "csv"]


def test_env_export_formats_uppercased_lowercased(monkeypatch):
    """Format names are lowercased during parsing."""
    monkeypatch.setenv("ROOT_MCP_EXPORT_FORMATS", "JSON,CSV,Parquet")
    config = _default_config()
    apply_env_overrides(config)
    assert config.output.allowed_formats == ["json", "csv", "parquet"]


def test_env_export_formats_replaces_existing(monkeypatch):
    """ROOT_MCP_EXPORT_FORMATS replaces whatever was in config (YAML or default)."""
    monkeypatch.setenv("ROOT_MCP_EXPORT_FORMATS", "json")
    config = _default_config()
    assert "parquet" in config.output.allowed_formats  # default has parquet
    apply_env_overrides(config)
    assert config.output.allowed_formats == ["json"]


def test_env_export_formats_unset_is_noop(monkeypatch):
    """Missing ROOT_MCP_EXPORT_FORMATS leaves allowed_formats at default."""
    monkeypatch.delenv("ROOT_MCP_EXPORT_FORMATS", raising=False)
    config = _default_config()
    apply_env_overrides(config)
    assert set(config.output.allowed_formats) == {"json", "csv", "parquet"}


# ---------------------------------------------------------------------------
# apply_env_overrides — enable_export
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("val", ["1", "true", "yes", "True", "TRUE", "YES"])
def test_env_enable_export_true_values(monkeypatch, val):
    """All recognised truthy strings set enable_export=True."""
    monkeypatch.setenv("ROOT_MCP_ENABLE_EXPORT", val)
    config = _default_config()
    config.features.enable_export = False  # start from False
    apply_env_overrides(config)
    assert config.features.enable_export is True


@pytest.mark.parametrize("val", ["0", "false", "no", "False", "off"])
def test_env_enable_export_false_values(monkeypatch, val):
    """Non-truthy strings set enable_export=False."""
    monkeypatch.setenv("ROOT_MCP_ENABLE_EXPORT", val)
    config = _default_config()
    apply_env_overrides(config)
    assert config.features.enable_export is False


def test_env_enable_export_unset_is_noop(monkeypatch):
    """Missing ROOT_MCP_ENABLE_EXPORT leaves enable_export at default (True)."""
    monkeypatch.delenv("ROOT_MCP_ENABLE_EXPORT", raising=False)
    config = _default_config()
    apply_env_overrides(config)
    assert config.features.enable_export is True


# ---------------------------------------------------------------------------
# apply_cli_overrides
# ---------------------------------------------------------------------------


def test_cli_export_path(tmp_path):
    """--export-path sets output.export_base_path (resolved to absolute)."""
    config = _default_config()
    apply_cli_overrides(config, _make_args(export_path=str(tmp_path)))
    assert config.output.export_base_path == str(tmp_path.resolve())


def test_cli_export_path_none_is_noop():
    """args.export_path=None leaves export_base_path unchanged."""
    config = _default_config()
    default = config.output.export_base_path
    apply_cli_overrides(config, _make_args(export_path=None))
    assert config.output.export_base_path == default


def test_cli_export_formats_comma():
    """--export-formats with a comma-string is split and lowercased."""
    config = _default_config()
    apply_cli_overrides(config, _make_args(export_formats="json,csv"))
    assert config.output.allowed_formats == ["json", "csv"]


def test_cli_export_formats_none_is_noop():
    """args.export_formats=None leaves allowed_formats unchanged."""
    config = _default_config()
    apply_cli_overrides(config, _make_args(export_formats=None))
    assert set(config.output.allowed_formats) == {"json", "csv", "parquet"}


def test_cli_no_export_disables_feature():
    """--no-export (args.enable_export=False) disables the export feature."""
    config = _default_config()
    assert config.features.enable_export is True
    apply_cli_overrides(config, _make_args(enable_export=False))
    assert config.features.enable_export is False


def test_cli_enable_export_none_is_noop():
    """args.enable_export=None (flag not given) leaves enable_export unchanged."""
    config = _default_config()
    apply_cli_overrides(config, _make_args(enable_export=None))
    assert config.features.enable_export is True


# ---------------------------------------------------------------------------
# Priority: CLI beats env var
# ---------------------------------------------------------------------------


def test_cli_export_path_overrides_env(monkeypatch, tmp_path):
    """CLI --export-path wins over ROOT_MCP_EXPORT_PATH."""
    env_dir = str(tmp_path / "env")
    cli_dir = str(tmp_path / "cli")
    monkeypatch.setenv("ROOT_MCP_EXPORT_PATH", env_dir)
    config = _default_config()
    apply_env_overrides(config)
    import pathlib

    assert config.output.export_base_path == str(pathlib.Path(env_dir).resolve())
    apply_cli_overrides(config, _make_args(export_path=cli_dir))
    assert config.output.export_base_path == str(pathlib.Path(cli_dir).resolve())


def test_cli_export_formats_overrides_env(monkeypatch):
    """CLI --export-formats wins over ROOT_MCP_EXPORT_FORMATS."""
    monkeypatch.setenv("ROOT_MCP_EXPORT_FORMATS", "json,csv,parquet")
    config = _default_config()
    apply_env_overrides(config)
    assert config.output.allowed_formats == ["json", "csv", "parquet"]
    apply_cli_overrides(config, _make_args(export_formats="json"))
    assert config.output.allowed_formats == ["json"]


def test_cli_no_export_overrides_env_enable(monkeypatch):
    """CLI --no-export wins even when ROOT_MCP_ENABLE_EXPORT=true."""
    monkeypatch.setenv("ROOT_MCP_ENABLE_EXPORT", "true")
    config = _default_config()
    apply_env_overrides(config)
    assert config.features.enable_export is True
    apply_cli_overrides(config, _make_args(enable_export=False))
    assert config.features.enable_export is False


# ===========================================================================
# Core Limits & Cache
# ===========================================================================

# ---------------------------------------------------------------------------
# apply_env_overrides — max_rows_per_call
# ---------------------------------------------------------------------------


def test_env_max_rows_integer_parsing(monkeypatch):
    """ROOT_MCP_MAX_ROWS sets core.limits.max_rows_per_call."""
    monkeypatch.setenv("ROOT_MCP_MAX_ROWS", "500000")
    config = _default_config()
    apply_env_overrides(config)
    assert config.core.limits.max_rows_per_call == 500_000


def test_env_max_rows_invalid_raises(monkeypatch):
    """A non-integer ROOT_MCP_MAX_ROWS raises ValueError."""
    monkeypatch.setenv("ROOT_MCP_MAX_ROWS", "abc")
    config = _default_config()
    with pytest.raises(ValueError, match="ROOT_MCP_MAX_ROWS"):
        apply_env_overrides(config)


def test_env_max_rows_zero_raises(monkeypatch):
    """ROOT_MCP_MAX_ROWS=0 raises ValueError (must be > 0)."""
    monkeypatch.setenv("ROOT_MCP_MAX_ROWS", "0")
    config = _default_config()
    with pytest.raises(ValueError, match="> 0"):
        apply_env_overrides(config)


def test_env_max_rows_unset_is_noop(monkeypatch):
    """Missing ROOT_MCP_MAX_ROWS leaves max_rows_per_call at default (1_000_000)."""
    monkeypatch.delenv("ROOT_MCP_MAX_ROWS", raising=False)
    config = _default_config()
    apply_env_overrides(config)
    assert config.core.limits.max_rows_per_call == 1_000_000


# ---------------------------------------------------------------------------
# apply_env_overrides — max_export_rows
# ---------------------------------------------------------------------------


def test_env_max_export_rows_integer_parsing(monkeypatch):
    """ROOT_MCP_MAX_EXPORT_ROWS sets core.limits.max_export_rows."""
    monkeypatch.setenv("ROOT_MCP_MAX_EXPORT_ROWS", "1000")
    config = _default_config()
    apply_env_overrides(config)
    assert config.core.limits.max_export_rows == 1000


def test_env_max_export_rows_invalid_raises(monkeypatch):
    """A non-integer ROOT_MCP_MAX_EXPORT_ROWS raises ValueError."""
    monkeypatch.setenv("ROOT_MCP_MAX_EXPORT_ROWS", "lots")
    config = _default_config()
    with pytest.raises(ValueError, match="ROOT_MCP_MAX_EXPORT_ROWS"):
        apply_env_overrides(config)


def test_env_max_export_rows_negative_raises(monkeypatch):
    """ROOT_MCP_MAX_EXPORT_ROWS=-1 raises ValueError."""
    monkeypatch.setenv("ROOT_MCP_MAX_EXPORT_ROWS", "-1")
    config = _default_config()
    with pytest.raises(ValueError, match="> 0"):
        apply_env_overrides(config)


def test_env_max_export_rows_unset_is_noop(monkeypatch):
    """Missing ROOT_MCP_MAX_EXPORT_ROWS leaves default (10_000_000) unchanged."""
    monkeypatch.delenv("ROOT_MCP_MAX_EXPORT_ROWS", raising=False)
    config = _default_config()
    apply_env_overrides(config)
    assert config.core.limits.max_export_rows == 10_000_000


# ---------------------------------------------------------------------------
# apply_env_overrides — cache.enabled
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("val", ["1", "true", "yes", "True", "TRUE"])
def test_env_cache_true_values(monkeypatch, val):
    """Truthy ROOT_MCP_CACHE strings set cache.enabled=True."""
    monkeypatch.setenv("ROOT_MCP_CACHE", val)
    config = _default_config()
    config.core.cache.enabled = False  # start from False
    apply_env_overrides(config)
    assert config.core.cache.enabled is True


@pytest.mark.parametrize("val", ["0", "false", "no", "False"])
def test_env_cache_false_values(monkeypatch, val):
    """Non-truthy ROOT_MCP_CACHE strings set cache.enabled=False."""
    monkeypatch.setenv("ROOT_MCP_CACHE", val)
    config = _default_config()
    apply_env_overrides(config)
    assert config.core.cache.enabled is False


def test_env_cache_unset_is_noop(monkeypatch):
    """Missing ROOT_MCP_CACHE leaves cache.enabled at default (True)."""
    monkeypatch.delenv("ROOT_MCP_CACHE", raising=False)
    config = _default_config()
    apply_env_overrides(config)
    assert config.core.cache.enabled is True


# ---------------------------------------------------------------------------
# apply_env_overrides — cache.file_cache_size
# ---------------------------------------------------------------------------


def test_env_cache_size_integer(monkeypatch):
    """ROOT_MCP_CACHE_SIZE sets core.cache.file_cache_size."""
    monkeypatch.setenv("ROOT_MCP_CACHE_SIZE", "100")
    config = _default_config()
    apply_env_overrides(config)
    assert config.core.cache.file_cache_size == 100


def test_env_cache_size_invalid_raises(monkeypatch):
    """A non-integer ROOT_MCP_CACHE_SIZE raises ValueError."""
    monkeypatch.setenv("ROOT_MCP_CACHE_SIZE", "big")
    config = _default_config()
    with pytest.raises(ValueError, match="ROOT_MCP_CACHE_SIZE"):
        apply_env_overrides(config)


def test_env_cache_size_zero_raises(monkeypatch):
    """ROOT_MCP_CACHE_SIZE=0 raises ValueError."""
    monkeypatch.setenv("ROOT_MCP_CACHE_SIZE", "0")
    config = _default_config()
    with pytest.raises(ValueError, match="> 0"):
        apply_env_overrides(config)


def test_env_cache_size_unset_is_noop(monkeypatch):
    """Missing ROOT_MCP_CACHE_SIZE leaves file_cache_size at default (50)."""
    monkeypatch.delenv("ROOT_MCP_CACHE_SIZE", raising=False)
    config = _default_config()
    apply_env_overrides(config)
    assert config.core.cache.file_cache_size == 50


# ---------------------------------------------------------------------------
# apply_cli_overrides
# ---------------------------------------------------------------------------


def test_cli_max_rows():
    """--max-rows sets max_rows_per_call."""
    config = _default_config()
    apply_cli_overrides(config, _make_args(max_rows=250_000))
    assert config.core.limits.max_rows_per_call == 250_000


def test_cli_max_rows_zero_raises():
    """--max-rows 0 raises ValueError."""
    config = _default_config()
    with pytest.raises(ValueError, match="--max-rows"):
        apply_cli_overrides(config, _make_args(max_rows=0))


def test_cli_max_rows_none_is_noop():
    """args.max_rows=None leaves max_rows_per_call unchanged."""
    config = _default_config()
    apply_cli_overrides(config, _make_args(max_rows=None))
    assert config.core.limits.max_rows_per_call == 1_000_000


def test_cli_max_export_rows():
    """--max-export-rows sets max_export_rows."""
    config = _default_config()
    apply_cli_overrides(config, _make_args(max_export_rows=5_000))
    assert config.core.limits.max_export_rows == 5_000


def test_cli_max_export_rows_zero_raises():
    """--max-export-rows 0 raises ValueError."""
    config = _default_config()
    with pytest.raises(ValueError, match="--max-export-rows"):
        apply_cli_overrides(config, _make_args(max_export_rows=0))


def test_cli_max_export_rows_none_is_noop():
    """args.max_export_rows=None leaves max_export_rows unchanged."""
    config = _default_config()
    apply_cli_overrides(config, _make_args(max_export_rows=None))
    assert config.core.limits.max_export_rows == 10_000_000


def test_cli_no_cache():
    """--no-cache (args.cache_enabled=False) disables the cache."""
    config = _default_config()
    assert config.core.cache.enabled is True
    apply_cli_overrides(config, _make_args(cache_enabled=False))
    assert config.core.cache.enabled is False


def test_cli_cache_enabled_none_is_noop():
    """args.cache_enabled=None (flag not given) leaves cache.enabled unchanged."""
    config = _default_config()
    apply_cli_overrides(config, _make_args(cache_enabled=None))
    assert config.core.cache.enabled is True


def test_cli_cache_size():
    """--cache-size sets file_cache_size."""
    config = _default_config()
    apply_cli_overrides(config, _make_args(cache_size=20))
    assert config.core.cache.file_cache_size == 20


def test_cli_cache_size_zero_raises():
    """--cache-size 0 raises ValueError."""
    config = _default_config()
    with pytest.raises(ValueError, match="--cache-size"):
        apply_cli_overrides(config, _make_args(cache_size=0))


def test_cli_cache_size_none_is_noop():
    """args.cache_size=None leaves file_cache_size at default (50)."""
    config = _default_config()
    apply_cli_overrides(config, _make_args(cache_size=None))
    assert config.core.cache.file_cache_size == 50


# ---------------------------------------------------------------------------
# Priority: CLI beats env var
# ---------------------------------------------------------------------------


def test_cli_max_rows_overrides_env(monkeypatch):
    """CLI --max-rows wins over ROOT_MCP_MAX_ROWS."""
    monkeypatch.setenv("ROOT_MCP_MAX_ROWS", "100")
    config = _default_config()
    apply_env_overrides(config)
    assert config.core.limits.max_rows_per_call == 100
    apply_cli_overrides(config, _make_args(max_rows=9999))
    assert config.core.limits.max_rows_per_call == 9999


def test_cli_no_cache_overrides_env_cache_true(monkeypatch):
    """CLI --no-cache wins even when ROOT_MCP_CACHE=true."""
    monkeypatch.setenv("ROOT_MCP_CACHE", "true")
    config = _default_config()
    apply_env_overrides(config)
    assert config.core.cache.enabled is True
    apply_cli_overrides(config, _make_args(cache_enabled=False))
    assert config.core.cache.enabled is False


def test_cli_cache_size_overrides_env(monkeypatch):
    """CLI --cache-size wins over ROOT_MCP_CACHE_SIZE."""
    monkeypatch.setenv("ROOT_MCP_CACHE_SIZE", "10")
    config = _default_config()
    apply_env_overrides(config)
    assert config.core.cache.file_cache_size == 10
    apply_cli_overrides(config, _make_args(cache_size=200))
    assert config.core.cache.file_cache_size == 200


# ===========================================================================
# Extended Analysis
# ===========================================================================

# ---------------------------------------------------------------------------
# apply_env_overrides — histogram bins
# ---------------------------------------------------------------------------


def test_env_max_bins_1d(monkeypatch):
    """ROOT_MCP_MAX_BINS_1D sets extended.histogram.max_bins_1d."""
    monkeypatch.setenv("ROOT_MCP_MAX_BINS_1D", "500")
    config = _default_config()
    apply_env_overrides(config)
    assert config.extended.histogram.max_bins_1d == 500


def test_env_max_bins_1d_invalid_raises(monkeypatch):
    """A non-integer ROOT_MCP_MAX_BINS_1D raises ValueError."""
    monkeypatch.setenv("ROOT_MCP_MAX_BINS_1D", "many")
    config = _default_config()
    with pytest.raises(ValueError, match="ROOT_MCP_MAX_BINS_1D"):
        apply_env_overrides(config)


def test_env_max_bins_1d_zero_raises(monkeypatch):
    """ROOT_MCP_MAX_BINS_1D=0 raises ValueError."""
    monkeypatch.setenv("ROOT_MCP_MAX_BINS_1D", "0")
    config = _default_config()
    with pytest.raises(ValueError, match="> 0"):
        apply_env_overrides(config)


def test_env_max_bins_1d_unset_is_noop(monkeypatch):
    """Missing ROOT_MCP_MAX_BINS_1D leaves max_bins_1d at default (10_000)."""
    monkeypatch.delenv("ROOT_MCP_MAX_BINS_1D", raising=False)
    config = _default_config()
    apply_env_overrides(config)
    assert config.extended.histogram.max_bins_1d == 10_000


def test_env_max_bins_2d(monkeypatch):
    """ROOT_MCP_MAX_BINS_2D sets extended.histogram.max_bins_2d."""
    monkeypatch.setenv("ROOT_MCP_MAX_BINS_2D", "200")
    config = _default_config()
    apply_env_overrides(config)
    assert config.extended.histogram.max_bins_2d == 200


def test_env_max_bins_2d_unset_is_noop(monkeypatch):
    """Missing ROOT_MCP_MAX_BINS_2D leaves max_bins_2d at default (1_000)."""
    monkeypatch.delenv("ROOT_MCP_MAX_BINS_2D", raising=False)
    config = _default_config()
    apply_env_overrides(config)
    assert config.extended.histogram.max_bins_2d == 1_000


# ---------------------------------------------------------------------------
# apply_env_overrides — fitting_max_iterations
# ---------------------------------------------------------------------------


def test_env_fitting_iterations(monkeypatch):
    """ROOT_MCP_FITTING_ITERATIONS sets extended.fitting_max_iterations."""
    monkeypatch.setenv("ROOT_MCP_FITTING_ITERATIONS", "5000")
    config = _default_config()
    apply_env_overrides(config)
    assert config.extended.fitting_max_iterations == 5000


def test_env_fitting_iterations_invalid_raises(monkeypatch):
    """A non-integer ROOT_MCP_FITTING_ITERATIONS raises ValueError."""
    monkeypatch.setenv("ROOT_MCP_FITTING_ITERATIONS", "inf")
    config = _default_config()
    with pytest.raises(ValueError, match="ROOT_MCP_FITTING_ITERATIONS"):
        apply_env_overrides(config)


def test_env_fitting_iterations_unset_is_noop(monkeypatch):
    """Missing ROOT_MCP_FITTING_ITERATIONS leaves fitting_max_iterations at default."""
    monkeypatch.delenv("ROOT_MCP_FITTING_ITERATIONS", raising=False)
    config = _default_config()
    apply_env_overrides(config)
    assert config.extended.fitting_max_iterations == 10_000


# ---------------------------------------------------------------------------
# apply_env_overrides — plotting.dpi
# ---------------------------------------------------------------------------


def test_env_plot_dpi(monkeypatch):
    """ROOT_MCP_PLOT_DPI sets extended.plotting.dpi."""
    monkeypatch.setenv("ROOT_MCP_PLOT_DPI", "150")
    config = _default_config()
    apply_env_overrides(config)
    assert config.extended.plotting.dpi == 150


def test_env_plot_dpi_invalid_raises(monkeypatch):
    """A non-integer ROOT_MCP_PLOT_DPI raises ValueError."""
    monkeypatch.setenv("ROOT_MCP_PLOT_DPI", "high")
    config = _default_config()
    with pytest.raises(ValueError, match="ROOT_MCP_PLOT_DPI"):
        apply_env_overrides(config)


def test_env_plot_dpi_unset_is_noop(monkeypatch):
    """Missing ROOT_MCP_PLOT_DPI leaves dpi at default (100)."""
    monkeypatch.delenv("ROOT_MCP_PLOT_DPI", raising=False)
    config = _default_config()
    apply_env_overrides(config)
    assert config.extended.plotting.dpi == 100


# ---------------------------------------------------------------------------
# apply_env_overrides — plotting.default_format
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fmt", ["png", "pdf", "svg"])
def test_env_plot_format_valid(monkeypatch, fmt):
    """Each valid ROOT_MCP_PLOT_FORMAT value is accepted."""
    monkeypatch.setenv("ROOT_MCP_PLOT_FORMAT", fmt)
    config = _default_config()
    apply_env_overrides(config)
    assert config.extended.plotting.default_format == fmt


def test_env_plot_format_uppercased_accepted(monkeypatch):
    """ROOT_MCP_PLOT_FORMAT is compared case-insensitively."""
    monkeypatch.setenv("ROOT_MCP_PLOT_FORMAT", "PDF")
    config = _default_config()
    apply_env_overrides(config)
    assert config.extended.plotting.default_format == "pdf"


def test_env_plot_format_invalid_raises(monkeypatch):
    """An unrecognised ROOT_MCP_PLOT_FORMAT raises ValueError."""
    monkeypatch.setenv("ROOT_MCP_PLOT_FORMAT", "bmp")
    config = _default_config()
    with pytest.raises(ValueError, match="ROOT_MCP_PLOT_FORMAT"):
        apply_env_overrides(config)


def test_env_plot_format_unset_is_noop(monkeypatch):
    """Missing ROOT_MCP_PLOT_FORMAT leaves default_format at 'png'."""
    monkeypatch.delenv("ROOT_MCP_PLOT_FORMAT", raising=False)
    config = _default_config()
    apply_env_overrides(config)
    assert config.extended.plotting.default_format == "png"


# ---------------------------------------------------------------------------
# apply_env_overrides — plotting.figure_width / figure_height
# ---------------------------------------------------------------------------


def test_env_plot_width(monkeypatch):
    """ROOT_MCP_PLOT_WIDTH sets extended.plotting.figure_width."""
    monkeypatch.setenv("ROOT_MCP_PLOT_WIDTH", "12.5")
    config = _default_config()
    apply_env_overrides(config)
    assert config.extended.plotting.figure_width == pytest.approx(12.5)


def test_env_plot_width_invalid_raises(monkeypatch):
    """A non-numeric ROOT_MCP_PLOT_WIDTH raises ValueError."""
    monkeypatch.setenv("ROOT_MCP_PLOT_WIDTH", "wide")
    config = _default_config()
    with pytest.raises(ValueError, match="ROOT_MCP_PLOT_WIDTH"):
        apply_env_overrides(config)


def test_env_plot_width_zero_raises(monkeypatch):
    """ROOT_MCP_PLOT_WIDTH=0 raises ValueError."""
    monkeypatch.setenv("ROOT_MCP_PLOT_WIDTH", "0")
    config = _default_config()
    with pytest.raises(ValueError, match="> 0"):
        apply_env_overrides(config)


def test_env_plot_width_unset_is_noop(monkeypatch):
    """Missing ROOT_MCP_PLOT_WIDTH leaves figure_width at default (10.0)."""
    monkeypatch.delenv("ROOT_MCP_PLOT_WIDTH", raising=False)
    config = _default_config()
    apply_env_overrides(config)
    assert config.extended.plotting.figure_width == pytest.approx(10.0)


def test_env_plot_height(monkeypatch):
    """ROOT_MCP_PLOT_HEIGHT sets extended.plotting.figure_height."""
    monkeypatch.setenv("ROOT_MCP_PLOT_HEIGHT", "8.0")
    config = _default_config()
    apply_env_overrides(config)
    assert config.extended.plotting.figure_height == pytest.approx(8.0)


def test_env_plot_height_unset_is_noop(monkeypatch):
    """Missing ROOT_MCP_PLOT_HEIGHT leaves figure_height at default (6.0)."""
    monkeypatch.delenv("ROOT_MCP_PLOT_HEIGHT", raising=False)
    config = _default_config()
    apply_env_overrides(config)
    assert config.extended.plotting.figure_height == pytest.approx(6.0)


# ---------------------------------------------------------------------------
# apply_cli_overrides
# ---------------------------------------------------------------------------


def test_cli_max_bins_1d():
    """--max-bins-1d sets extended.histogram.max_bins_1d."""
    config = _default_config()
    apply_cli_overrides(config, _make_args(max_bins_1d=800))
    assert config.extended.histogram.max_bins_1d == 800


def test_cli_max_bins_1d_none_is_noop():
    """args.max_bins_1d=None leaves max_bins_1d unchanged."""
    config = _default_config()
    apply_cli_overrides(config, _make_args(max_bins_1d=None))
    assert config.extended.histogram.max_bins_1d == 10_000


def test_cli_max_bins_1d_zero_raises():
    """--max-bins-1d 0 raises ValueError."""
    config = _default_config()
    with pytest.raises(ValueError, match="--max-bins-1d"):
        apply_cli_overrides(config, _make_args(max_bins_1d=0))


def test_cli_max_bins_2d():
    """--max-bins-2d sets extended.histogram.max_bins_2d."""
    config = _default_config()
    apply_cli_overrides(config, _make_args(max_bins_2d=50))
    assert config.extended.histogram.max_bins_2d == 50


def test_cli_fitting_iterations():
    """--fitting-iterations sets extended.fitting_max_iterations."""
    config = _default_config()
    apply_cli_overrides(config, _make_args(fitting_iterations=1000))
    assert config.extended.fitting_max_iterations == 1000


def test_cli_fitting_iterations_none_is_noop():
    """args.fitting_iterations=None leaves fitting_max_iterations unchanged."""
    config = _default_config()
    apply_cli_overrides(config, _make_args(fitting_iterations=None))
    assert config.extended.fitting_max_iterations == 10_000


def test_cli_plot_dpi():
    """--plot-dpi sets extended.plotting.dpi."""
    config = _default_config()
    apply_cli_overrides(config, _make_args(plot_dpi=300))
    assert config.extended.plotting.dpi == 300


def test_cli_plot_dpi_zero_raises():
    """--plot-dpi 0 raises ValueError."""
    config = _default_config()
    with pytest.raises(ValueError, match="--plot-dpi"):
        apply_cli_overrides(config, _make_args(plot_dpi=0))


def test_cli_plot_dpi_none_is_noop():
    """args.plot_dpi=None leaves dpi unchanged."""
    config = _default_config()
    apply_cli_overrides(config, _make_args(plot_dpi=None))
    assert config.extended.plotting.dpi == 100


@pytest.mark.parametrize("fmt", ["png", "pdf", "svg"])
def test_cli_plot_format_valid(fmt):
    """Each valid --plot-format value is accepted."""
    config = _default_config()
    apply_cli_overrides(config, _make_args(plot_format=fmt))
    assert config.extended.plotting.default_format == fmt


def test_cli_plot_format_invalid_raises():
    """An invalid --plot-format raises ValueError."""
    config = _default_config()
    with pytest.raises(ValueError, match="--plot-format"):
        apply_cli_overrides(config, _make_args(plot_format="tiff"))


def test_cli_plot_format_none_is_noop():
    """args.plot_format=None leaves default_format unchanged."""
    config = _default_config()
    apply_cli_overrides(config, _make_args(plot_format=None))
    assert config.extended.plotting.default_format == "png"


def test_cli_plot_width():
    """--plot-width sets extended.plotting.figure_width."""
    config = _default_config()
    apply_cli_overrides(config, _make_args(plot_width=14.0))
    assert config.extended.plotting.figure_width == pytest.approx(14.0)


def test_cli_plot_width_zero_raises():
    """--plot-width 0 raises ValueError."""
    config = _default_config()
    with pytest.raises(ValueError, match="--plot-width"):
        apply_cli_overrides(config, _make_args(plot_width=0.0))


def test_cli_plot_width_none_is_noop():
    """args.plot_width=None leaves figure_width unchanged."""
    config = _default_config()
    apply_cli_overrides(config, _make_args(plot_width=None))
    assert config.extended.plotting.figure_width == pytest.approx(10.0)


def test_cli_plot_height():
    """--plot-height sets extended.plotting.figure_height."""
    config = _default_config()
    apply_cli_overrides(config, _make_args(plot_height=4.5))
    assert config.extended.plotting.figure_height == pytest.approx(4.5)


def test_cli_plot_height_none_is_noop():
    """args.plot_height=None leaves figure_height unchanged."""
    config = _default_config()
    apply_cli_overrides(config, _make_args(plot_height=None))
    assert config.extended.plotting.figure_height == pytest.approx(6.0)


# ---------------------------------------------------------------------------
# Priority: CLI beats env var
# ---------------------------------------------------------------------------


def test_cli_max_bins_1d_overrides_env(monkeypatch):
    """CLI --max-bins-1d wins over ROOT_MCP_MAX_BINS_1D."""
    monkeypatch.setenv("ROOT_MCP_MAX_BINS_1D", "100")
    config = _default_config()
    apply_env_overrides(config)
    assert config.extended.histogram.max_bins_1d == 100
    apply_cli_overrides(config, _make_args(max_bins_1d=9999))
    assert config.extended.histogram.max_bins_1d == 9999


def test_cli_plot_format_overrides_env(monkeypatch):
    """CLI --plot-format wins over ROOT_MCP_PLOT_FORMAT."""
    monkeypatch.setenv("ROOT_MCP_PLOT_FORMAT", "pdf")
    config = _default_config()
    apply_env_overrides(config)
    assert config.extended.plotting.default_format == "pdf"
    apply_cli_overrides(config, _make_args(plot_format="svg"))
    assert config.extended.plotting.default_format == "svg"


def test_cli_plot_dpi_overrides_env(monkeypatch):
    """CLI --plot-dpi wins over ROOT_MCP_PLOT_DPI."""
    monkeypatch.setenv("ROOT_MCP_PLOT_DPI", "72")
    config = _default_config()
    apply_env_overrides(config)
    assert config.extended.plotting.dpi == 72
    apply_cli_overrides(config, _make_args(plot_dpi=300))
    assert config.extended.plotting.dpi == 300


# ===========================================================================
# Native ROOT Execution
# ===========================================================================

# ---------------------------------------------------------------------------
# apply_env_overrides — execution_timeout
# ---------------------------------------------------------------------------


def test_env_root_timeout(monkeypatch):
    """ROOT_MCP_ROOT_TIMEOUT sets root_native.execution_timeout."""
    monkeypatch.setenv("ROOT_MCP_ROOT_TIMEOUT", "120")
    config = _default_config()
    apply_env_overrides(config)
    assert config.root_native.execution_timeout == 120


def test_env_root_timeout_invalid_raises(monkeypatch):
    """A non-integer ROOT_MCP_ROOT_TIMEOUT raises ValueError."""
    monkeypatch.setenv("ROOT_MCP_ROOT_TIMEOUT", "forever")
    config = _default_config()
    with pytest.raises(ValueError, match="ROOT_MCP_ROOT_TIMEOUT"):
        apply_env_overrides(config)


def test_env_root_timeout_zero_raises(monkeypatch):
    """ROOT_MCP_ROOT_TIMEOUT=0 raises ValueError."""
    monkeypatch.setenv("ROOT_MCP_ROOT_TIMEOUT", "0")
    config = _default_config()
    with pytest.raises(ValueError, match="> 0"):
        apply_env_overrides(config)


def test_env_root_timeout_unset_is_noop(monkeypatch):
    """Missing ROOT_MCP_ROOT_TIMEOUT leaves execution_timeout at default (60)."""
    monkeypatch.delenv("ROOT_MCP_ROOT_TIMEOUT", raising=False)
    config = _default_config()
    apply_env_overrides(config)
    assert config.root_native.execution_timeout == 60


# ---------------------------------------------------------------------------
# apply_env_overrides — working_directory
# ---------------------------------------------------------------------------


def test_env_root_workdir(monkeypatch):
    """ROOT_MCP_ROOT_WORKDIR sets root_native.working_directory."""
    monkeypatch.setenv("ROOT_MCP_ROOT_WORKDIR", "/custom/workdir")
    config = _default_config()
    apply_env_overrides(config)
    assert config.root_native.working_directory == "/custom/workdir"


def test_env_root_workdir_unset_is_noop(monkeypatch):
    """Missing ROOT_MCP_ROOT_WORKDIR leaves working_directory at default."""
    monkeypatch.delenv("ROOT_MCP_ROOT_WORKDIR", raising=False)
    config = _default_config()
    apply_env_overrides(config)
    assert config.root_native.working_directory == "/tmp/root_mcp_native"


# ---------------------------------------------------------------------------
# apply_env_overrides — max_output_size
# ---------------------------------------------------------------------------


def test_env_root_max_output(monkeypatch):
    """ROOT_MCP_ROOT_MAX_OUTPUT sets root_native.max_output_size."""
    monkeypatch.setenv("ROOT_MCP_ROOT_MAX_OUTPUT", "500000")
    config = _default_config()
    apply_env_overrides(config)
    assert config.root_native.max_output_size == 500000


def test_env_root_max_output_invalid_raises(monkeypatch):
    """A non-integer ROOT_MCP_ROOT_MAX_OUTPUT raises ValueError."""
    monkeypatch.setenv("ROOT_MCP_ROOT_MAX_OUTPUT", "big")
    config = _default_config()
    with pytest.raises(ValueError, match="ROOT_MCP_ROOT_MAX_OUTPUT"):
        apply_env_overrides(config)


def test_env_root_max_output_unset_is_noop(monkeypatch):
    """Missing ROOT_MCP_ROOT_MAX_OUTPUT leaves max_output_size at default."""
    monkeypatch.delenv("ROOT_MCP_ROOT_MAX_OUTPUT", raising=False)
    config = _default_config()
    apply_env_overrides(config)
    assert config.root_native.max_output_size == 10_000_000


# ---------------------------------------------------------------------------
# apply_env_overrides — max_code_length
# ---------------------------------------------------------------------------


def test_env_root_max_code(monkeypatch):
    """ROOT_MCP_ROOT_MAX_CODE sets root_native.max_code_length."""
    monkeypatch.setenv("ROOT_MCP_ROOT_MAX_CODE", "200000")
    config = _default_config()
    apply_env_overrides(config)
    assert config.root_native.max_code_length == 200000


def test_env_root_max_code_unset_is_noop(monkeypatch):
    """Missing ROOT_MCP_ROOT_MAX_CODE leaves max_code_length at default."""
    monkeypatch.delenv("ROOT_MCP_ROOT_MAX_CODE", raising=False)
    config = _default_config()
    apply_env_overrides(config)
    assert config.root_native.max_code_length == 100_000


# ---------------------------------------------------------------------------
# apply_cli_overrides
# ---------------------------------------------------------------------------


def test_cli_root_timeout():
    """--root-timeout sets root_native.execution_timeout."""
    config = _default_config()
    apply_cli_overrides(config, _make_args(root_timeout=90))
    assert config.root_native.execution_timeout == 90


def test_cli_root_timeout_zero_raises():
    """--root-timeout 0 raises ValueError."""
    config = _default_config()
    with pytest.raises(ValueError, match="--root-timeout"):
        apply_cli_overrides(config, _make_args(root_timeout=0))


def test_cli_root_timeout_none_is_noop():
    """args.root_timeout=None leaves execution_timeout unchanged."""
    config = _default_config()
    apply_cli_overrides(config, _make_args(root_timeout=None))
    assert config.root_native.execution_timeout == 60


def test_cli_root_workdir():
    """--root-workdir sets root_native.working_directory."""
    config = _default_config()
    apply_cli_overrides(config, _make_args(root_workdir="/my/workdir"))
    assert config.root_native.working_directory == "/my/workdir"


def test_cli_root_workdir_none_is_noop():
    """args.root_workdir=None leaves working_directory unchanged."""
    config = _default_config()
    apply_cli_overrides(config, _make_args(root_workdir=None))
    assert config.root_native.working_directory == "/tmp/root_mcp_native"


def test_cli_root_max_output():
    """--root-max-output sets root_native.max_output_size."""
    config = _default_config()
    apply_cli_overrides(config, _make_args(root_max_output=9999))
    assert config.root_native.max_output_size == 9999


def test_cli_root_max_output_zero_raises():
    """--root-max-output 0 raises ValueError."""
    config = _default_config()
    with pytest.raises(ValueError, match="--root-max-output"):
        apply_cli_overrides(config, _make_args(root_max_output=0))


def test_cli_root_max_output_none_is_noop():
    """args.root_max_output=None leaves max_output_size unchanged."""
    config = _default_config()
    apply_cli_overrides(config, _make_args(root_max_output=None))
    assert config.root_native.max_output_size == 10_000_000


def test_cli_root_max_code():
    """--root-max-code sets root_native.max_code_length."""
    config = _default_config()
    apply_cli_overrides(config, _make_args(root_max_code=50000))
    assert config.root_native.max_code_length == 50000


def test_cli_root_max_code_none_is_noop():
    """args.root_max_code=None leaves max_code_length unchanged."""
    config = _default_config()
    apply_cli_overrides(config, _make_args(root_max_code=None))
    assert config.root_native.max_code_length == 100_000


# ---------------------------------------------------------------------------
# Priority: CLI beats env var
# ---------------------------------------------------------------------------


def test_cli_root_timeout_overrides_env(monkeypatch):
    """CLI --root-timeout wins over ROOT_MCP_ROOT_TIMEOUT."""
    monkeypatch.setenv("ROOT_MCP_ROOT_TIMEOUT", "30")
    config = _default_config()
    apply_env_overrides(config)
    assert config.root_native.execution_timeout == 30
    apply_cli_overrides(config, _make_args(root_timeout=180))
    assert config.root_native.execution_timeout == 180


def test_cli_root_workdir_overrides_env(monkeypatch):
    """CLI --root-workdir wins over ROOT_MCP_ROOT_WORKDIR."""
    monkeypatch.setenv("ROOT_MCP_ROOT_WORKDIR", "/env/workdir")
    config = _default_config()
    apply_env_overrides(config)
    assert config.root_native.working_directory == "/env/workdir"
    apply_cli_overrides(config, _make_args(root_workdir="/cli/workdir"))
    assert config.root_native.working_directory == "/cli/workdir"


def test_cli_root_max_output_overrides_env(monkeypatch):
    """CLI --root-max-output wins over ROOT_MCP_ROOT_MAX_OUTPUT."""
    monkeypatch.setenv("ROOT_MCP_ROOT_MAX_OUTPUT", "1024")
    config = _default_config()
    apply_env_overrides(config)
    assert config.root_native.max_output_size == 1024
    apply_cli_overrides(config, _make_args(root_max_output=8192))
    assert config.root_native.max_output_size == 8192


# ===========================================================================
# Remote Resources
# ===========================================================================

# ---------------------------------------------------------------------------
# _parse_resource_spec unit tests
# ---------------------------------------------------------------------------


def test_parse_resource_spec_simple():
    """NAME=URI with no description."""
    r = _parse_resource_spec("cms=root://xrootd.cern.ch//store")
    assert r.name == "cms"
    assert r.uri == "root://xrootd.cern.ch//store"
    assert r.description == ""


def test_parse_resource_spec_with_description():
    """NAME=URI|DESCRIPTION parses all three parts."""
    r = _parse_resource_spec("local=file:///data|My local data")
    assert r.name == "local"
    assert r.uri == "file:///data"
    assert r.description == "My local data"


def test_parse_resource_spec_xrootd_with_description():
    """XRootD URI (contains ://) plus description."""
    r = _parse_resource_spec("atlas=root://eos.cern.ch//eos/atlas|ATLAS open data")
    assert r.name == "atlas"
    assert r.uri == "root://eos.cern.ch//eos/atlas"
    assert r.description == "ATLAS open data"


def test_parse_resource_spec_missing_equals_raises():
    """Spec without '=' raises ValueError."""
    with pytest.raises(ValueError, match="NAME=URI"):
        _parse_resource_spec("no-equals-here")


def test_parse_resource_spec_empty_name_raises():
    """Empty name raises ValueError."""
    with pytest.raises(ValueError, match="empty"):
        _parse_resource_spec("=file:///data")


def test_parse_resource_spec_empty_uri_raises():
    """Empty URI raises ValueError."""
    with pytest.raises(ValueError, match="empty"):
        _parse_resource_spec("myname=")


def test_parse_resource_spec_invalid_name_raises():
    """Invalid name (spaces) is rejected by ResourceConfig validator."""
    with pytest.raises(Exception):
        _parse_resource_spec("bad name=file:///data")


# ---------------------------------------------------------------------------
# apply_env_overrides — ROOT_MCP_RESOURCES
# ---------------------------------------------------------------------------


def test_env_resources_single(monkeypatch):
    """ROOT_MCP_RESOURCES with one spec adds a resource."""
    monkeypatch.setenv("ROOT_MCP_RESOURCES", "cms=root://host//store")
    config = _default_config()
    apply_env_overrides(config)
    names = [r.name for r in config.resources]
    assert "cms" in names
    uris = [r.uri for r in config.resources]
    assert "root://host//store" in uris


def test_env_resources_semicolon_separated(monkeypatch):
    """ROOT_MCP_RESOURCES with semicolon-separated specs adds multiple resources."""
    monkeypatch.setenv("ROOT_MCP_RESOURCES", "r1=file:///a;r2=file:///b")
    config = _default_config()
    apply_env_overrides(config)
    names = [r.name for r in config.resources]
    assert "r1" in names
    assert "r2" in names


def test_env_resources_with_description(monkeypatch):
    """ROOT_MCP_RESOURCES spec with | description is stored."""
    monkeypatch.setenv("ROOT_MCP_RESOURCES", "atlas=root://eos//atlas|ATLAS data")
    config = _default_config()
    apply_env_overrides(config)
    r = next(x for x in config.resources if x.name == "atlas")
    assert r.description == "ATLAS data"


def test_env_resources_empty_segment_skipped(monkeypatch):
    """Empty segments between semicolons are silently skipped."""
    monkeypatch.setenv("ROOT_MCP_RESOURCES", "r1=file:///a;;r2=file:///b")
    config = _default_config()
    apply_env_overrides(config)
    names = [r.name for r in config.resources]
    assert "r1" in names
    assert "r2" in names


def test_env_resources_unset_is_noop(monkeypatch):
    """Missing ROOT_MCP_RESOURCES leaves resources unchanged."""
    monkeypatch.delenv("ROOT_MCP_RESOURCES", raising=False)
    config = _default_config()
    before = list(config.resources)
    apply_env_overrides(config)
    assert config.resources == before


def test_env_resources_invalid_spec_raises(monkeypatch):
    """A malformed spec in ROOT_MCP_RESOURCES raises ValueError."""
    monkeypatch.setenv("ROOT_MCP_RESOURCES", "no-equals")
    config = _default_config()
    with pytest.raises(ValueError, match="NAME=URI"):
        apply_env_overrides(config)


# ---------------------------------------------------------------------------
# apply_cli_overrides — --resource
# ---------------------------------------------------------------------------


def test_cli_resource_local():
    """--resource with a local file URI adds the resource."""
    config = _default_config()
    apply_cli_overrides(config, _make_args(resource=["mydata=file:///data"]))
    uris = [r.uri for r in config.resources]
    assert "file:///data" in uris


def test_cli_resource_xrootd():
    """--resource with an XRootD URI adds the resource."""
    config = _default_config()
    apply_cli_overrides(config, _make_args(resource=["cms=root://xrootd.cern.ch//store"]))
    names = [r.name for r in config.resources]
    assert "cms" in names


def test_cli_resource_with_description():
    """--resource NAME=URI|DESCRIPTION stores the description."""
    config = _default_config()
    apply_cli_overrides(config, _make_args(resource=["atlas=root://eos//path|ATLAS open data"]))
    r = next(x for x in config.resources if x.name == "atlas")
    assert r.description == "ATLAS open data"


def test_cli_resource_multiple():
    """Multiple --resource flags each add a distinct resource."""
    config = _default_config()
    apply_cli_overrides(config, _make_args(resource=["r1=file:///a", "r2=file:///b"]))
    names = [r.name for r in config.resources]
    assert "r1" in names
    assert "r2" in names


def test_cli_resource_invalid_format_raises():
    """A malformed --resource spec raises ValueError."""
    config = _default_config()
    with pytest.raises(ValueError, match="NAME=URI"):
        apply_cli_overrides(config, _make_args(resource=["no-equals-sign"]))


def test_cli_resource_none_is_noop():
    """args.resource=None leaves resources unchanged."""
    config = _default_config()
    before = list(config.resources)
    apply_cli_overrides(config, _make_args(resource=None))
    assert config.resources == before


# ---------------------------------------------------------------------------
# Deduplication: YAML-declared URI takes precedence
# ---------------------------------------------------------------------------


def test_resource_deduplicates_with_yaml(monkeypatch):
    """A resource already in config (YAML) is not duplicated by env var."""
    from root_mcp.config import ResourceConfig

    config = _default_config()
    config.resources.append(ResourceConfig(name="existing", uri="root://host//path"))
    before_count = len(config.resources)
    monkeypatch.setenv("ROOT_MCP_RESOURCES", "dup=root://host//path")
    apply_env_overrides(config)
    assert len(config.resources) == before_count  # no new entry added


def test_cli_resource_deduplicates_with_yaml():
    """A CLI --resource with an existing URI is silently skipped."""
    from root_mcp.config import ResourceConfig

    config = _default_config()
    config.resources.append(ResourceConfig(name="existing", uri="file:///mydata"))
    before_count = len(config.resources)
    apply_cli_overrides(config, _make_args(resource=["dup=file:///mydata"]))
    assert len(config.resources) == before_count


# ---------------------------------------------------------------------------
# Priority: CLI beats env var
# ---------------------------------------------------------------------------


def test_cli_resource_overrides_env(monkeypatch):
    """CLI --resource and ROOT_MCP_RESOURCES both add resources (they are additive)."""
    monkeypatch.setenv("ROOT_MCP_RESOURCES", "r_env=file:///env")
    config = _default_config()
    apply_env_overrides(config)
    apply_cli_overrides(config, _make_args(resource=["r_cli=file:///cli"]))
    names = [r.name for r in config.resources]
    assert "r_env" in names
    assert "r_cli" in names


# ===========================================================================
# Log Level
# ===========================================================================


@pytest.fixture()
def restore_log_level():
    """Restore the root logger level after each test so tests don't bleed."""
    original = _logging.root.level
    yield
    _logging.root.setLevel(original)


def test_apply_log_level_debug(restore_log_level):
    """apply_log_level('DEBUG') sets the root logger to DEBUG."""
    apply_log_level("DEBUG")
    assert _logging.root.level == _logging.DEBUG


def test_apply_log_level_info(restore_log_level):
    """apply_log_level('INFO') sets the root logger to INFO."""
    apply_log_level("INFO")
    assert _logging.root.level == _logging.INFO


def test_apply_log_level_warning(restore_log_level):
    """apply_log_level('WARNING') sets the root logger to WARNING."""
    apply_log_level("WARNING")
    assert _logging.root.level == _logging.WARNING


def test_apply_log_level_error(restore_log_level):
    """apply_log_level('ERROR') sets the root logger to ERROR."""
    apply_log_level("ERROR")
    assert _logging.root.level == _logging.ERROR


def test_apply_log_level_case_insensitive(restore_log_level):
    """apply_log_level is case-insensitive (lowercase accepted)."""
    apply_log_level("warning")
    assert _logging.root.level == _logging.WARNING


def test_apply_log_level_mixed_case(restore_log_level):
    """apply_log_level is case-insensitive (mixed case accepted)."""
    apply_log_level("Debug")
    assert _logging.root.level == _logging.DEBUG


def test_apply_log_level_invalid_raises(restore_log_level):
    """An unrecognised level string raises ValueError."""
    with pytest.raises(ValueError, match="Log level must be one of"):
        apply_log_level("VERBOSE")


def test_apply_log_level_empty_raises(restore_log_level):
    """An empty string raises ValueError."""
    with pytest.raises(ValueError):
        apply_log_level("")


def test_env_log_level_debug(monkeypatch, restore_log_level):
    """ROOT_MCP_LOG_LEVEL=DEBUG is respected (simulates main() behaviour)."""
    monkeypatch.setenv("ROOT_MCP_LOG_LEVEL", "DEBUG")
    level_str = os.environ.get("ROOT_MCP_LOG_LEVEL", "").strip().upper()
    apply_log_level(level_str)
    assert _logging.root.level == _logging.DEBUG


def test_env_log_level_case_insensitive(monkeypatch, restore_log_level):
    """ROOT_MCP_LOG_LEVEL is compared case-insensitively."""
    monkeypatch.setenv("ROOT_MCP_LOG_LEVEL", "error")
    level_str = os.environ.get("ROOT_MCP_LOG_LEVEL", "").strip().upper()
    apply_log_level(level_str)
    assert _logging.root.level == _logging.ERROR


def test_cli_log_level_warning(restore_log_level):
    """Calling apply_log_level with 'WARNING' sets WARNING (simulates --log-level WARNING)."""
    apply_log_level("WARNING")
    assert _logging.root.level == _logging.WARNING


def test_cli_log_level_overrides_env(monkeypatch, restore_log_level):
    """CLI --log-level wins over ROOT_MCP_LOG_LEVEL (simulates main() priority)."""
    monkeypatch.setenv("ROOT_MCP_LOG_LEVEL", "DEBUG")
    env_level = os.environ.get("ROOT_MCP_LOG_LEVEL", "").strip().upper()
    cli_level = "ERROR"  # CLI flag wins
    final_level = cli_level or env_level  # CLI takes precedence
    apply_log_level(final_level)
    assert _logging.root.level == _logging.ERROR
