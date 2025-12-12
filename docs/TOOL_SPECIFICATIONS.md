# ROOT-MCP Tool Specifications

Complete API reference for all MCP tools provided by the ROOT-MCP server.

## Tool Design Patterns

All tools follow consistent patterns:

### Request Format
```json
{
  "name": "tool_name",
  "arguments": {
    "path": "file path or resource URI",
    ...
  }
}
```

### Response Format
```json
{
  "data": { ... },
  "metadata": {
    "operation": "tool_name",
    "execution_time_ms": 100,
    "truncated": false
  },
  "suggestions": ["Helpful next steps for the AI model"]
}
```

### Error Format
```json
{
  "error": "error_code",
  "message": "Human-readable description",
  "details": { ... },
  "suggestion": "How to fix or retry",
  "retry_with": { "corrected": "parameters" }
}
```

---

## Discovery Tools

### 1. list_files

**Purpose**: Enumerate ROOT files accessible under a resource root.

**Input Schema**:
```json
{
  "resource": "string (optional)",
  "pattern": "string (optional, glob pattern)",
  "limit": "integer (optional, default 100, max 1000)"
}
```

**Parameters**:
- `resource` (optional): Resource ID from configuration (e.g., "local_data"). If omitted, lists from default resource.
- `pattern` (optional): Glob pattern to filter files (e.g., "run_*.root", "*2024*.root")
- `limit` (optional): Maximum number of files to return

**Output Schema**:
```json
{
  "data": {
    "files": [
      {
        "path": "string (absolute or resource-relative)",
        "size_bytes": "integer",
        "modified": "ISO 8601 timestamp",
        "resource": "string (resource ID)"
      }
    ],
    "total_matched": "integer",
    "total_scanned": "integer"
  },
  "metadata": { ... },
  "suggestions": [
    "Inspect a file with inspect_file(path='...')",
    "Filter further with pattern='run_123*'"
  ]
}
```

**Example 1: List all files in default resource**
```json
Request:
{
  "name": "list_files",
  "arguments": {}
}

Response:
{
  "data": {
    "files": [
      {
        "path": "/data/run_12345.root",
        "size_bytes": 471859200,
        "modified": "2024-03-15T14:30:00Z",
        "resource": "local_data"
      },
      {
        "path": "/data/run_12346.root",
        "size_bytes": 523567104,
        "modified": "2024-03-15T15:45:00Z",
        "resource": "local_data"
      }
    ],
    "total_matched": 2,
    "total_scanned": 2
  },
  "metadata": {
    "operation": "list_files",
    "execution_time_ms": 45
  },
  "suggestions": [
    "Inspect run_12345.root with inspect_file(path='/data/run_12345.root')"
  ]
}
```

**Example 2: List with pattern filter**
```json
Request:
{
  "name": "list_files",
  "arguments": {
    "pattern": "*2024*.root",
    "limit": 50
  }
}
```

**Error Examples**:
```json
{
  "error": "resource_not_found",
  "message": "Resource 'unknown_resource' is not configured",
  "details": {
    "available_resources": ["local_data", "xrootd_atlas", "public_datasets"]
  },
  "suggestion": "Use one of the available resources"
}
```

---

### 2. inspect_file

**Purpose**: Get high-level metadata about a ROOT file without reading data.

**Input Schema**:
```json
{
  "path": "string (required)",
  "include_histograms": "boolean (optional, default true)",
  "include_trees": "boolean (optional, default true)"
}
```

**Parameters**:
- `path` (required): File path or resource URI
- `include_histograms` (optional): Include histogram metadata
- `include_trees` (optional): Include TTree metadata

**Output Schema**:
```json
{
  "data": {
    "path": "string",
    "size_bytes": "integer",
    "compression": "string (e.g., 'ZLIB:4')",
    "root_version": "string",
    "trees": [
      {
        "name": "string",
        "path": "string (full path in file, e.g., 'dir/tree')",
        "entries": "integer",
        "branches": "integer (count)",
        "size_bytes": "integer (compressed)"
      }
    ],
    "histograms": [
      {
        "name": "string",
        "type": "string (TH1F, TH2D, etc.)",
        "path": "string",
        "bins": "integer or [int, int] for 2D",
        "entries": "integer"
      }
    ],
    "directories": ["string (list of TDirectory paths)"],
    "other_objects": [
      {
        "name": "string",
        "type": "string (class name)",
        "path": "string"
      }
    ]
  },
  "metadata": { ... },
  "suggestions": [
    "List branches in 'events' tree with list_branches(tree='events')",
    "Read histogram 'h_pt' with read_histogram(name='h_pt')"
  ]
}
```

