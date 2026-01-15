# Tool Reference

Complete reference for all ROOT-MCP tools, organized by mode availability.

## Tool Organization

ROOT-MCP provides **15 tools** organized into two categories:

- **Core Tools (9)**: Always available in both core and extended modes
- **Extended Tools (6)**: Only available in extended mode

All tools return a standard JSON response structure:

```json
{
  "data": { ... },       // Primary result
  "metadata": { ... },   // Operation details, execution time
  "suggestions": [ ... ] // Optional next steps or hints
}
```

## Mode Information

Check current mode and available tools:

```json
{
  "tool": "get_server_info",
  "arguments": {}
}
```

Switch modes at runtime:

```json
{
  "tool": "switch_mode",
  "arguments": {"mode": "extended"}
}
```

---

# Core Tools

Core tools are **always available** in both core and extended modes. They provide file operations, data reading, and basic statistics.

## File Discovery

### `list_files`

List accessible ROOT files under a configured resource.

**Mode**: Core (always available)

**Arguments**:

| Name | Type | Required | Description | Default |
|------|------|----------|-------------|---------|
| `resource` | `string` | No | Resource ID from config | First resource |
| `pattern` | `string` | No | Glob pattern (e.g., `'run_*.root'`) | `*` |
| `limit` | `integer` | No | Maximum files to return | `100` |

**Example**:

```json
{
  "tool": "list_files",
  "arguments": {
    "pattern": "*.root",
    "limit": 10
  }
}
```

**Response**:

```json
{
  "data": {
    "files": [
      {
        "path": "/data/sample.root",
        "size_bytes": 1306965,
        "size_human": "1.2 MB",
        "modified": "2024-05-14T10:45:17",
        "resource": "local_data"
      }
    ],
    "total_matched": 1,
    "total_scanned": 1
  }
}
```

---

### `inspect_file`

Inspect ROOT file structure including trees, histograms, and directories.

**Mode**: Core (always available)

**Arguments**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `path` | `string` | Yes | Absolute path to ROOT file |
| `include_histograms` | `boolean` | No | Include histogram metadata |
| `include_trees` | `boolean` | No | Include TTree metadata |

**Example**:

```json
{
  "tool": "inspect_file",
  "arguments": {
    "path": "/data/sample.root"
  }
}
```

**Response**:

```json
{
  "data": {
    "path": "/data/sample.root",
    "size_bytes": 1306965,
    "trees": [
      {
        "name": "events",
        "entries": 10000,
        "branches": 26,
        "total_bytes": 1200000
      }
    ],
    "histograms": [],
    "directories": []
  }
}
```

---

### `list_branches`

List branches in a TTree with type information.

**Mode**: Core (always available)

**Arguments**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `path` | `string` | Yes | Absolute path to ROOT file |
| `tree` | `string` | Yes | TTree name (e.g., `"events"`) |
| `pattern` | `string` | No | Glob pattern (e.g., `"muon_*"`) |
| `limit` | `integer` | No | Maximum branches to return |
| `include_stats` | `boolean` | No | Compute statistics (slower) |

**Example**:

```json
{
  "tool": "list_branches",
  "arguments": {
    "path": "/data/sample.root",
    "tree": "events",
    "pattern": "muon_*"
  }
}
```

**Response**:

```json
{
  "data": {
    "tree": "events",
    "total_entries": 10000,
    "branches": [
      {
        "name": "muon_pt",
        "type": "float32",
        "is_jagged": true,
        "interpretation": "var * float32"
      },
      {
        "name": "muon_eta",
        "type": "float32",
        "is_jagged": true
      }
    ]
  }
}
```

---

### `validate_file`

Check ROOT file integrity and readability.

**Mode**: Core (always available)

**Arguments**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `path` | `string` | Yes | Absolute path to ROOT file |

**Example**:

```json
{
  "tool": "validate_file",
  "arguments": {
    "path": "/data/sample.root"
  }
}
```

**Response**:

