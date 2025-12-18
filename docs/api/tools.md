# Tool Reference

This document provides a comprehensive reference for all tools available in the ROOT-MCP server.

All tools return a standard JSON response structure:

```json
{
  "data": { ... },       // The primary result
  "metadata": { ... },   // Operation details, execution time, etc.
  "suggestions": [ ... ] // Optional next steps or hints
}
```

## Discovery Tools

Tools for exploring available files and their structure.

### `list_files`

List accessible ROOT files under a configured resource.

**Arguments:**

| Name | Type | Description | Default |
|------|------|-------------|---------|
| `resource` | `string` | Resource ID (optional, uses default if omitted) | `null` |
| `pattern` | `string` | Glob pattern to filter files (e.g., `'run_*.root'`) | `null` |
| `limit` | `integer` | Maximum number of files to return | `100` |

**Example Request:**

```json
{
  "name": "list_files",
  "arguments": {}
}
```

**Example Response:**

```json
{
  "data": {
    "files": [
      {
        "path": "/data/root_files/sample_events.root",
        "size_bytes": 1306965,
        "modified": 1715648717.53,
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

Inspect a ROOT file's general structure, including TTree names and histograms.

**Arguments:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `path` | `string` | Yes | Absolute path to the ROOT file |
| `include_histograms` | `boolean` | No | Include histogram metadata |
| `include_trees` | `boolean` | No | Include TTree metadata |

**Example Request:**

```json
{
  "name": "inspect_file",
  "arguments": {
    "path": "/data/root_files/sample_events.root"
  }
}
```

**Example Response:**

```json
{
  "data": {
    "path": "/data/root_files/sample_events.root",
    "trees": [
      {
        "name": "events;1",
        "path": "events;1",
        "classname": "TTree",
        "entries": 10000,
        "branches": 26
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

**Arguments:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `path` | `string` | Yes | Absolute path to the ROOT file |
| `tree` | `string` | Yes | Name of the TTree (e.g., `"events"`) |
| `pattern` | `string` | No | Glob pattern to filter branches (e.g., `"muon_*"`) |
| `limit` | `integer` | No | Maximum branches to return (default 100) |
| `include_stats` | `boolean` | No | Compute min/max/mean (slower) |

**Example Request:**

```json
{
  "name": "list_branches",
  "arguments": {
    "path": "/data/root_files/sample_events.root",
    "tree": "events",
    "limit": 5
  }
}
```

**Example Response:**

```json
{
  "data": {
    "tree": "events",
    "total_entries": 10000,
    "branches": [
      {
        "name": "met",
        "type": "float",
        "title": "met/F",
        "is_jagged": false
      }
    ]
  }
}
```

## Data Access Tools

Tools for reading actual data from TTrees.

### `read_branches`

Read branch data from a TTree with optional filtering and pagination. Supports derived branches through the `defines` parameter.

**Arguments:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `path` | `string` | Yes | Absolute path to the ROOT file |
| `tree` | `string` | Yes | Name of the TTree |
| `branches` | `string[]` | Yes | List of branch names to read (can include physical or derived branches) |
| `selection` | `string` | No | ROOT-style cut expression (e.g., `'pt > 20'`) |
| `limit` | `integer` | No | Maximum entries to return |
| `offset` | `integer` | No | Number of entries to skip |
| `flatten` | `boolean` | No | Flatten jagged arrays (default `false`) |
| `defines` | `object` | No | Dictionary of derived variable definitions `{name: expression}` |

**Example Request (Basic):**

```json
{
  "name": "read_branches",
  "arguments": {
    "path": "/data/root_files/sample_events.root",
    "tree": "events",
    "branches": ["muon_pt", "muon_eta"],
    "limit": 2
  }
}
```

**Example Request (With Derived Branches):**

```json
{
  "name": "read_branches",
  "arguments": {
    "path": "/data/root_files/sample_events.root",
    "tree": "events",
    "branches": ["met", "met_x", "met_y"],
    "defines": {
      "met_x": "met * cos(met_phi)",
      "met_y": "met * sin(met_phi)"
    },
    "selection": "met > 50",
    "limit": 2
  }
}
```

**Example Response:**

```json
{
  "data": {
    "branches": ["muon_pt", "muon_eta"],
    "entries": 2,
    "is_jagged": true,
    "records": [
      {
        "muon_pt": [60.9],
        "muon_eta": [1.95]
      },
      {
        "muon_pt": [134.8, 29.1],
        "muon_eta": [-1.42, 0.29]
      }
    ]
  },
  "metadata": {
    "operation": "read_branches",
    "entries_selected": 2,
    "defines": null
  }
}
```

---

### `sample_tree`

Get a quick sample from a TTree. useful for understanding the data schema.

**Arguments:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `path` | `string` | Yes | Absolute path to the ROOT file |
| `tree` | `string` | Yes | Name of the TTree |
| `size` | `integer` | No | Sample size (default 100) |
| `method` | `string` | No | `"first"` or `"random"` |
| `branches` | `string[]` | No | Specific branches to include |

**Example Request:**

```json
{
  "name": "sample_tree",
  "arguments": {
    "path": "/data/root_files/sample_events.root",
    "tree": "events",
    "size": 2,
    "branches": ["run_number", "met"]
  }
}
```

**Example Response:**

```json
{
  "data": {
    "branches": ["run_number", "met"],
    "records": [
      { "run_number": 12345, "met": 14.07 },
      { "run_number": 12345, "met": 90.30 }
    ]
  }
}
```

## Analysis Tools

Tools for performing computations on the data without transferring it all.

### `compute_kinematics`

Compute kinematic quantities (invariant masses, ΔR, Δφ, etc.) from particle four-momenta. Essential for Dalitz plots, resonance studies, and angular correlations.

**Arguments:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `path` | `string` | Yes | File path |
| `tree` | `string` | Yes | Tree name |
| `computations` | `array` | Yes | List of kinematic calculations (see below) |
| `selection` | `string` | No | Optional cut expression |
| `limit` | `integer` | No | Max entries to process |

**Computation Object:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | `string` | Yes | Output variable name |
| `type` | `string` | Yes | One of: `invariant_mass`, `invariant_mass_squared`, `transverse_mass`, `delta_r`, `delta_phi` |
| `particles` | `array` | Yes | List of particle name prefixes |
| `components` | `array` | No | Component suffixes (default: `['PX', 'PY', 'PZ', 'PE']`) |
| `eta_suffix` | `string` | No | Eta suffix for delta_r (default: `'ETA'`) |
| `phi_suffix` | `string` | No | Phi suffix for delta_r/delta_phi (default: `'PHI'`) |

**Example Request (Dalitz Plot):**

```json
{
  "name": "compute_kinematics",
  "arguments": {
    "path": "/data/D0_decay.root",
    "tree": "DecayTree",
    "computations": [
      {
        "name": "m_Kpi_squared",
        "type": "invariant_mass_squared",
        "particles": ["K", "pi_1"]
      },
      {
        "name": "m_pipi_squared",
        "type": "invariant_mass_squared",
        "particles": ["pi_1", "pi_2"]
      }
    ],
    "selection": "K_PT > 500",
    "limit": 10000
  }
}
```

**Example Response:**

```json
{
  "data": {
    "m_Kpi_squared": [1.234, 2.345, 3.456, ...],
    "m_pipi_squared": [0.987, 1.876, 2.765, ...]
  },
  "metadata": {
    "operation": "compute_kinematics",
    "tree": "DecayTree",
    "entries_processed": 10000,
    "computations": [
      {"name": "m_Kpi_squared", "type": "invariant_mass_squared"},
      {"name": "m_pipi_squared", "type": "invariant_mass_squared"}
    ],
    "selection": "K_PT > 500"
  },
  "suggestions": [
    "Computed 2 kinematic quantities: m_Kpi_squared, m_pipi_squared",
    "Processed 10,000 entries",
    "Use compute_histogram() to visualize mass distributions or compute_histogram_2d() for Dalitz plots"
  ]
}
```

See [Kinematic Computation Guide](../guides/compute_kinematics.md) for detailed examples and physics applications.

---

### `apply_selection`

Count how many entries pass a selection.

**Arguments:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `path` | `string` | Yes | Absolute path to the ROOT file |
| `tree` | `string` | Yes | Name of the TTree |
| `selection` | `string` | Yes | Cut expression |

**Example Request:**

```json
{
  "name": "apply_selection",
  "arguments": {
    "path": "/data/root_files/sample_events.root",
    "tree": "events",
    "selection": "met > 50"
  }
}
```

**Example Response:**

```json
{
  "data": {
    "entries_total": 10000,
    "entries_selected": 1823,
    "efficiency": 0.1823,
    "selection": "met > 50"
  }
}
```

---

### `compute_histogram`

Compute a 1D histogram.

**Arguments:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `path` | `string` | Yes | File path |
| `tree` | `string` | Yes | Tree name |
| `branch` | `string` | Yes | Branch to histogram |
| `bins` | `integer` | Yes | Number of bins |
| `range` | `[min, max]` | No | Range (auto if omitted) |
| `selection` | `string` | No | Optional cut |
| `weights` | `string` | No | Weight branch |

**Example Request:**

```json
{
  "name": "compute_histogram",
  "arguments": {
    "path": "/data/root_files/sample_events.root",
    "tree": "events",
    "branch": "met",
    "bins": 10,
    "range": [0, 200]
  }
}
```

**Example Response:**

```json
{
  "data": {
    "bin_edges": [0.0, 20.0, ..., 200.0],
    "bin_counts": [4943, 2518, ..., 9],
    "mean": 29.32,
    "std": 29.23
  }
}
```