**Example**:
```json
Request:
{
  "name": "inspect_file",
  "arguments": {
    "path": "/data/run_12345.root"
  }
}

Response:
{
  "data": {
    "path": "/data/run_12345.root",
    "size_bytes": 471859200,
    "compression": "LZMA:4",
    "root_version": "6.28/04",
    "trees": [
      {
        "name": "events",
        "path": "events",
        "entries": 1000000,
        "branches": 245,
        "size_bytes": 450000000
      },
      {
        "name": "metadata",
        "path": "metadata",
        "entries": 1,
        "branches": 10,
        "size_bytes": 5120
      }
    ],
    "histograms": [
      {
        "name": "cutflow",
        "type": "TH1F",
        "path": "cutflow",
        "bins": 10,
        "entries": 2000000
      }
    ],
    "directories": ["plots", "systematics"],
    "other_objects": [
      {
        "name": "run_info",
        "type": "TObjString",
        "path": "run_info"
      }
    ]
  },
  "metadata": {
    "operation": "inspect_file",
    "execution_time_ms": 120
  },
  "suggestions": [
    "Explore the 'events' tree with 1M entries using list_branches()",
    "The file is 450 MB compressed, consider using selections to limit data"
  ]
}
```

---

### 3. list_branches

**Purpose**: List branches in a TTree with type information and statistics.

**Input Schema**:
```json
{
  "path": "string (required)",
  "tree": "string (required)",
  "pattern": "string (optional, glob pattern)",
  "limit": "integer (optional, default 100, max 1000)",
  "include_stats": "boolean (optional, default false)"
}
```

**Parameters**:
- `path` (required): File path
- `tree` (required): Tree name or path
- `pattern` (optional): Glob pattern to filter branches (e.g., "muon_*", "*_pt")
- `limit` (optional): Maximum branches to return
- `include_stats` (optional): Compute min/max for each branch (slower)

**Output Schema**:
```json
{
  "data": {
    "tree": "string",
    "total_entries": "integer",
    "total_branches": "integer",
    "branches": [
      {
        "name": "string",
        "type": "string (uproot type name)",
        "dtype": "string (numpy dtype if simple)",
        "title": "string (ROOT title/description)",
        "compression": "string",
        "is_jagged": "boolean (variable-length arrays)",
        "stats": {
          "min": "number (if include_stats=true)",
          "max": "number",
          "mean": "number (approximate)"
        }
      }
    ],
    "matched": "integer (number of branches after pattern filter)"
  },
  "metadata": { ... },
  "suggestions": [
    "Read muon branches with read_branches(branches=['muon_pt', 'muon_eta'])",
    "Filter with pattern='electron_*' to see electron variables"
  ]
}
```

**Example 1: List all branches**
```json
Request:
{
  "name": "list_branches",
  "arguments": {
    "path": "/data/run_12345.root",
    "tree": "events",
    "limit": 10
  }
}

Response:
{
  "data": {
    "tree": "events",
    "total_entries": 1000000,
    "total_branches": 245,
    "branches": [
      {
        "name": "muon_pt",
        "type": "float32[]",
        "dtype": null,
        "title": "Muon transverse momentum (GeV)",
        "compression": "LZMA:4",
        "is_jagged": true
      },
      {
        "name": "muon_eta",
        "type": "float32[]",
        "dtype": null,
        "title": "Muon pseudorapidity",
        "compression": "LZMA:4",
        "is_jagged": true
      },
      {
        "name": "event_number",
        "type": "uint64",
        "dtype": "uint64",
        "title": "Event number",
        "compression": "LZMA:4",
        "is_jagged": false
      }
    ],
    "matched": 10
  },
  "metadata": {
    "operation": "list_branches",
    "execution_time_ms": 80
  },
  "suggestions": [
    "245 total branches - use pattern='muon_*' to filter",
    "Sample data with read_branches(limit=10)"
  ]
}
```