```json
{
  "data": {
    "valid": true,
    "readable": true,
    "warnings": [],
    "metadata": {
      "num_objects": 5,
      "num_trees": 1,
      "trees": ["events"],
      "compression_ratio": 2.3
    }
  }
}
```

---

## Data Access

### `read_branches`

Read branch data from TTree with optional filtering and derived branches.

**Mode**: Core (always available)

**Arguments**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `path` | `string` | Yes | Absolute path to ROOT file |
| `tree` | `string` | Yes | TTree name |
| `branches` | `string[]` | Yes | Branch names (physical or derived) |
| `selection` | `string` | No | Cut expression (e.g., `'pt > 20'`) |
| `limit` | `integer` | No | Maximum entries to return |
| `offset` | `integer` | No | Number of entries to skip |
| `flatten` | `boolean` | No | Flatten jagged arrays |
| `defines` | `object` | No | Derived variables `{name: expr}` |

**Example (Basic)**:

```json
{
  "tool": "read_branches",
  "arguments": {
    "path": "/data/sample.root",
    "tree": "events",
    "branches": ["muon_pt", "muon_eta"],
    "selection": "muon_pt > 20",
    "limit": 100
  }
}
```

**Example (Derived Branches)**:

```json
{
  "tool": "read_branches",
  "arguments": {
    "path": "/data/sample.root",
    "tree": "events",
    "branches": ["met", "met_x", "met_y"],
    "defines": {
      "met_x": "met * cos(met_phi)",
      "met_y": "met * sin(met_phi)"
    },
    "selection": "met > 50"
  }
}
```

**Response**:

```json
{
  "data": {
    "branches": ["muon_pt", "muon_eta"],
    "entries": 100,
    "is_jagged": true,
    "records": [
      {"muon_pt": [25.3, 30.1], "muon_eta": [1.2, -0.5]},
      {"muon_pt": [45.7], "muon_eta": [0.8]}
    ]
  },
  "metadata": {
    "entries_selected": 100,
    "selection": "muon_pt > 20"
  }
}
```

---

### `get_branch_stats`

Compute basic statistics for branches.

**Mode**: Core (always available)

**Arguments**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `path` | `string` | Yes | Absolute path to ROOT file |
| `tree` | `string` | Yes | TTree name |
| `branches` | `string[]` | Yes | Branch names |
| `selection` | `string` | No | Optional cut expression |

**Example**:

```json
{
  "tool": "get_branch_stats",
  "arguments": {
    "path": "/data/sample.root",
    "tree": "events",
    "branches": ["met", "muon_pt"]
  }
}
```

**Response**:

```json
{
  "data": {
    "met": {
      "count": 10000,
      "mean": 45.2,
      "std": 28.3,
      "min": 0.0,
      "max": 250.5,
      "median": 38.7,
      "percentiles": {
        "25": 25.1,
        "75": 60.3
      }
    },
    "muon_pt": {
      "count": 15234,
      "mean": 35.6,
      "std": 22.1,
      "min": 10.0,
      "max": 180.2
    }
  }
}
```

---

## Data Export

### `export_data`

Export branch data to JSON, CSV, or Parquet format.

**Mode**: Core (always available)

**Arguments**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `path` | `string` | Yes | Input ROOT file path |
| `tree` | `string` | Yes | TTree name |
| `branches` | `string[]` | Yes | Branches to export |
| `output_path` | `string` | Yes | Output file path |
| `format` | `string` | Yes | `"json"`, `"csv"`, or `"parquet"` |
| `selection` | `string` | No | Optional cut expression |
| `limit` | `integer` | No | Maximum entries to export |
| `compress` | `boolean` | No | Compress output (gzip) |

**Example**:

```json
{
  "tool": "export_data",
  "arguments": {
    "path": "/data/sample.root",
    "tree": "events",
    "branches": ["run", "event", "met"],
    "output_path": "/exports/data.parquet",
    "format": "parquet",
    "selection": "met > 50"
  }
}
```

**Response**:

```json
{
  "data": {
    "output_path": "/exports/data.parquet",
    "format": "parquet",
    "entries_exported": 1823,
    "file_size_bytes": 45678,
    "compressed": false
  }
}
```

