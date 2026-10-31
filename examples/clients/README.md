# Client configurations

These templates connect a client to local ROOT-MCP over stdio. Replace
`/absolute/path/to/data`, then merge the server definition into the destination.
Retain unrelated settings and credentials. Do not put every template into the
same project: some harnesses import other clients' configuration automatically.

| Template | Destination | Client reference |
|---|---|---|
| [vscode.json](vscode.json) | `.vscode/mcp.json` for the Local harness | [VS Code](https://code.visualstudio.com/docs/agents/reference/mcp-configuration) |
| [copilot.json](copilot.json) | Trusted workspace `.mcp.json` or `~/.copilot/mcp-config.json` | [Copilot CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-mcp-servers) |
| [cursor.json](cursor.json) | `.cursor/mcp.json` or `~/.cursor/mcp.json` | [Cursor](https://prod.cursor.com/docs/mcp) |
| [zed.json](zed.json) | Merge into the settings opened by `zed: open settings file` | [Zed](https://zed.dev/docs/ai/mcp) |
| [antigravity.json](antigravity.json) | `.agents/mcp_config.json` or `~/.gemini/config/mcp_config.json` | [Antigravity app, IDE and CLI](https://antigravity.google/docs/mcp) |
| [claude.json](claude.json) | `.mcp.json` or the MCP configuration opened by Claude Desktop | [Claude Code](https://code.claude.com/docs/en/mcp) |
| [codex.toml](codex.toml) | Trusted project `.codex/config.toml` or `~/.codex/config.toml` | [Codex](https://learn.chatgpt.com/docs/extend/mcp) |
| [qwen.json](qwen.json) | `.qwen/settings.json` or `~/.qwen/settings.json` | [Qwen Code](https://qwenlm.github.io/qwen-code-docs/en/users/features/mcp/) |
| [pi.json](pi.json) | Trusted project `.pi/mcp.json` or `~/.pi/agent/mcp.json` | [Pi](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/mcp.md) |
| [omp.json](omp.json) | `.omp/mcp.json` or `~/.omp/agent/mcp.json` | [Oh My Pi](https://github.com/can1357/oh-my-pi/blob/main/docs/mcp-config.md) |
| [opencode-v2.json](opencode-v2.json) | `opencode.json` or `opencode.jsonc` | [OpenCode v2](https://dev.opencode.ai/v2/docs/mcp-servers/) |
| [cline.json](cline.json) | Cline → MCP Servers → Configure MCP Servers | [Cline](https://github.com/cline/cline/blob/main/docs/mcp/mcp-overview.mdx) |
| [roo.json](roo.json) | `.roo/mcp.json` | [Roo Code](https://roocodeinc.github.io/Roo-Code/features/mcp/using-mcp-in-roo/) |
| [continue.yaml](continue.yaml) | Merge into the active Continue YAML configuration | [Continue](https://docs.continue.dev/reference) |

For a checkout, use `uv` as `command` and
`["run", "--directory", "/absolute/path/to/root-mcp", "root-mcp", "--data-path", "/absolute/path/to/data"]`
as `args`. OpenCode's `command` combines the executable and arguments into one
array. Install the checkout dependencies before connecting a client.

The [integration guide](../../docs/guides/llm_integration.md) explains setup,
authenticated HTTP and workflow details. Client features and configuration can
vary by release; check the linked upstream documentation for your installation.