**Example 2: Pattern filter with stats**
```json
Request:
{
  "name": "list_branches",
  "arguments": {
    "path": "/data/run_12345.root",
    "tree": "events",
    "pattern": "muon_*",
    "include_stats": true
  }
}

Response:
{
  "data": {
    "tree": "events",
    "total_entries": 1000000,
    "total_branches": 245,
    "branches": [
      {
        "name": "muon_pt",
        "type": "float32[]",
        "title": "Muon transverse momentum (GeV)",
        "is_jagged": true,
        "stats": {
          "min": 3.5,
          "max": 487.2,
          "mean": 28.4
        }
      },
      {
        "name": "muon_eta",
        "type": "float32[]",
        "is_jagged": true,
        "stats": {
          "min": -2.49,
          "max": 2.48,
          "mean": 0.02
        }
      },
      {
        "name": "muon_phi",
        "type": "float32[]",
        "is_jagged": true,
        "stats": {
          "min": -3.14159,
          "max": 3.14159,
          "mean": 0.001
        }
      }
    ],
    "matched": 3
  },
  "suggestions": [
    "muon_pt ranges from 3.5 to 487.2 GeV - suitable for histogramming"
  ]
}
```

---

## Data Access Tools

### 4. read_branches

**Purpose**: Extract data from TTree branches with optional filtering and pagination.

**Input Schema**:
```json
{
  "path": "string (required)",
  "tree": "string (required)",
  "branches": "string[] (required, list of branch names)",
  "selection": "string (optional, ROOT-style cut expression)",
  "limit": "integer (optional, default 1000, max 1000000)",
  "offset": "integer (optional, default 0)",
  "flatten": "boolean (optional, default false)",
  "output_format": "string (optional, 'json'|'csv'|'records', default 'records')"
}
```

**Parameters**:
- `path`, `tree`, `branches`: Specify what to read
- `selection` (optional): ROOT-style expression (e.g., "pt > 20 && abs(eta) < 2.5")
- `limit`, `offset`: Pagination (max 1M rows)
- `flatten` (optional): For jagged arrays, flatten to 1D (repeats parent event data)
- `output_format`: How to structure the output

**Output Schema**:
```json
{
  "data": {
    "branches": ["string (branch names included)"],
    "entries": "integer (number of events/rows returned)",
    "is_jagged": "boolean (contains variable-length arrays)",
    "records": [
      {
        "branch1": "value or array",
        "branch2": "value or array"
      }
    ]
  },
  "metadata": {
    "operation": "read_branches",
    "entries_scanned": "integer (total examined)",
    "entries_selected": "integer (passed selection)",
    "entries_returned": "integer (after limit/offset)",
    "truncated": "boolean (more data available)",
    "execution_time_ms": "integer"
  },
  "suggestions": [ ... ]
}
```

**Example 1: Simple read**
```json
Request:
{
  "name": "read_branches",
  "arguments": {
    "path": "/data/run_12345.root",
    "tree": "events",
    "branches": ["muon_pt", "muon_eta"],
    "limit": 5
  }
}

Response:
{
  "data": {
    "branches": ["muon_pt", "muon_eta"],
    "entries": 5,
    "is_jagged": true,
    "records": [
      {
        "muon_pt": [25.3, 18.9],
        "muon_eta": [-0.5, 1.2]
      },
      {
        "muon_pt": [102.1],
        "muon_eta": [0.1]
      },
      {
        "muon_pt": [],
        "muon_eta": []
      },
      {
        "muon_pt": [45.2, 32.1, 28.7],
        "muon_eta": [1.8, -1.3, 0.4]
      },
      {
        "muon_pt": [67.4],
        "muon_eta": [-2.1]
      }
    ]
  },
  "metadata": {
    "operation": "read_branches",
    "entries_scanned": 5,
    "entries_selected": 5,
    "entries_returned": 5,
    "truncated": true,
    "execution_time_ms": 45
  },
  "suggestions": [
    "Data has variable-length arrays (0-3 muons per event)",
    "Use flatten=true for flat output, or apply selection to filter events"
  ]
}
```