---

## Server Management

### `switch_mode`

Switch between core and extended modes at runtime.

**Mode**: Core (always available)

**Arguments**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `mode` | `string` | Yes | `"core"` or `"extended"` |

**Example**:

```json
{
  "tool": "switch_mode",
  "arguments": {
    "mode": "extended"
  }
}
```

**Response**:

```json
{
  "status": "success",
  "previous_mode": "core",
  "current_mode": "extended",
  "message": "Switched from core to extended mode",
  "extended_features_available": true
}
```

---

### `get_server_info`

Get server information including current mode and capabilities.

**Mode**: Core (always available)

**Arguments**: None

**Example**:

```json
{
  "tool": "get_server_info",
  "arguments": {}
}
```

**Response**:

```json
{
  "server_name": "root-mcp",
  "version": "0.1.2",
  "current_mode": "extended",
  "extended_components_loaded": true,
  "available_modes": ["core", "extended"],
  "capabilities": {
    "core_tools": 9,
    "extended_tools": 6,
    "total_tools": 15
  }
}
```

---

# Extended Tools

Extended tools are **only available in extended mode**. They require scipy and matplotlib and provide advanced analysis capabilities.

If you try to use an extended tool in core mode, you'll receive an error:

```json
{
  "error": "mode_error",
  "message": "Tool 'fit_histogram' requires extended mode. Current mode: core",
  "hint": "Use switch_mode tool to enable extended mode"
}
```

## Histogram Analysis

### `compute_histogram`

Create 1D histogram with optional fitting support.

**Mode**: Extended only

**Arguments**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `path` | `string` | Yes | ROOT file path |
| `tree` | `string` | Yes | TTree name |
| `branch` | `string` | Yes | Branch to histogram |
| `bins` | `integer` | Yes | Number of bins |
| `range` | `[min, max]` | No | Range (auto if omitted) |
| `selection` | `string` | No | Cut expression |
| `weights` | `string` | No | Weight branch name |
| `fit_model` | `string` | No | Model: `"gaussian"`, `"exponential"`, `"polynomial"`, `"crystal_ball"` |
| `fit_range` | `[min, max]` | No | Fit range |

**Example**:

```json
{
  "tool": "compute_histogram",
  "arguments": {
    "path": "/data/sample.root",
    "tree": "events",
    "branch": "dimuon_mass",
    "bins": 100,
    "range": [2.8, 3.4],
    "fit_model": "gaussian",
    "fit_range": [3.0, 3.2]
  }
}
```

**Response**:

```json
{
  "data": {
    "bin_edges": [2.8, 2.806, ..., 3.4],
    "bin_counts": [45, 52, ..., 38],
    "bin_errors": [6.7, 7.2, ..., 6.2],
    "mean": 3.096,
    "std": 0.093,
    "fit": {
      "model": "gaussian",
      "parameters": {
        "amplitude": 1250.5,
        "mean": 3.0969,
        "sigma": 0.0432
      },
      "errors": {
        "amplitude": 15.2,
        "mean": 0.0003,
        "sigma": 0.0004
      },
      "chi2": 45.3,
      "ndof": 47,
      "chi2_ndof": 0.96
    }
  }
}
```

---

### `compute_histogram_2d`

Create 2D histogram for correlation studies.

**Mode**: Extended only

**Arguments**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `path` | `string` | Yes | ROOT file path |
| `tree` | `string` | Yes | TTree name |
| `branch_x` | `string` | Yes | X-axis branch |
| `branch_y` | `string` | Yes | Y-axis branch |
| `bins_x` | `integer` | Yes | Number of X bins |
| `bins_y` | `integer` | Yes | Number of Y bins |
| `range_x` | `[min, max]` | No | X range |
| `range_y` | `[min, max]` | No | Y range |
| `selection` | `string` | No | Cut expression |

**Example**:

