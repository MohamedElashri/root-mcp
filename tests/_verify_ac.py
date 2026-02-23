#!/usr/bin/env python
"""Quick acceptance-criteria spot-checks — complement to test_env_cli_overrides.py."""

import os
import sys
import logging
import types

sys.path.insert(0, "src")
from root_mcp.config import (
    load_config,
    apply_env_overrides,
    apply_cli_overrides,
    apply_log_level,
)


def fresh():
    return load_config(None)


OK = []
FAIL = []


def chk(name, val):
    if val:
        OK.append(name)
    else:
        FAIL.append(name)


def make_args(**kw):
    d = dict(
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
    d.update(kw)
    return types.SimpleNamespace(**d)


# ── AC2: each env var sets its field; unset is noop ───────────────────────────
scalar = [
    ("ROOT_MCP_MODE", lambda c: c.server.mode, "core"),
    ("ROOT_MCP_SERVER_NAME", lambda c: c.server.name, "myserver"),
    ("ROOT_MCP_MAX_PATH_DEPTH", lambda c: c.security.max_path_depth, 5),
    ("ROOT_MCP_MAX_ROWS", lambda c: c.core.limits.max_rows_per_call, 999),
    ("ROOT_MCP_CACHE_SIZE", lambda c: c.core.cache.file_cache_size, 7),
    ("ROOT_MCP_MAX_BINS_1D", lambda c: c.extended.histogram.max_bins_1d, 42),
    ("ROOT_MCP_FITTING_ITERATIONS", lambda c: c.extended.fitting_max_iterations, 123),
    ("ROOT_MCP_PLOT_DPI", lambda c: c.extended.plotting.dpi, 72),
    ("ROOT_MCP_PLOT_FORMAT", lambda c: c.extended.plotting.default_format, "pdf"),
    ("ROOT_MCP_ROOT_TIMEOUT", lambda c: c.root_native.execution_timeout, 30),
    ("ROOT_MCP_ROOT_WORKDIR", lambda c: c.root_native.working_directory, "/custom/wd"),
    ("ROOT_MCP_ROOT_MAX_OUTPUT", lambda c: c.root_native.max_output_size, 1234),
    ("ROOT_MCP_ROOT_MAX_CODE", lambda c: c.root_native.max_code_length, 500),
]
for var, getter, val in scalar:
    os.environ[var] = str(val)
    c = fresh()
    apply_env_overrides(c)
    chk(f"AC2 {var} set", getter(c) == val)
    del os.environ[var]
    c2 = fresh()
    apply_env_overrides(c2)
    chk(f"AC2 {var} unset→noop", getter(c2) != val)

os.environ["ROOT_MCP_ALLOW_REMOTE"] = "1"
c = fresh()
apply_env_overrides(c)
chk("AC2 ALLOW_REMOTE=1", c.security.allow_remote is True)
del os.environ["ROOT_MCP_ALLOW_REMOTE"]

os.environ["ROOT_MCP_ALLOWED_ROOTS"] = "/a:/b"
c = fresh()
apply_env_overrides(c)
chk("AC2 ALLOWED_ROOTS colon-sep", c.security.allowed_roots == ["/a", "/b"])
del os.environ["ROOT_MCP_ALLOWED_ROOTS"]

os.environ["ROOT_MCP_EXPORT_FORMATS"] = "json,csv"
c = fresh()
apply_env_overrides(c)
chk("AC2 EXPORT_FORMATS", c.output.allowed_formats == ["json", "csv"])
del os.environ["ROOT_MCP_EXPORT_FORMATS"]

os.environ["ROOT_MCP_ENABLE_EXPORT"] = "0"
c = fresh()
apply_env_overrides(c)
chk("AC2 ENABLE_EXPORT=0", c.features.enable_export is False)
del os.environ["ROOT_MCP_ENABLE_EXPORT"]

os.environ["ROOT_MCP_CACHE"] = "0"
c = fresh()
apply_env_overrides(c)
chk("AC2 CACHE=0", c.core.cache.enabled is False)
del os.environ["ROOT_MCP_CACHE"]

os.environ["ROOT_MCP_RESOURCES"] = "r1=file:///x;r2=root://host//path|My data"
c = fresh()
apply_env_overrides(c)
names = [r.name for r in c.resources]
chk("AC2 RESOURCES r1+r2 parsed", "r1" in names and "r2" in names)
del os.environ["ROOT_MCP_RESOURCES"]

orig_level = logging.root.level
apply_log_level("ERROR")
chk("AC2 LOG_LEVEL ERROR", logging.root.level == logging.ERROR)
logging.root.setLevel(orig_level)

# ── AC3: CLI beats env var ────────────────────────────────────────────────────
os.environ["ROOT_MCP_MODE"] = "core"
c = fresh()
apply_env_overrides(c)
apply_cli_overrides(c, make_args(mode="extended"))
chk("AC3 CLI mode beats env", c.server.mode == "extended")
del os.environ["ROOT_MCP_MODE"]

os.environ["ROOT_MCP_CACHE_SIZE"] = "5"
c = fresh()
apply_env_overrides(c)
apply_cli_overrides(c, make_args(cache_size=99))
chk("AC3 CLI cache_size beats env", c.core.cache.file_cache_size == 99)
del os.environ["ROOT_MCP_CACHE_SIZE"]

os.environ["ROOT_MCP_ROOT_TIMEOUT"] = "10"
c = fresh()
apply_env_overrides(c)
apply_cli_overrides(c, make_args(root_timeout=200))
chk("AC3 CLI root_timeout beats env", c.root_native.execution_timeout == 200)
del os.environ["ROOT_MCP_ROOT_TIMEOUT"]

os.environ["ROOT_MCP_PLOT_FORMAT"] = "png"
c = fresh()
apply_env_overrides(c)
apply_cli_overrides(c, make_args(plot_format="pdf"))
chk("AC3 CLI plot_format beats env", c.extended.plotting.default_format == "pdf")
del os.environ["ROOT_MCP_PLOT_FORMAT"]


# ── AC5: bad type/value → ValueError ─────────────────────────────────────────
def bad_env(var, val):
    os.environ[var] = val
    try:
        apply_env_overrides(fresh())
        return False
    except ValueError:
        return True
    finally:
        os.environ.pop(var, None)


for var, bad in [
    ("ROOT_MCP_MODE", "badmode"),
    ("ROOT_MCP_MAX_ROWS", "abc"),
    ("ROOT_MCP_CACHE_SIZE", "zero"),
    ("ROOT_MCP_MAX_BINS_1D", "notanint"),
    ("ROOT_MCP_PLOT_FORMAT", "bmp"),
    ("ROOT_MCP_ROOT_TIMEOUT", "never"),
    ("ROOT_MCP_RESOURCES", "no-equals"),
]:
    chk(f"AC5 {var}={bad!r}→ValueError", bad_env(var, bad))

for var in [
    "ROOT_MCP_MAX_ROWS",
    "ROOT_MCP_CACHE_SIZE",
    "ROOT_MCP_MAX_BINS_1D",
    "ROOT_MCP_ROOT_TIMEOUT",
]:
    chk(f"AC5 {var}=0→ValueError", bad_env(var, "0"))

# ── AC8: Worked examples without config.yaml ─────────────────────────────────
# 1) Docker / env-only
os.environ.update(
    {
        "ROOT_MCP_MODE": "extended",
        "ROOT_MCP_ROOT_TIMEOUT": "120",
        "ROOT_MCP_ALLOWED_ROOTS": "/data:/exports",
    }
)
c = fresh()
apply_env_overrides(c)
chk("AC8 Docker env-only", c.server.mode == "extended" and c.root_native.execution_timeout == 120)
for k in ["ROOT_MCP_MODE", "ROOT_MCP_ROOT_TIMEOUT", "ROOT_MCP_ALLOWED_ROOTS"]:
    del os.environ[k]

# 2) Claude Desktop JSON args
c = fresh()
apply_cli_overrides(c, make_args(mode="extended", root_timeout=120))
chk(
    "AC8 Claude Desktop CLI args",
    c.server.mode == "extended" and c.root_native.execution_timeout == 120,
)

# 3) XRootD resource (no config.yaml)
c = fresh()
apply_cli_overrides(
    c,
    make_args(
        resource=["cms=root://xrootd.cern.ch//store/data"], allow_remote=True, mode="extended"
    ),
)
chk(
    "AC8 XRootD --resource flag",
    any(r.name == "cms" for r in c.resources) and c.security.allow_remote,
)

# 4) Restricted production
c = fresh()
apply_cli_overrides(
    c, make_args(allowed_root=["/data/physics", "/tmp/exports"], max_rows=100000, cache_size=10)
)
chk(
    "AC8 restricted production",
    c.core.limits.max_rows_per_call == 100000 and c.core.cache.file_cache_size == 10,
)

# ── Print results ─────────────────────────────────────────────────────────────
total = len(OK) + len(FAIL)
print(f"\n{'='*55}")
print(f"Acceptance criteria spot-checks: {len(OK)}/{total} passed")
if FAIL:
    print(f"\nFAILED ({len(FAIL)}):")
    for f in FAIL:
        print(f"  ✗ {f}")
    sys.exit(1)
else:
    print("All checks PASSED ✓")
    print("\nCriteria covered:")
    print("  AC2 – every ROOT_MCP_* env var honoured; unset is noop")
    print("  AC3 – CLI flag always beats env var")
    print("  AC5 – invalid values raise ValueError")
    print("  AC8 – all worked examples parse without config.yaml")