**Example 2: With selection and pagination**
```json
Request:
{
  "name": "read_branches",
  "arguments": {
    "path": "/data/run_12345.root",
    "tree": "events",
    "branches": ["muon_pt", "muon_eta", "muon_charge"],
    "selection": "muon_pt > 20 && abs(muon_eta) < 2.4",
    "limit": 1000,
    "offset": 0
  }
}

Response:
{
  "data": {
    "branches": ["muon_pt", "muon_eta", "muon_charge"],
    "entries": 1000,
    "is_jagged": true,
    "records": [ ... ]
  },
  "metadata": {
    "entries_scanned": 50000,
    "entries_selected": 15000,
    "entries_returned": 1000,
    "truncated": true,
    "execution_time_ms": 520
  },
  "suggestions": [
    "15000 events passed selection, but only 1000 returned due to limit",
    "Use offset=1000 to get next page",
    "Consider compute_histogram() for full dataset analysis"
  ]
}
```

**Example 3: Flattened output**
```json
Request:
{
  "name": "read_branches",
  "arguments": {
    "path": "/data/run_12345.root",
    "tree": "events",
    "branches": ["event_number", "muon_pt"],
    "limit": 3,
    "flatten": true
  }
}

Response:
{
  "data": {
    "branches": ["event_number", "muon_pt"],
    "entries": 5,  // 5 individual muons
    "is_jagged": false,
    "records": [
      {"event_number": 12345, "muon_pt": 25.3},
      {"event_number": 12345, "muon_pt": 18.9},
      {"event_number": 12346, "muon_pt": 102.1},
      {"event_number": 12348, "muon_pt": 45.2},
      {"event_number": 12348, "muon_pt": 32.1}
    ]
  },
  "suggestions": [
    "Flattened output: event 12345 appears twice (had 2 muons)",
    "Event 12347 skipped (had 0 muons)"
  ]
}
```

---

### 5. sample_tree

**Purpose**: Get a quick random or sequential sample from a tree.

**Input Schema**:
```json
{
  "path": "string (required)",
  "tree": "string (required)",
  "size": "integer (optional, default 100, max 10000)",
  "method": "string (optional, 'first'|'random', default 'first')",
  "branches": "string[] (optional, default all)",
  "seed": "integer (optional, for reproducible random sampling)"
}
```

**Output**: Same as `read_branches` but optimized for small samples.

**Example**:
```json
Request:
{
  "name": "sample_tree",
  "arguments": {
    "path": "/data/run_12345.root",
    "tree": "events",
    "size": 10,
    "method": "random",
    "seed": 42
  }
}
```

---

## Analysis Tools

### 6. compute_histogram

**Purpose**: Compute a 1D histogram with optional selection.

**Input Schema**:
```json
{
  "path": "string (required)",
  "tree": "string (required)",
  "branch": "string (required)",
  "bins": "integer (required, max 10000)",
  "range": "[number, number] (optional, auto-detected if omitted)",
  "selection": "string (optional)",
  "weights": "string (optional, branch name for weights)",
  "flatten": "boolean (optional, default true for jagged arrays)"
}
```

**Parameters**:
- `branch`: Branch to histogram (must be numeric)
- `bins`: Number of bins (max 10,000 to prevent OOM)
- `range`: [min, max] for histogram. If omitted, computed from data
- `selection`: Cut expression applied before histogramming
- `weights`: Optional branch to use for weighted histogram
- `flatten`: For jagged arrays, histogram all elements (true) or per-event length (false)

**Output Schema**:
```json
{
  "data": {
    "bin_edges": ["number[] (length = bins + 1)"],
    "bin_counts": ["number[] (length = bins)"],
    "bin_errors": ["number[] (statistical errors, sqrt(N))"],
    "underflow": "integer",
    "overflow": "integer",
    "entries": "integer (total entries histogrammed)",
    "sum_weights": "number (if weighted)",
    "mean": "number",
    "std": "number"
  },
  "metadata": {
    "operation": "compute_histogram",
    "entries_scanned": "integer",
    "entries_selected": "integer (after selection)",
    "execution_time_ms": "integer"
  },
  "suggestions": [ ... ]
}
```

