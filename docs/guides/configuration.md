# Configuration Guide

ROOT-MCP is highly configurable via a YAML configuration file.

## Loading Order

The server looks for configuration in the following order:
1. Path specified in `ROOT_MCP_CONFIG` environment variable.
2. `./config.yaml` (Current directory).
3. `~/.config/root-mcp/config.yaml` (User config directory).

## Configuration Reference

### `resources`
Defines the data sources available to the server.

```yaml
resources:
  - name: "local_data"              # Unique identifier
    uri: "file:///data/root_files"  # URI (currently only file:// and root:// supported)
    description: "My Physics Data"  # Description for the AI
    allowed_patterns: ["*.root"]    # Glob patterns to include
    max_file_size_gb: 10            # Max allowable file size
```

### `security`
Controls file system access. Critical for safety.

```yaml
security:
  allowed_roots:                    # Whitelist of absolute paths
    - "/data/root_files"
    - "/tmp/root_mcp_output"
  allowed_protocols: ["file"]       # Protocols allowed in URIs
  max_path_depth: 10                # Max directory depth to traverse
```

### `limits`
Resource usage limits to prevent the server from crashing the host.

```yaml
limits:
  max_rows_per_call: 1000000        # Max entries returned by read_branches
  max_memory_mb: 512                # Hint for internal caches
  max_file_handles: 100             # Max open ROOT files
  operation_timeout_sec: 60         # Timeout for long operations
```

### `output`
Settings for file exports (`export_branches`).

```yaml
output:
  export_base_path: "/tmp/root_mcp_output" # Where exported files go
  allowed_formats: ["json", "csv", "parquet"]
```

### `analysis`
Tweak the analysis engine.

```yaml
analysis:
  default_chunk_size: 10000         # Chunk size for iterative processing
  use_awkward: true                 # Use awkward-array (recommended)
  histogram:
    max_bins_1d: 10000
    max_bins_2d: 1000
```

## Example `config.yaml`

```yaml
server:
  name: "root-mcp"
  log_level: "INFO"

resources:
  - name: "cms_open_data"
    uri: "file:///data/cms"
    description: "CMS Open Data 2011"
    allowed_patterns: ["*.root"]

security:
  allowed_roots:
    - "/data/cms"
    - "/tmp/root_mcp_output"

limits:
  max_rows_per_call: 500000
```
