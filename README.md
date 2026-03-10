<p align="center">
  <img src="https://raw.githubusercontent.com/MohamedElashri/root-mcp/main/root-mcp_logo.png" alt="CERN ROOT MCP Server" width="160" />
</p>

<h1 align="center">CERN ROOT MCP Server</h1>

<p align="center">
  An <a href="https://modelcontextprotocol.io/">MCP</a> server and <strong>CLI tool</strong> that allow LLMs to interact with CERN ROOT files.
</p>


[![CI](https://github.com/MohamedElashri/root-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/MohamedElashri/root-mcp/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/root-mcp.svg)](https://pypi.org/project/root-mcp/)
[![License](https://img.shields.io/pypi/l/root-mcp.svg)](LICENSE)
[![Language](https://img.shields.io/badge/language-Python-blue.svg)](https://www.python.org/)

**ROOT-MCP** empowers Large Language Models (LLMs) to natively understand and analyze CERN ROOT files.

By exposing a set of specialized tools via the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) or a token-efficient <strong>CLI interface</strong>, it turns Claude (and other MCP-compliant agents) into capable physics research assistants that can:
- **Inspect** ROOT file structures (Trees, Branches, Histograms)
- **Analyze** data distributions (Compute Histograms, Statistics)
- **Compute** kinematic quantities (Invariant Mass)
- **Visualize** results (Plot 1D/2D histograms directly)
- **Filter** data using physics cuts ("selections")

> **Why this matters**: Instead of asking an LLM to "write a script" that you have to debug and run, you can ask the LLM to *"Check the muon pT distribution in this file"* and it will **just do it**.

---

## Two Interfaces: MCP Server and CLI

ROOT-MCP provides **two ways** to interact with ROOT files:

### 1. MCP Server (for Claude Desktop and MCP clients)
- Full JSON-RPC protocol support
- Structured input/output for programmatic use
- Best for: MCP-compliant LLM clients, automated workflows

### 2. ROOT CLI (`root-cli`)
- Human-readable output by default
- Simpler architecture (no server process)
- Best for: Direct LLM interaction, debugging, scripting

Both interfaces share the same backend and support all 17 analysis tools.

---

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
# MCP Server
root-mcp --data-path /path/to/your/data

# CLI (token-efficient)
root-cli -d /path/to/your/data ls
```

Or set an environment variable once:

```bash
export ROOT_MCP_DATA_PATH=/path/to/your/data
```

---

## ROOT CLI (Recommended for LLM Interaction)

The CLI provides a **token-efficient**, human-readable interface that saves ~60% tokens compared to the MCP JSON protocol.

### Basic Usage

```bash
# List files
root-cli ls

# Inspect a file
root-cli inspect /data/sample.root

# Create histogram with fit
root-cli histogram /data/sample.root events muon_pt --bins 100 --fit gaussian

# Read data with selection
root-cli read /data/sample.root events met muon_pt --selection "met > 50"

# Plot results
root-cli plot1d /tmp/root_mcp/muon_pt_hist.json -o plot.png --title "Muon pT"
```

### Example LLM Workflow

Ask your LLM: *"Plot the muon pT distribution"*

The LLM generates:
```bash
root-cli histogram /data/sample.root events muon_pt --bins 50 && \
root-cli plot1d /tmp/root_mcp/muon_pt_hist.json -o muon_pt.png --title "Muon pT Distribution"
```


### Documentation

See [`docs/skills/root-cli.md`](docs/skills/root-cli.md) for complete command reference with examples.

---

## MCP Server

### Zero-config one-liners:

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

### Run with Claude Desktop

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

## Documentation

The full documentation site is built with Sphinx and covers installation,
configuration, all 20 MCP tools, LLM integration patterns, and the developer
guide with auto-generated API reference.

**Read online**: The docs are hosted at [root-mcp docs](https://melashri.net/root-mcp)

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
- **[CLI Reference](docs/skills/root-cli.md)** — complete command reference for root-cli with examples
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