```json
{
  "tool": "compute_histogram_2d",
  "arguments": {
    "path": "/data/sample.root",
    "tree": "events",
    "branch_x": "muon_eta",
    "branch_y": "muon_phi",
    "bins_x": 50,
    "bins_y": 50,
    "range_x": [-2.5, 2.5],
    "range_y": [-3.14, 3.14]
  }
}
```

**Response**:

```json
{
  "data": {
    "bin_edges_x": [-2.5, -2.4, ..., 2.5],
    "bin_edges_y": [-3.14, -3.01, ..., 3.14],
    "bin_counts": [[12, 15, ...], [18, 20, ...], ...],
    "total_entries": 10000
  }
}
```

---

### `fit_histogram`

Fit mathematical model to existing histogram data.

**Mode**: Extended only

**Arguments**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `bin_centers` | `number[]` | Yes | Histogram bin centers |
| `bin_counts` | `number[]` | Yes | Histogram bin counts |
| `model` | `string` | Yes | Model name (see below) |
| `initial_params` | `object` | No | Initial parameter guesses |
| `fixed_params` | `object` | No | Fixed parameters |
| `bounds` | `object` | No | Parameter bounds |

**Available Models**:
- `gaussian`: Normal distribution
- `exponential`: Exponential decay
- `polynomial`: Polynomial (degree 1-5)
- `crystal_ball`: Crystal Ball function (for resonances)
- `gaussian_2d`: 2D Gaussian (for 2D histograms)
- `polynomial_2d`: 2D polynomial

**Example**:

```json
{
  "tool": "fit_histogram",
  "arguments": {
    "bin_centers": [3.0, 3.01, 3.02, ...],
    "bin_counts": [45, 52, 58, ...],
    "model": "gaussian",
    "initial_params": {
      "mean": 3.1,
      "sigma": 0.05
    }
  }
}
```

**Response**:

```json
{
  "data": {
    "model": "gaussian",
    "parameters": {
      "amplitude": 1250.5,
      "mean": 3.0969,
      "sigma": 0.0432
    },
    "errors": {
      "amplitude": 15.2,
      "mean": 0.0003,
      "sigma": 0.0004
    },
    "chi2": 45.3,
    "ndof": 47,
    "chi2_ndof": 0.96,
    "success": true
  }
}
```

---

## Kinematics

### `compute_invariant_mass`

Calculate invariant mass from particle 4-vectors.

**Mode**: Extended only

**Arguments**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `path` | `string` | Yes | ROOT file path |
| `tree` | `string` | Yes | TTree name |
| `pt_branches` | `string[]` | Yes | Transverse momentum branches |
| `eta_branches` | `string[]` | Yes | Pseudorapidity branches |
| `phi_branches` | `string[]` | Yes | Azimuthal angle branches |
| `mass_branches` | `string[]` | No | Particle mass branches |
| `selection` | `string` | No | Cut expression |
| `limit` | `integer` | No | Maximum entries |

**Example**:

```json
{
  "tool": "compute_invariant_mass",
  "arguments": {
    "path": "/data/sample.root",
    "tree": "events",
    "pt_branches": ["muon1_pt", "muon2_pt"],
    "eta_branches": ["muon1_eta", "muon2_eta"],
    "phi_branches": ["muon1_phi", "muon2_phi"],
    "mass_branches": ["muon1_mass", "muon2_mass"],
    "selection": "muon1_pt > 20 && muon2_pt > 20"
  }
}
```

**Response**:

```json
{
  "data": {
    "invariant_mass": [91.2, 89.5, 92.1, ...],
    "entries": 5432
  },
  "metadata": {
    "n_particles": 2,
    "selection": "muon1_pt > 20 && muon2_pt > 20"
  }
}
```

---

### `compute_transverse_mass`

Calculate transverse mass (for W→lν analyses).

**Mode**: Extended only

**Arguments**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `path` | `string` | Yes | ROOT file path |
| `tree` | `string` | Yes | TTree name |
| `lepton_pt` | `string` | Yes | Lepton pT branch |
| `lepton_phi` | `string` | Yes | Lepton φ branch |
| `met` | `string` | Yes | Missing ET branch |
| `met_phi` | `string` | Yes | Missing ET φ branch |
| `selection` | `string` | No | Cut expression |