**Example 1: Basic histogram**
```json
Request:
{
  "name": "compute_histogram",
  "arguments": {
    "path": "/data/run_12345.root",
    "tree": "events",
    "branch": "muon_pt",
    "bins": 50,
    "range": [0, 200]
  }
}

Response:
{
  "data": {
    "bin_edges": [0, 4, 8, 12, ..., 196, 200],
    "bin_counts": [0, 145, 1203, 2456, ..., 12, 5],
    "bin_errors": [0, 12.04, 34.68, 49.56, ..., 3.46, 2.24],
    "underflow": 0,
    "overflow": 234,
    "entries": 125000,
    "mean": 45.3,
    "std": 28.7
  },
  "metadata": {
    "operation": "compute_histogram",
    "entries_scanned": 1000000,
    "entries_selected": 1000000,
    "execution_time_ms": 1250
  },
  "suggestions": [
    "234 entries overflow (pT > 200 GeV) - consider extending range",
    "Peak around 40-50 GeV - typical for muons"
  ]
}
```

**Example 2: With selection**
```json
Request:
{
  "name": "compute_histogram",
  "arguments": {
    "path": "/data/run_12345.root",
    "tree": "events",
    "branch": "muon_pt",
    "bins": 50,
    "range": [0, 200],
    "selection": "abs(muon_eta) < 2.4 && muon_charge > 0"
  }
}

Response:
{
  "data": {
    "bin_edges": [...],
    "bin_counts": [...],
    "entries": 62000
  },
  "metadata": {
    "entries_scanned": 1000000,
    "entries_selected": 62000,
    "execution_time_ms": 1450
  },
  "suggestions": [
    "Selected 62k/1M entries (6.2%)",
    "Selection applied: positive muons in central detector"
  ]
}
```

---

### 7. compute_histogram_2d

**Purpose**: Compute a 2D histogram (scatter plot binned).

**Input Schema**:
```json
{
  "path": "string (required)",
  "tree": "string (required)",
  "x_branch": "string (required)",
  "y_branch": "string (required)",
  "x_bins": "integer (required, max 1000)",
  "y_bins": "integer (required, max 1000)",
  "x_range": "[number, number] (optional)",
  "y_range": "[number, number] (optional)",
  "selection": "string (optional)",
  "flatten": "boolean (optional, default true)"
}
```

**Output Schema**:
```json
{
  "data": {
    "x_edges": ["number[] (length = x_bins + 1)"],
    "y_edges": ["number[] (length = y_bins + 1)"],
    "counts": ["number[][] (shape: y_bins × x_bins)"],
    "entries": "integer"
  },
  "metadata": { ... }
}
```

**Example**:
```json
Request:
{
  "name": "compute_histogram_2d",
  "arguments": {
    "path": "/data/run_12345.root",
    "tree": "events",
    "x_branch": "muon_eta",
    "y_branch": "muon_phi",
    "x_bins": 50,
    "y_bins": 50,
    "x_range": [-2.5, 2.5],
    "y_range": [-3.15, 3.15]
  }
}
```

---

### 8. apply_selection

**Purpose**: Count entries passing a selection without reading data.

**Input Schema**:
```json
{
  "path": "string (required)",
  "tree": "string (required)",
  "selection": "string (required)"
}
```

**Output Schema**:
```json
{
  "data": {
    "entries_total": "integer",
    "entries_selected": "integer",
    "efficiency": "number (fraction passing)",
    "selection": "string (echoed back)"
  },
  "metadata": { ... }
}
```

**Example**:
```json
Request:
{
  "name": "apply_selection",
  "arguments": {
    "path": "/data/run_12345.root",
    "tree": "events",
    "selection": "muon_pt > 25 && abs(muon_eta) < 2.4"
  }
}

Response:
{
  "data": {
    "entries_total": 1000000,
    "entries_selected": 45230,
    "efficiency": 0.04523,
    "selection": "muon_pt > 25 && abs(muon_eta) < 2.4"
  },
  "metadata": {
    "execution_time_ms": 890
  },
  "suggestions": [
    "4.5% of events pass selection (45k/1M)",
    "Proceed with compute_histogram() or read_branches() using this selection"
  ]
}
```

