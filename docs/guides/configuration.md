# Configuration Guide

ROOT-MCP is configured through a YAML file that controls server behavior, analysis tier selection, resource limits, and security constraints.

## Quick Start

You do **not** need a config file to get started. Three zero-config approaches are available:

### Option 1 — Inline data path (fastest)

Pass `--data-path` directly on the command line. The server will grant access to that directory without any YAML required:

```bash
root-mcp --data-path /path/to/your/data
```

Multiple directories are supported:

```bash
root-mcp --data-path /data/run2024 --data-path /data/simulation
```

### Option 2 — Environment variable

Set `ROOT_MCP_DATA_PATH` once (colon-separated on Linux/macOS) and start the server without arguments:

```bash
export ROOT_MCP_DATA_PATH=/path/to/your/data
root-mcp
```

### Option 3 — Generate a starter config file

Use the built-in `init` command to create a ready-to-edit `config.yaml` in the current directory:

```bash
root-mcp init                    # generates config.yaml with a placeholder URI
root-mcp init --permissive       # fills the URI with the current working directory
root-mcp init --output ~/root-mcp.yaml   # custom output path
```

Open the generated file, replace the `REPLACE_WITH_YOUR_DATA_PATH` placeholder, and run:

```bash
root-mcp --config config.yaml
```

### Permissive mode

When `security.allowed_roots` is an **empty list** (the default in the generated config), the server allows access to **any** local path. This is the recommended setting for personal or local use. Restrict it by listing explicit directories when deploying in a shared environment:

```yaml
security:
  allowed_roots: []            # permissive — any local path is accessible
  # allowed_roots:             # restrictive — only these directories
  #   - /data/physics
  #   - /home/user/exports
```

> **Shared deployment warning**: Permissive local defaults are not safe for a
> shared or central HTTP service. Before exposing ROOT-MCP to multiple users or
> agents, configure explicit `allowed_roots` or named resources, require
> authentication, and use a restrictive deployment policy.

---

## Configuration File Location

Settings are merged from multiple sources in the following priority order (highest wins):

```
1. Built-in Pydantic defaults          (always lowest)
2. YAML config file                    (ROOT_MCP_CONFIG / --config / auto-discovery)
3. ROOT_MCP_* environment variables    (override anything from YAML)
4. CLI flags                           (always highest — beat both YAML and env vars)
```

