# Documentation

This folder contains the full documentation for `ROOT-MCP`, a Model Context Protocol (MCP) server for safe, high-level access to CERN `ROOT` files.

## Where to start

- **Project overview / quick start**: `../README.md`
- **Architecture and design**: `ARCHITECTURE.md`
- **Contributing**: `CONTRIBUTING.md`

## Releasing

Releases are handled by the GitHub Actions workflow: `.github/workflows/release.yml`.

- **Version source of truth**: update `pyproject.toml` (`[project].version`).
- **Tag rule**: when the workflow runs on a tag push `vX.Y.Z`, it will fail unless `X.Y.Z` matches `pyproject.toml`.
- **Publishing auth**: publishing uses PyPI/TestPyPI **Trusted Publishers (OIDC)** and requires the environment names below.

Steps:

1) Bump version in `pyproject.toml` and merge to `main`.

2) Create and push a matching tag:

```bash
git tag vX.Y.Z
git push origin vX.Y.Z
```

3) This triggers an automatic publish to **TestPyPI** (job environment: `publish_testpypi`).

4) Publish to **PyPI** manually:

- GitHub → **Actions** → **Release** → **Run workflow**
- Select `repository = pypi`
- This runs under job environment: `publish_pypi`

## Running the server

### Install

From the repository root:

```bash
pip install -e .
```

Optional XRootD support:

```bash
pip install -e ".[xrootd]"
```

### Configure

`ROOT-MCP` loads configuration from:

1. `ROOT_MCP_CONFIG` environment variable
2. `./config.yaml`
3. `~/.config/root-mcp/config.yaml`

Minimal example:

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

### Start

```bash
ROOT_MCP_CONFIG=/path/to/config.yaml root-mcp
```

## Using with Claude Desktop

Add an MCP server entry to Claude Desktop’s configuration (paths are examples):

```json
{
  "mcpServers": {
    "root-mcp": {
      "command": "/absolute/path/to/root-mcp",
      "args": [],
      "env": {
        "ROOT_MCP_CONFIG": "/absolute/path/to/config.yaml"
      }
    }
  }
}
```

If `command: "root-mcp"` does not work, use the absolute path to the installed executable or run via Python:

```json
{
  "mcpServers": {
    "root-mcp": {
      "command": "/absolute/path/to/python",
      "args": ["-m", "root_mcp.server"],
      "env": {
        "ROOT_MCP_CONFIG": "/absolute/path/to/config.yaml"
      }
    }
  }
}
```

## Configuration reference (high level)

- **`resources`**: one or more file roots (local or remote URIs)
- **`security.allowed_roots`**: absolute filesystem roots allowed for local access (prevents path traversal)
- **`security.allowed_protocols`**: allowed URI schemes (typically `file`)
- **`limits`**: safety bounds (rows, memory, timeouts)
- **`output.export_base_path`**: base directory for exports (defaults to `/tmp/root_mcp_output`)

## Tool reference

All tool calls return JSON objects with a consistent shape:

- `data`: primary result
- `metadata`: operation info
- `suggestions`: optional next steps

### Discovery tools

#### `list_files`

- **Purpose**: list accessible ROOT files under a configured resource.
- **Arguments**:
  - `resource` (optional)
  - `pattern` (optional glob)
  - `limit` (optional)

#### `inspect_file`

- **Purpose**: inspect a ROOT file structure (trees, histograms, directories).
- **Arguments**:
  - `path` (required)
  - `include_histograms` (optional)
  - `include_trees` (optional)

#### `list_branches`

- **Purpose**: list branches in a TTree with type information.
- **Arguments**:
  - `path` (required)
  - `tree` (required)
  - `pattern` (optional)
  - `limit` (optional)
  - `include_stats` (optional)

### Data access tools

#### `read_branches`

- **Purpose**: read branch data with pagination.
- **Arguments**:
  - `path` (required)
  - `tree` (required)
  - `branches` (required)
  - `selection` (optional)
  - `limit` (optional)
  - `offset` (optional)
  - `flatten` (optional)

#### `sample_tree`

- **Purpose**: quick sample from a TTree.
- **Arguments**:
  - `path` (required)
  - `tree` (required)
  - `size` (optional)
  - `method` (optional: `first` | `random`)
  - `branches` (optional)
  - `seed` (optional)

#### `get_branch_stats`

- **Purpose**: compute summary statistics for branches.
- **Arguments**:
  - `path` (required)
  - `tree` (required)
  - `branches` (required)
  - `selection` (optional)

### Analysis tools

#### `compute_histogram`

