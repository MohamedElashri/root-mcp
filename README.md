# ROOT-MCP: LLM Powered HEP Analysis

[![CI](https://github.com/MohamedElashri/root-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/MohamedElashri/root-mcp/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/root-mcp.svg)](https://pypi.org/project/root-mcp/)
[![License](https://img.shields.io/pypi/l/root-mcp.svg)](LICENSE)
[![Language](https://img.shields.io/badge/language-Python-blue.svg)](https://www.python.org/)

**ROOT-MCP** empowers Large Language Models (LLMs) to natively understand and analyze CERN ROOT files.

By exposing a set of specialized tools via the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/), it turns Claude (and other MCP-compliant agents) into capable physics research assistants that can:
- **Inspect** ROOT file structures (Trees, Branches, Histograms)
- **Analyze** data distributions (Compute Histograms, Statistics)
- **Compute** kinematic quantities (invariant masses, angular correlations for Dalitz plots)
- **Visualize** results directly in the chat
- **Filter** data using physics cuts ("selections")

> **Why this matters**: Instead of asking an LLM to "write a script" that you have to debug and run, you can ask the LLM to *"Check the muon pT distribution in this file"* and it will **just do it**.

---

## Architecture

ROOT-MCP features a **dual-mode architecture**:

- **Core Mode**: File I/O, data reading, and basic statistics
- **Extended Mode**: Full analysis capabilities including fitting, kinematics, and correlations

The mode is controlled via configuration, and the server automatically loads only the components you need. Runtime mode switching is also available.

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

Create a `config.yaml` and set your preferred mode:

```yaml
# Server settings
server:
  name: "root-mcp"
  mode: "extended"  # Options: "core" or "extended"

# Data resources
resources:
  - name: "my_analysis"
    uri: "file:///Users/me/data"
    allowed_patterns: ["*.root"]

# Security
security:
  allowed_roots:
    - "/Users/me/data"

# Output directory for exports
output:
  export_base_path: "/Users/me/exports"
```

**Mode Selection:**
- `mode: "core"` - Lightweight mode for file operations and basic statistics
- `mode: "extended"` - Full analysis features (histograms, fitting, kinematics, correlations)

You can switch modes at runtime using the `switch_mode` tool without restarting the server.

### 3. Run with Claude Desktop

Add to your `claude_desktop_config.json`:

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

- **[Full Documentation](docs/README.md)**: The complete guide.
- **[Tool Reference](docs/api/tools.md)**: Detailed API definition for all tools.
- **[LLM Integration Guide](docs/guides/llm_integration.md)**: How to prompt and work with the agent.

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