Every field that can appear in `config.yaml` has a corresponding env var and CLI flag (see the [Complete Env Var & CLI Reference](#complete-env-var--cli-reference) below).  YAML users are unaffected — all new sources are strictly additive.

**Recommendation**: Use `ROOT_MCP_CONFIG` or `--config` for production, `--data-path` / `ROOT_MCP_DATA_PATH` for quick or per-session access.

## Complete Configuration Reference

### Server Settings

Controls server identity and the active analysis tier.

```yaml
server:
  name: "root-mcp"        # Server name (shown to AI)
  version: "0.1.6"        # Version (auto-detected if omitted)
  mode: "extended"        # "core" or "extended" - see Mode Selection below
```

**Mode Selection**:
- `core`: Lightweight file operations and basic statistics
- `extended`: Full physics analysis with fitting, kinematics, correlations

See the {doc}`Analysis Tiers and Mode Selection Guide </user/modes>` for detailed comparison.

### Deployment, Auth, and Policy

Controls whether ROOT-MCP starts in the existing local stdio profile or the
central Streamable HTTP service profile.

```yaml
deployment:
  profile: "local"        # "local" or "central"
  transport: "stdio"      # "stdio" or "streamable_http"
  fixed_analysis_tier: false

auth:
  required: false
  provider: "none"        # "none", "external_bearer", or "trusted_headers"
  audience: null
  issuer: null
  jwks_url: null
  jwt_algorithms: ["RS256"]
  principal_claim: "sub"
  tenant_claim: null
  roles_claim: "roles"
  scopes_claim: "scope"
  trusted_identity_headers: []
  trusted_principal_header: "x-auth-principal"
  trusted_tenant_header: "x-auth-tenant"
  trusted_roles_header: "x-auth-roles"
  trusted_scopes_header: "x-auth-scopes"
  trusted_proxy_networks: ["127.0.0.0/8", "::1/128"]

policy:
  default_tool_action: "allow"  # "allow" or "deny"
  allow_tools: []
  deny_tools: []
  require_named_resources: false
  disable_local_absolute_paths: false
  allow_central_absolute_paths: false

quotas:
  max_concurrent_requests_per_principal: 2
  max_concurrent_requests_per_tenant: 10
  max_request_seconds: 120
  max_rows_per_call: null
  max_output_bytes_per_call: null

audit:
  sink: "logger"          # "logger", "jsonl", or "both"
  jsonl_path: null        # required for "jsonl" or "both"

http:
  host: "127.0.0.1"
  port: 8000
  endpoint: "/mcp"
  origin_allowlist: []
  require_origin_header: true
  allow_local_http: false
  allow_public_bind: false
```

The default `local` profile preserves the existing Claude Desktop/stdin-stdout
workflow and permits zero-config local use. The `central` profile validates
strictly on startup: auth must be required, the provider cannot be `none`,
native ROOT must remain disabled until isolated execution exists, and
permissive local filesystem access is rejected.

`root-mcp` still starts stdio by default. `root-mcp serve-stdio` is the
explicit stdio form. `root-mcp serve-http` serves the configured Streamable HTTP
endpoint: it requires `streamable_http`, central profile unless
`http.allow_local_http` is set for local testing, authentication, an Origin
allow-list, and explicit `--allow-public-bind` before binding to a wildcard or
non-loopback host. `external_bearer` verifies JWTs through `auth.jwks_url` or
an injected validator; `trusted_headers` only accepts identity headers from
configured trusted proxy networks.

Central deployments should pass file inputs as named resources, either
`@resource/relative/path.root` or structured arguments such as
`{"resource": "cms", "path": "Run2012/file.root"}`. Raw absolute paths are
rejected in central mode unless `policy.allow_central_absolute_paths` is set
explicitly; even then, the path must stay under `security.allowed_roots`.

### Resources

Resources define named data roots and optional central ACLs.

```yaml
resources:
  - name: "cms"
    uri: "file:///data/cms"
    description: "CMS analysis inputs"
    allowed_patterns: ["*.root"]
    excluded_patterns: []
    allowed_roles: ["cms-reader"]
    allowed_principals: []
    allow_listing: true
    allow_read: true
    allow_export: false
```

In the `local` profile, resource ACL fields are permissive to preserve
backward-compatible workstation behavior. In the `central` profile, callers can
only list, read, or export from resources allowed by the resource flags and by
matching `allowed_roles` or `allowed_principals` when those lists are set.

Central write tools scope output under
`output.export_base_path / tenant_id / principal_id / session_id`. Callers
should pass relative artifact names such as `plots/mass.png`; absolute paths
and `..` traversal are rejected before files are written. Central tool calls
also emit structured JSON audit log records through the
`root_mcp.security.audit` logger.

Audit records can also be written to JSONL by configuring `audit.sink` as
`jsonl` or `both` and setting `audit.jsonl_path`.

Central quotas are process-local and keyed by the authenticated tenant and
principal, not by server-issued MCP sessions. File-handle cache entries are
also scoped by the central authorization context so one tenant or principal
cannot observe another caller's cached file object.

### Core Configuration

Settings used in both core and extended modes.

```yaml
core:
  # File caching
  cache:
    enabled: true              # Enable LRU cache for file handles
    file_cache_size: 50        # Max number of open file handles

  # Resource limits
  limits:
    max_rows_per_call: 1_000_000      # Max entries per read operation
    max_export_rows: 10_000_000       # Max entries for export operations
```

**Cache Settings**:
- Higher `file_cache_size` improves performance for repeated file access
- Lower values reduce memory usage
- Recommended: 50 for most use cases, 100+ for multi-file workflows

**Limit Settings**:
- `max_rows_per_call`: Prevents memory exhaustion from large reads
- `max_export_rows`: Limits export file sizes
- Adjust based on available memory (1M rows ≈ 100-500 MB depending on data)

### Extended Configuration

Settings used only in extended mode (ignored in core mode).

```yaml
extended:
  # Histogram settings
  histogram:
    max_bins_1d: 10_000        # Maximum bins for 1D histograms
    max_bins_2d: 1_000         # Maximum bins per dimension for 2D histograms

  # Plotting settings
  plotting:
    figure_width: 10.0         # Figure width in inches
    figure_height: 6.0         # Figure height in inches
    dpi: 100                   # Resolution
    marker_size: 4.0           # Data point marker size
    line_width: 2.0            # Line width
    grid_enabled: true         # Show grid
    default_format: "png"      # Default output format
    allowed_formats:           # Allowed export formats
      - "png"
      - "pdf"
      - "svg"

  # Fitting settings
  fitting_max_iterations: 10_000  # Max iterations for fitting algorithms
```

**Histogram Limits**:
- Prevents memory issues from excessive binning
- 1D: 10,000 bins is typically sufficient
- 2D: 1,000 × 1,000 = 1M bins (reasonable for most analyses)

**Plotting Customization**:
- Adjust `dpi` for quality vs file size tradeoff
- `default_format`: "png" for quick viewing, "pdf" for publications
- Matplotlib style settings can be customized

### Data Resources

Define data sources accessible to the server.

```yaml
resources:
  - name: "my_analysis"                    # Unique identifier
    uri: "file:///path/to/data"            # Base URI
    description: "My Physics Analysis"     # Description for AI
    allowed_patterns: ["*.root"]           # File patterns to include
    max_file_size_gb: 10                   # Max file size (optional)

  - name: "remote_data"
    uri: "root://xrootd.server.edu//path"  # XRootD URI
    description: "Remote Dataset"
    allowed_patterns: ["Run*.root"]
```

**URI Protocols**:
- `file://`: Local filesystem
- `root://`: XRootD protocol (requires `pip install "root-mcp[xrootd]"`)
- `http://`, `https://`: HTTP(S) access

**Resource Naming**:
- Use descriptive names (e.g., "cms_2015_data", "simulation_ttbar")
- Names shown to AI for context
- Must be unique within configuration

### Security Settings

Critical security constraints for file access.

```yaml
security:
  # Allowed root directories
  allowed_roots:
    - "/data/physics"
    - "/home/user/analysis"
    - "/tmp/root_mcp_exports"

  # Allowed URI protocols
  allowed_protocols:
    - "file"
    - "root"
    - "http"
    - "https"

  # Path traversal limits
  max_path_depth: 10           # Max directory depth
```

**Security Best Practices**:
1. **Restrict `allowed_roots`**: Only include necessary directories
2. **Separate read/write paths**: Different roots for input data and exports
3. **Limit protocols**: Only enable protocols you need
4. **Monitor logs**: Check for security violations

The default `allowed_roots: []` behavior is a local profile convenience, not a
central deployment setting. Treat any shared HTTP deployment as a separate
security profile with authenticated callers and explicit resource boundaries.

**Path Validation**:
- All file paths validated against `allowed_roots`
- Path traversal (`..`) blocked
- Symlinks validated
- Write operations require separate input/output paths

### Output Settings

Configuration for data export operations.

```yaml
output:
  export_base_path: "/tmp/root_mcp_exports"  # Base directory for exports
  allowed_formats:                            # Allowed export formats
    - "json"
    - "csv"
    - "parquet"
  retention_days: null                        # Optional cleanup age
  max_total_bytes: null                       # Optional cleanup size cap
```

**Export Formats**:
- **JSON**: Human-readable, good for small datasets
- **CSV**: Compatible with spreadsheets and analysis tools
- **Parquet**: Efficient columnar format, best for large datasets

**Export Path Security**:
- Must be under `output.export_base_path`
- Must differ from input file path
- All exports logged for audit trail
- Central exports are scoped by tenant, principal, and session
- Use `root-mcp cleanup-exports --config config.yaml --dry-run` to preview
  configured retention cleanup

### Project-Local Output

To save plots and exports within your project directory (e.g., `./plots`), update your configuration:

1.  Create the directory in your project root: `mkdir -p plots`
2.  Add the directory to `security.allowed_roots`
3.  Set `output.export_base_path` to this directory

```yaml
security:
  allowed_roots:
    - "/path/to/project/data"
    - "/path/to/project/plots"  # Must be explicitly allowed

output:
  export_base_path: "/path/to/project/plots"
```

**Note**: When using tools that accept output paths, you can use relative paths (e.g., `plots/output.png`) if the server is running from the project root. However, absolute paths are recommended for configuration settings.

### Feature Flags

Enable/disable experimental features.

```yaml
features:
  enable_remote_files: true      # Allow remote file access
  enable_caching: true           # Enable result caching
  enable_streaming: true         # Enable streaming for large files
```

## Complete Example Configurations

### Example 1: Local Analysis (Extended Mode)

```yaml
# Server settings
server:
  name: "root-mcp"
  mode: "extended"

# Core configuration
core:
  cache:
    enabled: true
    file_cache_size: 50
  limits:
    max_rows_per_call: 1_000_000
    max_export_rows: 10_000_000

# Extended configuration
extended:
  histogram:
    max_bins_1d: 10_000
    max_bins_2d: 1_000
  plotting:
    figure_width: 10.0
    figure_height: 6.0
    dpi: 100
    default_format: "png"
  fitting_max_iterations: 10_000

# Data resources
resources:
  - name: "cms_data"
    uri: "file:///data/cms/2015"
    description: "CMS 2015 Data"
    allowed_patterns: ["*.root"]

# Security
security:
  allowed_roots:
    - "/data/cms"
    - "/home/user/exports"
  allowed_protocols: ["file"]

# Output
output:
  export_base_path: "/home/user/exports"
  allowed_formats: ["json", "csv", "parquet"]
```

### Example 2: Remote Access (Core Mode)

```yaml
# Lightweight setup for remote file inspection
server:
  name: "root-mcp"
  mode: "core"

core:
  cache:
    enabled: true
    file_cache_size: 20  # Lower cache for remote files
  limits:
    max_rows_per_call: 100_000  # Smaller reads for remote

resources:
  - name: "grid_data"
    uri: "root://xrootd.grid.org//store/data"
    description: "Grid Storage"
    allowed_patterns: ["*.root"]

security:
  allowed_roots:
    - "/tmp/root_mcp_cache"
  allowed_protocols: ["root", "file"]

output:
  export_base_path: "/tmp/root_mcp_cache"
  allowed_formats: ["json", "parquet"]
```

### Example 3: High-Performance Analysis

```yaml
# Optimized for large-scale analysis
server:
  name: "root-mcp"
  mode: "extended"

core:
  cache:
    enabled: true
    file_cache_size: 100  # Large cache for multi-file analysis
  limits:
    max_rows_per_call: 5_000_000  # Large reads for performance
    max_export_rows: 50_000_000

extended:
  histogram:
    max_bins_1d: 50_000  # Fine binning
    max_bins_2d: 2_000
  plotting:
    dpi: 300  # High resolution
    default_format: "pdf"

resources:
  - name: "simulation"
    uri: "file:///data/simulation/ttbar"
    description: "ttbar Simulation"
    allowed_patterns: ["*.root"]

security:
  allowed_roots:
    - "/data/simulation"
    - "/data/results"
  allowed_protocols: ["file"]

output:
  export_base_path: "/data/results"
  allowed_formats: ["parquet"]  # Only efficient format
```

## Environment Variables

Every `config.yaml` field now has a matching `ROOT_MCP_*` environment variable. See the [Complete Env Var & CLI Reference](#complete-env-var--cli-reference) below for the full table. A few of the most commonly used variables:

```bash
# Data directory — no config file needed
export ROOT_MCP_DATA_PATH="/path/to/your/data"

# Multiple directories (colon-separated)
export ROOT_MCP_DATA_PATH="/data/run2024:/data/simulation"

# Configuration file location
export ROOT_MCP_CONFIG="/path/to/config.yaml"

# Override mode
export ROOT_MCP_MODE="core"

# Enable native ROOT
export ROOT_MCP_ENABLE_ROOT="1"

# Override log level
export ROOT_MCP_LOG_LEVEL="DEBUG"
```

---

## Complete Env Var & CLI Reference

Every field is configurable from three sources (later wins): YAML → env var → CLI flag.

### Already Shipped

| Config field | Env var | CLI flag |
|---|---|---|
| `resources[].uri` (local paths) | `ROOT_MCP_DATA_PATH` (colon-sep) | `--data-path DIR` (append) |
| `features.enable_root` | `ROOT_MCP_ENABLE_ROOT` | `--enable-root` |

### Server & Mode

| Config field | Env var | CLI flag | Type | Default |
|---|---|---|---|---|
| `server.mode` | `ROOT_MCP_MODE` | `--mode core\|extended` | str | `extended` |
| `server.name` | `ROOT_MCP_SERVER_NAME` | `--server-name NAME` | str | `root-mcp` |

### Deployment, Auth, and Policy

| Config field | Env var | CLI flag | Type | Default |
|---|---|---|---|---|
| `deployment.profile` | `ROOT_MCP_DEPLOYMENT_PROFILE` | `--profile local\|central` | str | `local` |
| `deployment.transport` | `ROOT_MCP_TRANSPORT` | `--transport stdio\|streamable-http` | str | `stdio` |
| `auth.required` | `ROOT_MCP_AUTH_REQUIRED` (`1`/`true`/`yes`) | `--auth-required` | bool | `false` |
| `auth.provider` | `ROOT_MCP_AUTH_PROVIDER` | `--auth-provider none\|external-bearer\|trusted-headers` | str | `none` |
| `policy.default_tool_action` | `ROOT_MCP_POLICY_DEFAULT_TOOL_ACTION` | Not yet exposed | str | `allow` |

### HTTP Startup

| Config field | Env var | CLI flag | Type | Default |
|---|---|---|---|---|
| `http.host` | `ROOT_MCP_HTTP_HOST` | `--host HOST` | str | `127.0.0.1` |
| `http.port` | `ROOT_MCP_HTTP_PORT` | `--port PORT` | int | `8000` |
| `http.endpoint` | `ROOT_MCP_HTTP_ENDPOINT` | `--endpoint PATH` | str | `/mcp` |
| `http.origin_allowlist` | `ROOT_MCP_HTTP_ORIGINS` (`,` sep) | `--origin ORIGIN` (append) | list[str] | `[]` |
| `http.allow_local_http` | `ROOT_MCP_HTTP_ALLOW_LOCAL` | `--allow-local-http` | bool | `false` |
| `http.allow_public_bind` | `ROOT_MCP_HTTP_ALLOW_PUBLIC_BIND` | `--allow-public-bind` | bool | `false` |

### Quotas

| Config field | Env var | CLI flag | Type | Default |
|---|---|---|---|---|
| `quotas.max_concurrent_requests_per_principal` | Not yet exposed | Not yet exposed | int | `2` |
| `quotas.max_concurrent_requests_per_tenant` | Not yet exposed | Not yet exposed | int | `10` |
| `quotas.max_request_seconds` | Not yet exposed | Not yet exposed | int | `120` |
| `quotas.max_rows_per_call` | Not yet exposed | Not yet exposed | int \| null | `null` |
| `quotas.max_output_bytes_per_call` | Not yet exposed | Not yet exposed | int \| null | `null` |

### Security

| Config field | Env var | CLI flag | Type | Default |
|---|---|---|---|---|
| `security.allowed_roots` | `ROOT_MCP_ALLOWED_ROOTS` (`:` sep) | `--allowed-root DIR` (append) | list[str] | `[]` |
| `security.allow_remote` | `ROOT_MCP_ALLOW_REMOTE` (`1`/`true`/`yes`) | `--allow-remote` / `--no-allow-remote` | bool | `false` |
| `security.allowed_protocols` | `ROOT_MCP_ALLOWED_PROTOCOLS` (`,` sep) | `--allowed-protocols p1,p2` | list[str] | `["file"]` |
| `security.max_path_depth` | `ROOT_MCP_MAX_PATH_DEPTH` | `--max-path-depth N` | int | `10` |

### Output / Export

| Config field | Env var | CLI flag | Type | Default |
|---|---|---|---|---|
| `output.export_base_path` | `ROOT_MCP_EXPORT_PATH` | `--export-path DIR` | str | `/tmp/root_mcp_output` |
| `output.allowed_formats` | `ROOT_MCP_EXPORT_FORMATS` (`,` sep) | `--export-formats json,csv` | list[str] | `["json","csv","parquet"]` |
| `features.enable_export` | `ROOT_MCP_ENABLE_EXPORT` (`0`/`false`/`no`) | `--no-export` | bool | `true` |

### Core Limits & Cache

| Config field | Env var | CLI flag | Type | Default |
|---|---|---|---|---|
| `core.limits.max_rows_per_call` | `ROOT_MCP_MAX_ROWS` | `--max-rows N` | int | `1_000_000` |
| `core.limits.max_export_rows` | `ROOT_MCP_MAX_EXPORT_ROWS` | `--max-export-rows N` | int | `10_000_000` |
| `core.cache.enabled` | `ROOT_MCP_CACHE` (`0`/`false`/`no`) | `--no-cache` | bool | `true` |
| `core.cache.file_cache_size` | `ROOT_MCP_CACHE_SIZE` | `--cache-size N` | int | `50` |

### Extended Analysis

| Config field | Env var | CLI flag | Type | Default |
|---|---|---|---|---|
| `extended.histogram.max_bins_1d` | `ROOT_MCP_MAX_BINS_1D` | `--max-bins-1d N` | int | `10_000` |
| `extended.histogram.max_bins_2d` | `ROOT_MCP_MAX_BINS_2D` | `--max-bins-2d N` | int | `1_000` |
| `extended.fitting_max_iterations` | `ROOT_MCP_FITTING_ITERATIONS` | `--fitting-iterations N` | int | `10_000` |
| `extended.plotting.dpi` | `ROOT_MCP_PLOT_DPI` | `--plot-dpi N` | int | `100` |
| `extended.plotting.default_format` | `ROOT_MCP_PLOT_FORMAT` | `--plot-format png\|pdf\|svg` | str | `png` |
| `extended.plotting.figure_width` | `ROOT_MCP_PLOT_WIDTH` | `--plot-width N` | float | `10.0` |
| `extended.plotting.figure_height` | `ROOT_MCP_PLOT_HEIGHT` | `--plot-height N` | float | `6.0` |

### Native ROOT Execution

| Config field | Env var | CLI flag | Type | Default |
|---|---|---|---|---|
| `root_native.execution_backend` | `ROOT_MCP_ROOT_BACKEND` | `--root-backend BACKEND` | `local_subprocess` or `disabled` | `local_subprocess` |
| `root_native.execution_timeout` | `ROOT_MCP_ROOT_TIMEOUT` | `--root-timeout N` | int (s) | `60` |
| `root_native.working_directory` | `ROOT_MCP_ROOT_WORKDIR` | `--root-workdir DIR` | str | `/tmp/root_mcp_native` |
| `root_native.max_output_size` | `ROOT_MCP_ROOT_MAX_OUTPUT` | `--root-max-output N` | int (B) | `10_000_000` |
| `root_native.max_code_length` | `ROOT_MCP_ROOT_MAX_CODE` | `--root-max-code N` | int (chars) | `100_000` |

Native ROOT execution is local-only in this release. Central deployments must
keep `features.enable_root: false`; the `disabled` backend is the documented
central posture until a container, batch, or Kubernetes isolated backend is
implemented.

### Remote Resources

| Mechanism | Syntax | Example |
|---|---|---|
| CLI | `--resource NAME=URI[\|DESCRIPTION]` (append) | `--resource cms=root://xrootd.cern.ch//store` |
| Env var | `ROOT_MCP_RESOURCES` — semicolon-sep list of `NAME=URI[\|DESC]` | `ROOT_MCP_RESOURCES="cms=root://…;local=file:///data"` |

Notes:
- Use `|` (pipe) to separate description from URI — colons are ambiguous inside URIs.
- YAML-declared resources take precedence: a spec whose URI already exists is silently skipped.
- Both sources are **additive**: env var resources plus CLI resources are both added.

### Log Level

| Mechanism | Env var | CLI flag | Notes |
|---|---|---|---|
| Log level | `ROOT_MCP_LOG_LEVEL` | `--log-level DEBUG\|INFO\|WARNING\|ERROR` | Applied before config loading |

## Configuration Validation

The server validates configuration on startup:

**Common Errors**:
- Invalid mode (must be "core" or "extended")
- Invalid deployment profile (must be "local" or "central")
- Central profile without required auth, a non-`none` provider, restricted local
  filesystem access, and an explicit policy shape
- `serve-http` without Streamable HTTP transport, auth, Origin validation, or
  safe host-binding settings
- Invalid URI format in resources
- Export path not in `allowed_roots` (add the path or set `allowed_roots: []` for permissive mode)

**Validation Messages**:
```
✓ Configuration loaded successfully
✓ Mode: extended
✓ Resources: 2 configured
✓ Security: 3 allowed roots
```

## Dynamic Configuration

Some settings can be changed at runtime:

**Mode Switching**:
```json
{
  "tool": "switch_mode",
  "arguments": {"mode": "core"}
}
```

**Cache Management**:
- Cache automatically managed by LRU policy
- Manual cache clear not currently supported

## Performance Tuning

### For Small Files (<1 GB)
```yaml
core:
  cache:
    file_cache_size: 20
  limits:
    max_rows_per_call: 1_000_000
```

### For Large Files (>10 GB)
```yaml
core:
  cache:
    file_cache_size: 5  # Fewer handles for large files
  limits:
    max_rows_per_call: 100_000  # Smaller chunks
```

### For Multi-File Analysis
```yaml
core:
  cache:
    file_cache_size: 100  # Cache many files
  limits:
    max_rows_per_call: 500_000
```

### For Remote Files
```yaml
core:
  cache:
    file_cache_size: 10  # Limited caching
  limits:
    max_rows_per_call: 50_000  # Small reads
```

## Troubleshooting

### Configuration Not Found
**Error**: `Failed to load configuration`
**Solution**: Check `ROOT_MCP_CONFIG` environment variable or place `config.yaml` in current directory

### Security Violation
**Error**: `SecurityError: Path not in allowed roots`
**Solution**: Add path to `security.allowed_roots`

### Mode Not Available
**Error**: `Failed to switch to extended mode`
**Solution**: Ensure scipy and matplotlib are installed

### Resource Limits Exceeded
**Error**: `Max rows per call exceeded`
**Solution**: Increase `core.limits.max_rows_per_call` or read in chunks

## Best Practices

1. **Start Conservative**: Begin with default limits, increase as needed
2. **Separate Environments**: Different configs for development/production
3. **Security First**: Minimal `allowed_roots`, only necessary protocols
4. **Monitor Resources**: Watch memory usage, adjust cache size
5. **Use Mode Switching**: Start in core, switch to extended when needed
6. **Document Changes**: Comment your config file with reasoning

## See Also

- {doc}`Mode Selection Guide </user/modes>`: Detailed mode comparison
- {doc}`Architecture </developer/architecture>`: System design details
- {doc}`Tool Reference </user/tools_reference>`: Available tools per mode