---

## Export Tools

### 9. export_branches

**Purpose**: Export filtered data to standard formats.

**Input Schema**:
```json
{
  "path": "string (required)",
  "tree": "string (required)",
  "branches": "string[] (required)",
  "selection": "string (optional)",
  "limit": "integer (optional, max 10000000)",
  "output_format": "string (required, 'json'|'csv'|'parquet')",
  "output_path": "string (required, destination file)"
}
```

**Output Schema**:
```json
{
  "data": {
    "output_path": "string",
    "format": "string",
    "entries_written": "integer",
    "size_bytes": "integer"
  },
  "metadata": { ... }
}
```

**Example**:
```json
Request:
{
  "name": "export_branches",
  "arguments": {
    "path": "/data/run_12345.root",
    "tree": "events",
    "branches": ["muon_pt", "muon_eta", "muon_phi"],
    "selection": "muon_pt > 25",
    "limit": 100000,
    "output_format": "parquet",
    "output_path": "/output/selected_muons.parquet"
  }
}

Response:
{
  "data": {
    "output_path": "/output/selected_muons.parquet",
    "format": "parquet",
    "entries_written": 45230,
    "size_bytes": 1245678
  },
  "metadata": {
    "execution_time_ms": 3400
  },
  "suggestions": [
    "Exported 45k entries to Parquet (1.2 MB)",
    "Use pandas.read_parquet() or PyArrow to read"
  ]
}
```

---

## Advanced Tools

### 10. get_branch_stats

**Purpose**: Compute summary statistics for branches.

**Input Schema**:
```json
{
  "path": "string (required)",
  "tree": "string (required)",
  "branches": "string[] (required)",
  "selection": "string (optional)",
  "quantiles": "number[] (optional, e.g., [0.25, 0.5, 0.75])"
}
```

**Output Schema**:
```json
{
  "data": {
    "statistics": {
      "branch_name": {
        "count": "integer",
        "mean": "number",
        "std": "number",
        "min": "number",
        "max": "number",
        "quantiles": {
          "0.25": "number",
          "0.5": "number",
          "0.75": "number"
        }
      }
    }
  }
}
```

---

## Common Error Codes

| Error Code | Meaning | Typical Resolution |
|-----------|---------|-------------------|
| `file_not_found` | Path does not exist | Check path, use list_files() |
| `tree_not_found` | Tree name invalid | Use inspect_file() to list trees |
| `branch_not_found` | Branch name invalid | Use list_branches() to see available |
| `invalid_selection` | Syntax error in cut expression | Check ROOT expression syntax |
| `limit_exceeded` | Requested too much data | Reduce limit, add selection, or use pagination |
| `timeout` | Operation took too long | Reduce scope, add tighter selection |
| `permission_denied` | File not accessible | Check resource configuration |
| `corrupted_file` | ROOT file cannot be read | Verify file integrity |
| `unsupported_type` | Branch type not supported | Use PyROOT fallback or skip branch |

---

## Performance Guidelines

| Operation | Typical Time | Scaling |
|-----------|-------------|---------|
| `inspect_file` | <100ms | O(1) - metadata only |
| `list_branches` | <500ms | O(n_branches) |
| `list_branches` (with stats) | 1-10s | O(n_entries) - full scan |
| `read_branches` (10k rows) | <1s | O(n_rows × n_branches) |
| `compute_histogram` (1M entries) | 2-5s | O(n_entries) |
| `compute_histogram_2d` (1M entries) | 5-15s | O(n_entries) |
| `export_branches` (100k rows) | 5-30s | O(n_rows × n_branches) + I/O |

**Optimization Tips for LLMs**:
1. Use `apply_selection()` to check selection efficiency before expensive operations
2. Use `sample_tree()` to understand data structure before full reads
3. Request only needed branches (column pruning)
4. Apply selections to reduce data volume
5. Use pagination for large datasets
6. Prefer histogramming over reading full datasets when possible

---

**Document Version**: 1.0
**Last Updated**: 2025-12-12