**Example**:

```json
{
  "tool": "compute_transverse_mass",
  "arguments": {
    "path": "/data/sample.root",
    "tree": "events",
    "lepton_pt": "electron_pt",
    "lepton_phi": "electron_phi",
    "met": "met",
    "met_phi": "met_phi",
    "selection": "electron_pt > 30 && met > 30"
  }
}
```

**Response**:

```json
{
  "data": {
    "transverse_mass": [75.3, 82.1, 79.8, ...],
    "entries": 3421
  }
}
```

---

### `compute_delta_r`

Calculate ΔR angular separation between particles.

**Mode**: Extended only

**Arguments**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `path` | `string` | Yes | ROOT file path |
| `tree` | `string` | Yes | TTree name |
| `eta_1` | `string` | Yes | First particle η |
| `phi_1` | `string` | Yes | First particle φ |
| `eta_2` | `string` | Yes | Second particle η |
| `phi_2` | `string` | Yes | Second particle φ |
| `selection` | `string` | No | Cut expression |

**Example**:

```json
{
  "tool": "compute_delta_r",
  "arguments": {
    "path": "/data/sample.root",
    "tree": "events",
    "eta_1": "jet1_eta",
    "phi_1": "jet1_phi",
    "eta_2": "jet2_eta",
    "phi_2": "jet2_phi"
  }
}
```

**Response**:

```json
{
  "data": {
    "delta_r": [0.8, 1.2, 2.5, ...],
    "entries": 10000
  }
}
```

---

## Statistical Analysis

### `compute_correlation`

Compute statistical correlations between branches.

**Mode**: Extended only

**Arguments**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `path` | `string` | Yes | ROOT file path |
| `tree` | `string` | Yes | TTree name |
| `branches` | `string[]` | Yes | Branches to correlate |
| `method` | `string` | No | `"pearson"` or `"spearman"` |
| `selection` | `string` | No | Cut expression |

**Example**:

```json
{
  "tool": "compute_correlation",
  "arguments": {
    "path": "/data/sample.root",
    "tree": "events",
    "branches": ["met", "jet1_pt", "jet2_pt"],
    "method": "pearson"
  }
}
```

**Response**:

```json
{
  "data": {
    "correlation_matrix": [
      [1.0, 0.45, 0.38],
      [0.45, 1.0, 0.62],
      [0.38, 0.62, 1.0]
    ],
    "branches": ["met", "jet1_pt", "jet2_pt"],
    "method": "pearson",
    "p_values": [
      [0.0, 0.001, 0.002],
      [0.001, 0.0, 0.0],
      [0.002, 0.0, 0.0]
    ]
  }
}
```

---

## Visualization

### `generate_plot`

Generate publication-quality plots.

**Mode**: Extended only

**Arguments**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `plot_type` | `string` | Yes | `"histogram"`, `"scatter"`, `"histogram_2d"` |
| `data` | `object` | Yes | Plot data (format depends on type) |
| `output_path` | `string` | Yes | Output file path |
| `title` | `string` | No | Plot title |
| `xlabel` | `string` | No | X-axis label |
| `ylabel` | `string` | No | Y-axis label |
| `format` | `string` | No | `"png"`, `"pdf"`, `"svg"` |
| `dpi` | `integer` | No | Resolution (default 100) |

**Example (Histogram)**:

```json
{
  "tool": "generate_plot",
  "arguments": {
    "plot_type": "histogram",
    "data": {
      "bin_edges": [0, 10, 20, ..., 100],
      "bin_counts": [45, 52, 58, ...]
    },
    "output_path": "/exports/mass_plot.png",
    "title": "Dimuon Mass Distribution",
    "xlabel": "Mass [GeV]",
    "ylabel": "Events / 1 GeV",
    "format": "png",
    "dpi": 300
  }
}
```

**Response**:

```json
{
  "data": {
    "output_path": "/exports/mass_plot.png",
    "format": "png",
    "size_bytes": 125678
  }
}
```

