# Central Deployment

Use the `central` profile only for shared Streamable HTTP deployments. Personal
workstation use should stay on local stdio unless there is a specific reason to
test HTTP locally.

Central deployments must use authenticated callers, explicit Origin validation,
named resources, scoped exports, quotas, and deny-by-default tool policy.

## Supported Posture

Central mode supports the Python/uproot analysis tools behind policy and
resource ACLs. Native ROOT execution is local-only until an isolated backend
exists:

```yaml
features:
  enable_root: false

root_native:
  execution_backend: "disabled"
```

`run_root_code`, `run_rdataframe`, `run_root_macro`, and `switch_mode` should be
absent from the central allow-list or explicitly denied.

## Start The Service

Run the HTTP service behind TLS and an identity-aware reverse proxy whenever
possible:

```bash
root-mcp serve-http \
  --config /etc/root-mcp/config.yaml \
  --profile central \
  --auth-required \
  --auth-provider trusted-headers \
  --origin https://analysis.example.org \
  --host 127.0.0.1 \
  --port 8000
```

Use `--allow-public-bind` only when the service intentionally binds to a
non-loopback address and the network boundary is already controlled.

## Minimal Config Shape

Start from a deny-by-default policy and add only the tools your users need:

```yaml
server:
  mode: "extended"

deployment:
  profile: "central"
  transport: "streamable_http"
  fixed_analysis_tier: true

auth:
  required: true
  provider: "trusted_headers"
  trusted_principal_header: "x-auth-principal"
  trusted_tenant_header: "x-auth-tenant"
  trusted_roles_header: "x-auth-roles"
  trusted_scopes_header: "x-auth-scopes"
  trusted_proxy_networks: ["127.0.0.0/8", "::1/128"]

policy:
  default_tool_action: "deny"
  allow_tools:
    - get_server_info
    - list_files
    - inspect_file
    - validate_file
    - list_branches
    - read_branches
    - get_branch_stats
    - compute_histogram
    - compute_histogram_2d
    - plot_histogram_1d
    - plot_histogram_2d
    - export_data
  deny_tools:
    - switch_mode
    - run_root_code
    - run_rdataframe
    - run_root_macro
  require_named_resources: true
  disable_local_absolute_paths: true
  allow_central_absolute_paths: false

http:
  host: "127.0.0.1"
  port: 8000
  endpoint: "/mcp"
  origin_allowlist: ["https://analysis.example.org"]
  require_origin_header: true

quotas:
  max_concurrent_requests_per_principal: 2
  max_concurrent_requests_per_tenant: 10
  max_request_seconds: 120
  max_rows_per_call: 1000000
  max_output_bytes_per_call: 50000000

features:
  enable_export: true
  enable_root: false

root_native:
  execution_backend: "disabled"
```

Restrictive starter configs and Kubernetes examples live in
`examples/central/`.

## Authentication

Use `trusted_headers` when a reverse proxy authenticates users and strips any
client-supplied identity headers before adding its own. Keep
`trusted_proxy_networks` limited to the proxy addresses.

Use `external_bearer` when clients send JWT bearer tokens directly to ROOT-MCP.
Configure `auth.audience`, `auth.issuer`, and `auth.jwks_url` to match the
identity provider. Requests without a valid token are rejected before policy or
tool dispatch.

## Data And Exports

Use named resources for every central data source:

```yaml
security:
  allowed_roots: ["/data/root"]

resources:
  - name: "run3"
    uri: "file:///data/root"
    allowed_patterns: ["*.root"]
    allowed_roles: ["analysis-reader"]
    allow_listing: true
    allow_read: true
    allow_export: false
```

Central callers should pass file inputs as `@resource/relative/file.root` or
structured references such as:

```json
{"resource": "run3", "path": "sample.root"}
```

For remote-only XRootD deployments, disable local absolute paths and avoid
`file` in `security.allowed_protocols`.

Write tools should pass artifact-relative output paths such as
`plots/mass.png`. The server resolves them under
`output.export_base_path / tenant_id / principal_id / session_id` and rejects
absolute paths or traversal.

## Runtime Operations

Central tool calls emit structured JSON through the `root_mcp.security.audit`
logger. If log collection alone is not enough, also write JSONL:

```yaml
audit:
  sink: "both"
  jsonl_path: "/var/log/root-mcp/audit.jsonl"
```

Export cleanup is operator-driven:

```yaml
output:
  export_base_path: "/srv/root-mcp/exports"
  retention_days: 14
  max_total_bytes: 50000000000
```

Preview and apply cleanup with:

```bash
root-mcp cleanup-exports --config /etc/root-mcp/config.yaml --dry-run
root-mcp cleanup-exports --config /etc/root-mcp/config.yaml
```

After deployment, run an external MCP client smoke test from outside the server
process. The repository includes:

```bash
python scripts/smoke_external_http_client.py
```

## Container Checklist

- Run as a non-root user.
- Prefer a read-only root filesystem.
- Mount input data read-only.
- Mount writable directories only for exports, temporary files, audit JSONL,
  and explicit cache/work directories.
- Do not mount `/`, `/home`, Docker sockets, host credentials, or broad host
  paths into the service.
- Set CPU and memory limits.
- Keep the service internal unless it is exposed through authenticated ingress
  or an identity-aware gateway.
- Limit egress to required identity provider, data, DNS, and log endpoints.
