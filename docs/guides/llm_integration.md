# LLM Integration Guide

ROOT-MCP connects coding agents to CERN ROOT files over stdio or authenticated
Streamable HTTP. Client configuration and transport availability vary by client.
The examples below were checked against official documentation on 2026-10-31.

## Local setup

Install `uv`, then use `uvx root-mcp --data-path /absolute/path/to/data` as the
server command. Clients launch this process themselves. For an existing Python
installation, use `root-mcp` directly instead of `uvx root-mcp`. Native PyROOT
must be installed separately and explicitly enabled with `--enable-root`.

For development against a checkout, replace `uvx root-mcp` with:

```bash
uv run --directory /absolute/path/to/root-mcp root-mcp
```

Use absolute data/config paths: clients can start servers from different working
directories. If a desktop client cannot find `uvx`, use its absolute executable
path. Server logs go to stderr; stdout carries MCP messages.

## Choose a client

Use the configuration belonging to the agent running your tools. For example,
Copilot in VS Code, the Codex extension and Claude Code each have their own MCP
configuration. ACP connects an editor to an agent; MCP connects that agent to
ROOT-MCP. An editor integration does not guarantee that every agent inherits its
MCP servers.

| Client | Project configuration | Container for server definitions |
|---|---|---|
| VS Code Local harness | `.vscode/mcp.json` | `servers` |
| VS Code Copilot harness / Copilot CLI | `.mcp.json` | `mcpServers` |
| Cursor | `.cursor/mcp.json` | `mcpServers` |
| Zed Agent | Zed settings, opened with `zed: open settings file` | `context_servers` |
| Antigravity app, IDE and CLI | `.agents/mcp_config.json` | `mcpServers` |
| Claude Code | `.mcp.json` | `mcpServers` |
| Codex CLI / IDE extension | `.codex/config.toml` in a trusted project | `mcp_servers` TOML tables |
| Qwen Code CLI | `.qwen/settings.json` | `mcpServers` |
| Pi | `.pi/mcp.json` in a trusted project | `mcpServers` |
| Oh My Pi (OMP) | `.omp/mcp.json` | `mcpServers` |
| OpenCode v2 | `opencode.json` or `opencode.jsonc` | `mcp.servers` |
| Cline | MCP Servers → Configure MCP Servers | `mcpServers` |
| Roo Code | `.roo/mcp.json` | `mcpServers` |
| Continue | Merge into `~/.continue/config.yaml` | `mcpServers` YAML list |
| Goose | `~/.config/goose/config.yaml` | `extensions` YAML map |