---

# Tool Summary

## By Mode

### Core Mode (9 tools)
1. `list_files` - List ROOT files
2. `inspect_file` - Inspect file structure
3. `list_branches` - List TTree branches
4. `validate_file` - Check file integrity
5. `read_branches` - Read branch data
6. `get_branch_stats` - Compute statistics
7. `export_data` - Export to JSON/CSV/Parquet
8. `switch_mode` - Change server mode
9. `get_server_info` - Get server capabilities

### Extended Mode (6 additional tools)
10. `compute_histogram` - 1D histogram with fitting
11. `compute_histogram_2d` - 2D histogram
12. `fit_histogram` - Model fitting
13. `compute_invariant_mass` - Invariant mass calculation
14. `compute_transverse_mass` - Transverse mass
15. `compute_delta_r` - Angular separation
16. `compute_correlation` - Statistical correlations
17. `generate_plot` - Visualization

## By Category

### File Operations
- `list_files`, `inspect_file`, `validate_file`

### Data Access
- `list_branches`, `read_branches`, `get_branch_stats`

### Data Export
- `export_data`, `generate_plot`

### Histograms
- `compute_histogram`, `compute_histogram_2d`, `fit_histogram`

### Kinematics
- `compute_invariant_mass`, `compute_transverse_mass`, `compute_delta_r`

### Statistics
- `get_branch_stats`, `compute_correlation`

### Server Management
- `switch_mode`, `get_server_info`

---

# Common Patterns

## Exploration Workflow (Core Mode)

```json
// 1. List available files
{"tool": "list_files", "arguments": {}}

// 2. Inspect file structure
{"tool": "inspect_file", "arguments": {"path": "/data/sample.root"}}

// 3. List branches
{"tool": "list_branches", "arguments": {"path": "/data/sample.root", "tree": "events"}}

// 4. Read data
{"tool": "read_branches", "arguments": {
  "path": "/data/sample.root",
  "tree": "events",
  "branches": ["muon_pt", "muon_eta"],
  "limit": 100
}}
```

## Analysis Workflow (Extended Mode)

```json
// 1. Switch to extended mode
{"tool": "switch_mode", "arguments": {"mode": "extended"}}

// 2. Compute invariant mass
{"tool": "compute_invariant_mass", "arguments": {
  "path": "/data/sample.root",
  "tree": "events",
  "pt_branches": ["muon1_pt", "muon2_pt"],
  "eta_branches": ["muon1_eta", "muon2_eta"],
  "phi_branches": ["muon1_phi", "muon2_phi"]
}}

// 3. Create histogram with fit
{"tool": "compute_histogram", "arguments": {
  "path": "/data/sample.root",
  "tree": "events",
  "branch": "dimuon_mass",
  "bins": 100,
  "range": [2.8, 3.4],
  "fit_model": "gaussian"
}}

// 4. Generate plot
{"tool": "generate_plot", "arguments": {
  "plot_type": "histogram",
  "data": {...},
  "output_path": "/exports/plot.png"
}}
```

---

# Error Handling

## Mode Errors

If you try to use an extended tool in core mode:

```json
{
  "error": "mode_error",
  "message": "Tool 'fit_histogram' requires extended mode. Current mode: core",
  "hint": "Use switch_mode tool to enable extended mode"
}
```

## Security Errors

If path is not in allowed roots:

```json
{
  "error": "security_error",
  "message": "Path '/unauthorized/file.root' not in allowed roots",
  "allowed_roots": ["/data", "/exports"]
}
```

## Validation Errors

If arguments are invalid:

```json
{
  "error": "validation_error",
  "message": "Invalid bin count: must be between 1 and 10000",
  "field": "bins",
  "value": 50000
}
```

---

# See Also

- [Mode Selection Guide](../guides/modes.md): Detailed mode comparison
- [Configuration Guide](../guides/configuration.md): Server configuration
- [Architecture](../ARCHITECTURE.md): System design
- [LLM Integration](../guides/llm_integration.md): Using with AI assistants
