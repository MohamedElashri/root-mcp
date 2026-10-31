# ROOT-MCP Architecture

ROOT-MCP provides an MCP server and a CLI backed by the same ROOT file analysis
components. Version 0.3.1 uses MCP Python SDK 2.3+ within the 2.x line.

## Analysis tier, deployment profile and transport

- **Analysis tier**: `server.mode` selects `core` or `extended`. Native ROOT tools
  additionally require PyROOT, an enabled feature flag and a local subprocess backend.
- **Deployment profile**: `local` is for a trusted workstation; `central` applies
  authentication, tool policy, named-resource ACLs, quotas and scoped exports.
- **Transport**: stdio is the local default. `root-mcp serve-http` starts the
  authenticated Streamable HTTP endpoint.

Core mode advertises nine tools for file discovery, bounded reads, statistics,
exports and server management. Extended mode adds eight histogram, fit,
kinematics, correlation and plotting tools. The three native execution tools are
local-only. Policy can hide or deny tools independently of the selected tier.

Extended components load when extended mode is selected at startup or by a local
`switch_mode` call, rather than on the first analysis call. Switching affects the
whole server process; clients must refresh their catalog afterward. Central
services disable switching and pin their analysis tier.

## Request flow

1. The MCP SDK handles the transport, protocol revision and wire serialization.
2. The HTTP wrapper validates Origin and authentication and attaches the caller's
   principal, tenant, roles and scopes to the request.
3. The server validates tool arguments against the advertised JSON Schema.
4. Tool policy, resource permissions and quotas gate execution.
5. Core or extended handlers call the shared I/O and analysis components.
6. The server returns a structured payload plus matching JSON text, with
   `isError` set for tool failures. Central calls also produce audit events.

Annotations describe tool behavior for clients but do not grant authorization.
Read-only analysis, file-writing tools, mode changes and native execution have
separate side-effect and retry hints. Unknown or unavailable tool names use
JSON-RPC invalid-params errors; argument validation failures are actionable tool
results.

## MCP protocol behavior

For revision 2026-07-28, each request carries its protocol metadata and HTTP
routing headers. Clients can call `server/discover` for versioned identity,
capabilities and concise server instructions. Modern requests do not require an
`initialize` handshake or `Mcp-Session-Id`. The SDK retains the legacy handshake
and session transport for older clients.

`tools/list` and the resource catalog use private caching with zero freshness,
because mode, policy and caller access can change. Resource listings are filtered
by the current authenticated request. `resources/read` returns JSON catalog
metadata for the listed `root-mcp://name` URIs, without disclosing backing storage
paths. Reading ROOT data uses the authorized tools and `@resource/relative.root`
references. `get_server_info` also returns resource descriptors for tool-only
clients.

The server does not advertise optional tasks, sampling, elicitation, prompts,
MCP Apps or catalog-change subscriptions. A client backgrounding a call does not
make it a resumable server task.

## Source layout

```text
src/
├── root_mcp/
│   ├── server.py             # MCP catalog, validation, dispatch and entry point
│   ├── protocol.py           # Agent instructions, annotations and schema checks
│   ├── config.py             # Pydantic settings, YAML, environment and CLI options
│   ├── transport/            # Stdio and authenticated HTTP runners
│   ├── security/             # Caller context, auth, policy, ACLs, quotas and audit
│   ├── observability/        # Process-local metrics
│   ├── core/
│   │   ├── io/               # File/cache lifecycle, readers, export and retention
│   │   ├── operations/       # Basic statistics
│   │   └── tools/            # Discovery and data access handlers
│   ├── extended/
│   │   ├── analysis/         # Histograms, fitting, kinematics, correlations, plots
│   │   ├── root_native/      # Local subprocess execution and code templates
│   │   └── tools/            # Extended and native ROOT handlers
│   └── common/               # Shared helpers, errors and ROOT availability
└── root_cli/                 # Click CLI and commands using the same backend
```

## Data and execution boundaries

`FileManager` manages uproot file handles and a bounded cache. Central cache keys
include authorization context. `ResourceResolver` applies listing/read/export
permissions and resolves named paths; `PathValidator` checks storage and output
paths. Exports are scoped to the configured output root and caller identity.

Central quotas are process-local. A timed-out worker thread is not guaranteed to
have stopped, so clients should use bounded reads and avoid automatic write
retries. Native ROOT runs in a subprocess with timeout and code validation; this
is not an operating-system isolation boundary. It is restricted to trusted local
use and must not be enabled in a shared central deployment.

`root-cli` uses the same analysis backend without an MCP connection. Its command
arguments differ from MCP schemas: for example, CLI plotting consumes cached
histogram JSON while MCP plotting tools read branch data.