Ready-to-edit files are in
[examples/clients](https://github.com/MohamedElashri/root-mcp/tree/main/examples/clients).
Replace the absolute data-path placeholder and merge the server entry into any
existing configuration. These files are templates, not automatic installers.

## IDEs

### VS Code

For the Local harness, put this in `.vscode/mcp.json`:

```json
{
  "servers": {
    "root-mcp": {
      "type": "stdio",
      "command": "uvx",
      "args": ["root-mcp", "--data-path", "/absolute/path/to/data"]
    }
  }
}
```

Use **MCP: List Servers** to start the server and inspect its output. Enable its
tools in the chat tool picker and call `get_server_info`.
Current Copilot harness sessions also read portable workspace-root `.mcp.json`
using `mcpServers`; `.vscode/mcp.json` remains a compatibility option for the
Local harness. Match the format to the installed VS Code release and selected
harness. The Codex and Claude extensions use their respective CLI configuration,
not this `servers` object. See Microsoft's
[configuration reference](https://code.visualstudio.com/docs/agents/reference/mcp-configuration).

### Cursor

Copy the `mcpServers` definition from `examples/clients/cursor.json` into
`.cursor/mcp.json`, or `~/.cursor/mcp.json` for personal global configuration.
Open **Customize → MCPs** (older releases: **Settings → Tools & MCP**) and verify
the server connects before enabling its tools in Agent chat. Remote servers use
`url` and `headers`. See [Cursor MCP](https://prod.cursor.com/docs/mcp).

### Zed

Merge this into Zed's settings file:

```json
{
  "context_servers": {
    "root-mcp": {
      "command": "uvx",
      "args": ["root-mcp", "--data-path", "/absolute/path/to/data"]
    }
  }
}
```

Open **Settings → AI → MCP Servers** to check the status and enable the tools for
your agent profile. This config applies directly to Zed Agent. External ACP
agents can receive forwarded servers where supported; terminal agents still
read their own native configuration. See [Zed MCP](https://zed.dev/docs/ai/mcp).

### Antigravity app and IDE

Use `examples/clients/antigravity.json` in `.agents/mcp_config.json` for a
workspace, or merge it into `~/.gemini/config/mcp_config.json` globally. The
remaining `.gemini` directory name is intentional. In the IDE's agent side panel,
open **MCP Servers → Manage MCP Servers → View raw config** to locate the active
file and reload it. Antigravity CLI uses the same documented config format.
For remote ROOT-MCP, use `serverUrl` and `headers`, including the deployment's
required `Origin`. See [Antigravity MCP](https://antigravity.google/docs/mcp).

## Terminal agents

### Codex

```bash
codex mcp add root-mcp -- uvx root-mcp --data-path /absolute/path/to/data
codex mcp list
```

Alternatively merge `examples/clients/codex.toml` into `~/.codex/config.toml`, or
a trusted project's `.codex/config.toml`. The CLI and IDE extension share this
configuration. Use `/mcp` to check the connection. Server instructions describe
cross-tool workflows; allow/deny lists and approval settings remain client
controls independent of server authorization. See the
[official Codex MCP guide](https://learn.chatgpt.com/docs/extend/mcp).

### Claude Code

```bash
claude mcp add --transport stdio --scope project root-mcp -- uvx root-mcp --data-path /absolute/path/to/data
claude mcp list
```

The `--` separates Claude's options from the executable and server arguments.
Use `--scope user` for a personal server across projects. Project definitions
live in `.mcp.json`; `examples/clients/claude.json` shows the format. Use `/mcp`
to check status. Tool search can load ROOT tools on demand using their names,
descriptions and server instructions. Refresh the catalog after `switch_mode`.
See [Claude Code MCP](https://code.claude.com/docs/en/mcp).

### Antigravity CLI (`agy`)

This replaces the former Gemini CLI setup instructions. Google's
[migration guide](https://antigravity.google/docs/cli/gcli-migration/) covers
moving existing Gemini CLI configuration to Antigravity.

```bash
agy mcp add root-mcp uvx root-mcp --data-path /absolute/path/to/data
agy mcp list
```

The installed `agy` CLI requires its own flags before the server name. The
command above registers a server through the CLI; for workspace-only setup,
edit `.agents/mcp_config.json` using the Antigravity example instead. Global
configuration is `~/.gemini/config/mcp_config.json`, rather than the legacy
Gemini `settings.json`. Use `/mcp` inside an active session to inspect live
connections. A successful `agy mcp list` is a configuration check, not proof of
a completed tool call. See [CLI reference](https://antigravity.google/docs/cli/reference/).

### Qwen Code (`qwen`)

```bash
qwen mcp add --scope project root-mcp uvx root-mcp --data-path /absolute/path/to/data
qwen mcp list
```

Qwen Code uses `mcpServers` in `.qwen/settings.json` or
`~/.qwen/settings.json`; merge `examples/clients/qwen.json` there. Use `/mcp` in
an active session to inspect discovered tools. Server discovery can happen in
the background, so wait for a connected status before requesting analysis.
See [Qwen Code MCP](https://qwenlm.github.io/qwen-code-docs/en/users/features/mcp/).

### Pi (`pi`)

Current Pi releases have native MCP support:

```bash
pi mcp add root-mcp -- uvx root-mcp --data-path /absolute/path/to/data
pi mcp list
```

This writes `~/.pi/agent/mcp.json`. Add `--local` before `--` for a trusted
project's `.pi/mcp.json`. The JSON shape is shown in `examples/clients/pi.json`.
Use `/mcp` in Pi and `/reload` after external config changes. Pi can expose tools
through code mode, deferred tool search or direct tools. Older Pi releases and
forks may require an MCP extension; check `pi --version` and `pi mcp --help`.
See [Pi's MCP guide](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/mcp.md).

### Oh My Pi (`omp`)

Merge `examples/clients/omp.json` into `.omp/mcp.json` or
`~/.omp/agent/mcp.json`, then start `omp` and inspect `/mcp`. OMP also imports
other clients' configurations; use its native file to avoid relying on an import
adapter for a newer client schema. Discoverable tools may be mounted as `xd://`
devices instead of appearing as top-level tools. Their absence from an RPC
`dumpTools` list alone does not indicate a failed MCP connection.
See [OMP MCP configuration](https://github.com/can1357/oh-my-pi/blob/main/docs/mcp-config.md).

## Other community harnesses

### OpenCode

Current v2 documentation uses `mcp.servers`, with the executable and arguments in
one array. Merge `examples/clients/opencode-v2.json` into `opencode.json`, or use:

```bash
opencode mcp add root-mcp -- uvx root-mcp --data-path /absolute/path/to/data
opencode mcp list
```

For v1 installations, consult that release's documentation: v1 server names sit
directly under `mcp`. V2 also changed enable/disable configuration. Prefer the
native `mcp add` command when crossing versions. See
[OpenCode v2 MCP](https://dev.opencode.ai/v2/docs/mcp-servers/).

### GitHub Copilot CLI

```bash
copilot mcp add root-mcp -- uvx root-mcp --data-path /absolute/path/to/data
copilot mcp list
```

Merge `examples/clients/copilot.json` into `~/.copilot/mcp-config.json`, or use
a trusted repository's `.mcp.json`. In a session, `/mcp` shows connection status
and tools. A shell shim called `copilot` can exist before the CLI is actually
installed; check `copilot --version`. See
[Copilot CLI MCP](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-mcp-servers).

### Cline and Roo Code

Both accept local `command`/`args` definitions under `mcpServers`.
In Cline, open **MCP Servers → Configure → Configure MCP Servers** and merge
`examples/clients/cline.json`. Cline CLI uses
`~/.cline/data/settings/cline_mcp_settings.json`.
In Roo Code, use **Edit Project MCP** or merge `examples/clients/roo.json` into
`.roo/mcp.json`. Leave automatic approvals unset until you choose which tools
to trust. Remote transport type spellings differ between clients; do not copy
an SSE example for ROOT-MCP's Streamable HTTP endpoint.
See [Cline](https://github.com/cline/cline/blob/main/docs/mcp/mcp-overview.mdx)
and [Roo Code](https://roocodeinc.github.io/Roo-Code/features/mcp/using-mcp-in-roo/).

### Continue

Merge the `mcpServers` list from `examples/clients/continue.yaml` into the active
Continue YAML configuration, retaining its existing models and other settings.
Use Agent mode with a model that supports tools, then verify `get_server_info`.
Continue uses a list of named YAML entries rather than a JSON server-name map.
See [Continue's configuration reference](https://docs.continue.dev/reference).

### Goose

Run `goose configure`, choose **Add Extension → Command-Line Extension**, and
enter `uvx root-mcp --data-path /absolute/path/to/data`. Alternatively, add it
for the current interactive session with:

```text
/extension uvx root-mcp --data-path /absolute/path/to/data
```

Check the extension's tools, then call `get_server_info`. Goose calls MCP
connections extensions; its YAML `extensions` map is separate from the portable
`mcpServers` JSON format. See the
[upstream extension guide](https://github.com/aaif-goose/goose/blob/main/documentation/docs/getting-started/using-extensions.md).

### Custom harnesses and SDKs

A harness does not need a ROOT-specific adapter: launch the stdio command or
connect to authenticated Streamable HTTP and expose the discovered tools.
For Python, [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/mcp/)
provides `MCPServerStdio` and `MCPServerStreamableHttp` connections.
[LangChain's current MCP integration](https://www.langchain.com/blog/mcp-in-langchain-stateless-protocol-elicitation-and-more)
provides MCP-backed tools for LangChain/LangGraph workflows. Check adapter and MCP
SDK version requirements independently of the ROOT-MCP server environment.
For shell-oriented harnesses, `root-cli` also provides the analysis backend
without an MCP adapter.

## Verify an integration

Check these separately: configuration parsed; server connected and tools listed;
`get_server_info` returned a real tool result; an analysis call read a known
sample. Successful installation, a green icon or an assistant's prose alone does
not prove all four. Use a bounded read on synthetic data before a large dataset.
A client may expose only tools even when the server also provides resources;
`get_server_info` supplies resource names for that case.

## Connecting to a central server

Deploy the server with `root-mcp serve-http --config /absolute/path/to/central.yaml`.
See [central deployment](https://github.com/MohamedElashri/root-mcp/blob/main/docs/operator/central_deployment.md) for authentication,
resource ACLs, export permissions and proxy configuration.

ROOT-MCP requires an allowed `Origin` header even for non-browser clients. Use the
origin supplied by the operator, along with a token valid for that deployment.
A remote Codex configuration can read a bearer token from the environment:

```toml
[mcp_servers.root-central]
url = "https://analysis.example.org/mcp"
bearer_token_env_var = "ROOT_MCP_TOKEN"
http_headers = { Origin = "https://client.example" }
tool_timeout_sec = 120
```

For Claude Code, a project `.mcp.json` entry can expand an environment variable:

```json
{
  "mcpServers": {
    "root-central": {
      "type": "http",
      "url": "https://analysis.example.org/mcp",
      "headers": {
        "Origin": "https://client.example",
        "Authorization": "Bearer ${ROOT_MCP_TOKEN}"
      }
    }
  }
}
```

Export `ROOT_MCP_TOKEN` before starting the client. Keep credentials out of
committed configuration. ROOT-MCP validates externally issued tokens or trusted
proxy identities; it does not currently provide OAuth discovery, registration or
an interactive login flow. `codex mcp login` is therefore not an authentication
setup step for this server. An external gateway can provide OAuth separately.

## Analysis workflow

1. Call `get_server_info` for the analysis mode, accessible resource names and
   effective row limits. MCP resources also expose readable JSON catalog descriptors.
2. Call `list_files(resource="data", pattern="*sample*", limit=20)` and reuse a
   returned file path. Central paths have the form `@data/sample.root`.
3. Call `inspect_file(path="@data/sample.root")`, then
   `list_branches(path="@data/sample.root", tree_name="events")` to verify names.
4. Sample explicit branches with `read_branches`, for example:

   ```json
   {
     "path": "@data/sample.root",
     "tree_name": "events",
     "branches": ["pt", "eta"],
     "entry_start": 0,
     "entry_stop": 100
   }
   ```

5. Prefer `get_branch_stats`, `compute_histogram` and `fit_histogram` over large
   raw arrays. Extended analysis tools appear only when that tier is available.
6. Use `export_data` or plotting tools when a file is requested. Supply an explicit
   output path; central deployments require an artifact-relative path and export
   permission. Existing outputs may be overwritten.

`read_branches` also supports `limit`/`offset`, `defines` for derived branches and
`flatten` for jagged arrays. Flattening removes event boundaries. Check physics
units and selection semantics before interpreting results. Use `tree_name` as
the argument name, and consult `tools/list` for each operation's complete schema.

Both structured results and JSON text are returned. Input validation failures
have `isError: true` and actionable constraint information; correct the arguments
before retrying. Unknown/unavailable tools use JSON-RPC invalid-params errors.
After an ambiguous timeout, inspect outputs before retrying a write or native
execution. Native tools run code outside the client's own shell sandbox;
server configuration controls their availability.

## Protocol and feature support

ROOT-MCP requires Python MCP SDK 2.3 or later within the 2.x line and serves the
[2026-07-28 MCP revision](https://modelcontextprotocol.io/specification/2026-07-28/changelog).
Modern requests are stateless: they carry protocol metadata on every request and
need no initialization handshake or `Mcp-Session-Id`. `server/discover` provides
identity, instructions and capabilities. The SDK retains compatibility with older
clients that initialize and use legacy HTTP sessions.

The SDK handles version negotiation, routing headers and wire serialization.
Tool and resource catalogs use private caching with zero freshness because mode,
policy and caller access can change. Catalogs are deterministic for the same
configuration and authorization context. Resource descriptors contain catalog
metadata, not binary ROOT contents or physical storage URIs.

ROOT-MCP does not advertise tasks, sampling, elicitation, prompts, MCP Apps or
change subscriptions. They are optional capabilities, and server-side task
support is still pending in the [Python SDK roadmap](https://github.com/modelcontextprotocol/python-sdk/blob/main/ROADMAP.md).
Client backgrounding does not turn an ordinary ROOT-MCP call into a resumable
server task. Central timeouts do not guarantee that a running worker thread has
stopped; choose bounded operations and avoid automatic write retries.

For agents with shell access, `root-cli` shares the analysis backend and can
return compact text without an MCP connection. Choose the interface supported by
your environment. Neither MCP annotations nor client approvals replace the
server's path validation, policy checks or resource permissions.

Run `root-mcp --help` for configuration flags and see the
[tools reference](https://github.com/MohamedElashri/root-mcp/blob/main/docs/user/tools_reference.rst) for analysis operations.