- **Purpose**: compute a 1D histogram.
- **Arguments**:
  - `path` (required)
  - `tree` (required)
  - `branch` (required)
  - `bins` (required)
  - `range` (optional)
  - `selection` (optional)
  - `weights` (optional)

#### `compute_histogram_2d`

- **Purpose**: compute a 2D histogram.
- **Arguments**:
  - `path` (required)
  - `tree` (required)
  - `x_branch` (required)
  - `y_branch` (required)
  - `x_bins` (required)
  - `y_bins` (required)
  - `x_range` (optional)
  - `y_range` (optional)
  - `selection` (optional)

#### `apply_selection`

- **Purpose**: count how many events pass a selection.
- **Jagged semantics**: if the selection produces a per-event variable-length boolean (e.g. `muon_pt > 20`), an event passes if **any** element passes.
- **Arguments**:
  - `path` (required)
  - `tree` (required)
  - `selection` (required)

#### `export_branches`

- **Purpose**: export branch data to JSON / CSV / Parquet.
- **Arguments**:
  - `path` (required)
  - `tree` (required)
  - `branches` (required)
  - `output_path` (required)
  - `output_format` (required: `json` | `csv` | `parquet`)
  - `selection` (optional)
  - `limit` (optional)

## Selections

ROOT-MCP accepts **ROOT-style** selection expressions in `selection` fields.

- Supported boolean operators: `&&`, `||`, `!`
- Supported comparisons: `<`, `<=`, `>`, `>=`, `==`, `!=`
- Supported functions: `abs`, `sqrt`, `log`, `exp`, `sin`, `cos`, `tan`, `min`, `max`

### Jagged (variable-length) semantics

Many HEP branches are jagged. If a selection produces a per-event variable-length boolean (e.g. `muon_pt > 20`), `ROOT-MCP` evaluates event-level pass/fail using:

- **ANY semantics**: an event passes if **any** element passes.

Example:

```text
muon_pt > 20 && muon_eta < 0
```

Means: *count events with at least one muon that satisfies both constraints.*

## Practical usage examples

### Explore data

1) List files

```json
{"name": "list_files", "arguments": {}}
```

2) Inspect a file

```json
{
  "name": "inspect_file",
  "arguments": {
    "path": "/absolute/path/to/data/root_files/sample_events.root"
  }
}
```

3) List branches

```json
{
  "name": "list_branches",
  "arguments": {
    "path": "/absolute/path/to/data/root_files/sample_events.root",
    "tree": "events",
    "pattern": "muon_*"
  }
}
```

### Check cut efficiency

```json
{
  "name": "apply_selection",
  "arguments": {
    "path": "/absolute/path/to/data/root_files/sample_events.root",
    "tree": "events",
    "selection": "muon_pt > 20 && abs(muon_eta) < 2.4"
  }
}
```

### Histogram

```json
{
  "name": "compute_histogram",
  "arguments": {
    "path": "/absolute/path/to/data/root_files/sample_events.root",
    "tree": "events",
    "branch": "muon_pt",
    "bins": 50,
    "range": [0, 200],
    "selection": "abs(muon_eta) < 2.4"
  }
}
```

### Export

```json
{
  "name": "export_branches",
  "arguments": {
    "path": "/absolute/path/to/data/root_files/sample_events.root",
    "tree": "events",
    "branches": ["event_number", "muon_pt", "muon_eta"],
    "output_path": "/tmp/root_mcp_output/muons.parquet",
    "output_format": "parquet"
  }
}
```

## Troubleshooting

### Claude Desktop can’t spawn the server

- Use an absolute `command` path to `root-mcp`, or run via Python with `-m root_mcp.server`.

### "Path not allowed"

- Ensure the file is under `security.allowed_roots`.
- Ensure you are using absolute paths.

### "Branch not found"

- Use `list_branches` with a `pattern` to discover the exact branch names.

### Exports fail for jagged data

- Prefer `parquet` for columnar data.
- For `csv`, jagged fields are stored as list-valued cells.

## Common error codes

- `invalid_path`
- `file_not_found`
- `tree_not_found`
- `branch_not_found`
- `invalid_selection`
- `limit_exceeded`
- `export_error`

## Example workflow

1. `list_files`
2. `inspect_file`
3. `list_branches`
4. `sample_tree`
5. `apply_selection`
6. `compute_histogram`
7. `export_branches`

## References

- MCP: https://modelcontextprotocol.io/
- ROOT: https://root.cern/
- uproot: https://github.com/scikit-hep/uproot5
- awkward: https://github.com/scikit-hep/awkward
