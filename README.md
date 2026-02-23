# ROOT-MCP: LLM Powered HEP Analysis

[![CI](https://github.com/MohamedElashri/root-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/MohamedElashri/root-mcp/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/root-mcp.svg)](https://pypi.org/project/root-mcp/)
[![License](https://img.shields.io/pypi/l/root-mcp.svg)](LICENSE)
[![Language](https://img.shields.io/badge/language-Python-blue.svg)](https://www.python.org/)

**ROOT-MCP** empowers Large Language Models (LLMs) to natively understand and analyze CERN ROOT files.

By exposing a set of specialized tools via the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/), it turns Claude (and other MCP-compliant agents) into capable physics research assistants that can:
- **Inspect** ROOT file structures (Trees, Branches, Histograms)
- **Analyze** data distributions (Compute Histograms, Statistics)
- **Compute** kinematic quantities (Invariant Mass)
- **Visualize** results (Plot 1D/2D histograms directly)
- **Filter** data using physics cuts ("selections")

> **Why this matters**: Instead of asking an LLM to "write a script" that you have to debug and run, you can ask the LLM to *"Check the muon pT distribution in this file"* and it will **just do it**.

---

## Architecture

ROOT-MCP features a **dual-mode architecture**:

- **Core Mode**: File I/O, data reading, and basic statistics
- **Extended Mode**: Full analysis capabilities including fitting, kinematics, and correlations

The mode is controlled via configuration, and the server automatically loads only the components you need. Runtime mode switching is also available.

### Optional Native ROOT Support

ROOT-MCP can optionally integrate with a native [ROOT/PyROOT](https://root.cern/) installation to unlock capabilities beyond what `uproot` provides:

- **`run_root_code`**: Execute arbitrary PyROOT/Python code and get structured results
- **`run_rdataframe`**: Compute histograms using ROOT's RDataFrame (no boilerplate needed)
- **`run_root_macro`**: Execute C++ ROOT macros via `gROOT.ProcessLine`

This feature is **entirely optional** — ROOT-MCP works fully without ROOT installed. When ROOT is available and enabled, these additional tools appear automatically.

**Requirements**: A working ROOT installation (via [conda-forge](https://anaconda.org/conda-forge/root), system package, or binary tarball). ROOT is not pip-installable at this time.

**Enable it** by setting `enable_root: true` in your `config.yaml`:

```yaml
features:
  enable_root: true

# Optional: tune execution settings
root_native:
  execution_timeout: 60
  working_directory: "/tmp/root_mcp_native"
```

Use `get_server_info` to check ROOT availability at runtime:
```json
{
  "root_native_available": true,
  "root_native_enabled": true,
  "root_version": "6.32/02",
  "root_features": {"rdataframe": true, "roofit": true, "tmva": false}
}
```

## Quick Start

### 1. Install

```bash
pip install root-mcp
```

Optional: For remote file access via XRootD protocol:
```bash
pip install "root-mcp[xrootd]"
```

### 2. Configure

**Fastest path — no config file needed:**

```bash
root-mcp --data-path /path/to/your/data
```

Or set an environment variable once:

```bash
export ROOT_MCP_DATA_PATH=/path/to/your/data
```

**Zero-config one-liners:**

```bash
# Core mode (lightweight, no scipy/matplotlib needed)
root-mcp --data-path /data --mode core

# Extended mode with native ROOT, restricted to one directory
root-mcp --data-path /data --enable-root --allowed-root /data

# Remote XRootD resource, no YAML needed
root-mcp --resource cms=root://xrootd.cern.ch//store --allow-remote --mode extended

# Docker / container — fully env-var driven
ROOT_MCP_DATA_PATH=/data ROOT_MCP_MODE=extended ROOT_MCP_EXPORT_PATH=/exports root-mcp

# Quiet server (only warnings+) with a cache increase
root-mcp --data-path /data --log-level WARNING --cache-size 100
```

**Generate a starter config (optional):**

```bash
root-mcp init --permissive   # creates config.yaml pre-filled with current directory
```

**Manual config file** — for persistent settings, remote resources, or native ROOT:

```yaml
server:
  mode: "extended"   # "core" or "extended"

resources:
  - name: "my_analysis"
    uri: "file:///path/to/data"
    allowed_patterns: ["*.root"]

security:
  allowed_roots: []  # empty = any local path is accessible (permissive)
```

**Mode Selection:**
- `mode: "core"` — Lightweight: file operations and basic statistics
- `mode: "extended"` — Full analysis: histograms, fitting, kinematics, correlations

Switch modes at runtime with the `switch_mode` tool — no restart required.

### 3. Run with Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "root-mcp": {
      "command": "root-mcp",
      "args": ["--data-path", "/path/to/your/data"]
    }
  }
}
```

Or with a persistent config file:

```json
{
  "mcpServers": {
    "root-mcp": {
      "command": "root-mcp",
      "env": {
        "ROOT_MCP_CONFIG": "/path/to/config.yaml"
      }
    }
  }
}
```

## Documentation

The full documentation site is built with Sphinx and covers installation,
configuration, all 20 MCP tools, LLM integration patterns, and the developer
guide with auto-generated API reference.

**Read online**: see the `docs/` directory on GitHub, or build locally:

```bash
pip install "root-mcp[docs]"
./scripts/build_docs.sh
# open docs/_build/html/index.html
```

For live-reload while writing docs:

```bash
cd docs && make livehtml
```

Highlights:
- **[User Guide](docs/user/)** — installation, quickstart, modes, configuration, LLM integration
- **[Tool Reference](docs/api/tools.md)** — complete catalogue of all tools and their JSON payloads
- **[Developer Guide](docs/developer/)** — architecture, module overview, dev setup, contributing
- **[API Reference](docs/apidoc/)** — auto-generated from source docstrings

## Citation

If you use ROOT-MCP in your research, please cite:

```bibtex
@software{root_mcp,
  title = {ROOT-MCP: Production-Grade MCP Server for CERN ROOT Files},
  author = {Mohamed Elashri},
  year = {2025},
  url = {https://github.com/MohamedElashri/root-mcp}
}
```
## License

MIT License - see [LICENSE](LICENSE) for details.
