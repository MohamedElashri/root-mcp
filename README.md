# MCP Server for CERN ROOT Files

[![CI](https://github.com/MohamedElashri/root-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/MohamedElashri/root-mcp/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/root-mcp.svg)](https://pypi.org/project/root-mcp/)
[![License](https://img.shields.io/pypi/l/root-mcp.svg)](LICENSE)
[![Language](https://img.shields.io/badge/language-Python-blue.svg)](https://www.python.org/)

A Model Context Protocol (`MCP`) server that provides AI models with safe, high-level access to CERN `ROOT` files and their contents (`TFile`, `TDirectory`, `TTree`, `TBranch`, histograms). Enables declarative, tool-based interaction with `ROOT` data without requiring users to write low-level C++ or `PyROOT` code.

## Quick Start

### Install

```bash
pip install root-mcp
```

Optional XRootD support:

```bash
pip install "root-mcp[xrootd]"
```

### Generate sample ROOT files

```bash
python examples/create_sample_data.py
```

### Configure

Create a config (example):

```yaml
resources:
  - name: "local_data"
    uri: "file:///absolute/path/to/data/root_files"
    description: "Sample ROOT files"
    allowed_patterns: ["*.root"]

security:
  allowed_roots:
    - "/absolute/path/to/data/root_files"
    - "/tmp/root_mcp_output"
  allowed_protocols: ["file"]
```

You can start from the repository example config at `config.yaml`.

### Run

```bash
ROOT_MCP_CONFIG=/path/to/config.yaml root-mcp
```

## Documentation

- `docs/README.md`: complete documentation (tools reference, configuration, Claude Desktop)
- `docs/ARCHITECTURE.md`: architecture and design notes
- `docs/CONTRIBUTING.md`: contributing guidelines

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

## References

- [Model Context Protocol](https://modelcontextprotocol.io/)
- [CERN ROOT](https://root.cern/)
- [uproot](https://github.com/scikit-hep/uproot5)
- [awkward-array](https://github.com/scikit-hep/awkward)

## License

MIT License - see [LICENSE](LICENSE) for details.
