# LLM Integration Guide

`ROOT-MCP` is designed primarily to give LLMs like Claude and Gemini Models through clients capabilities to interact with HEP data. This guide explains how to effectively use `ROOT-MCP` in an agentic workflow.

## Prerequisites

ROOT-MCP is typically installed and run using `uvx` (the recommended method). Before configuring any client:

1. **Install uvx** (if not already installed):
   ```bash
   # macOS (Homebrew)
   brew install uv

   # Or using pip
   pip install uv
   ```

2. **Find your uvx path** (important for macOS):
   ```bash
   which uvx
   ```
   Common locations:
   - **macOS (Apple Silicon)**: `/opt/homebrew/bin/uvx`
   - **macOS (Intel)**: `/usr/local/bin/uvx`
   - **Linux**: `/usr/local/bin/uvx` or `~/.local/bin/uvx`
   - **Windows**: `uvx` (typically in PATH, or find with `where uvx`)

3. **Use full paths in configurations**:
   - **macOS/Linux**: Always use the full path (e.g., `/opt/homebrew/bin/uvx`) instead of `~` or relative paths
   - **Windows**: You can typically use `uvx` directly if it's in your PATH

## Setup with Different LLM Clients

### Claude Code

Claude Code (available at [claude.ai/code](https://claude.ai/code)) provides both automatic MCP server installation and manual configuration options.

#### Automatic Installation (Recommended)

The easiest way to set up ROOT-MCP with Claude Code is using the built-in `claude mcp add` command:

```bash
# Basic setup with data path
claude mcp add root-mcp --data-path /path/to/your/data

# With native ROOT support
claude mcp add root-mcp --data-path /path/to/your/data --enable-root

# With additional configuration
claude mcp add root-mcp \
  --data-path /data/cms \
  --mode extended \
  --enable-root \
  --allowed-root /data/cms \
  --export-path /tmp/exports \
  --log-level WARNING
```

This command automatically installs ROOT-MCP and updates your Claude Code configuration.

**Note:** The `claude mcp add` command typically configures `uvx` to run root-mcp, which is the recommended approach.

#### Manual Configuration (User Scope - All Projects)

To configure ROOT-MCP globally for all Claude Code projects, edit the user-scope config file.

**macOS/Linux:** `/Users/username/.config/claude-code/mcp_config.json` (use full path, not `~`)

**Find the correct uvx path:**
```bash
which uvx  # On macOS, typically /opt/homebrew/bin/uvx or /usr/local/bin/uvx
```

**Configuration:**
```json
{
  "mcpServers": {
    "root-mcp": {
      "command": "uvx",
      "args": ["root-mcp", "--data-path", "/path/to/your/data"]
    }
  }
}
```

**With explicit uvx path (MUST be used for macOS):**
```json
{
  "mcpServers": {
    "root-mcp": {
      "command": "/opt/homebrew/bin/uvx",
      "args": ["root-mcp", "--data-path", "/path/to/your/data"]
    }
  }
}
```

**Extended configuration with additional arguments:**

```json
{
  "mcpServers": {
    "root-mcp": {
      "command": "/opt/homebrew/bin/uvx",
      "args": [
        "root-mcp",
        "--data-path", "/data/cms",
        "--mode", "extended",
        "--enable-root",
        "--allowed-root", "/data/cms",
        "--export-path", "/tmp/exports",
        "--root-timeout", "120",
        "--max-rows", "2000000",
        "--max-bins-1d", "5000",
        "--plot-dpi", "150",
        "--log-level", "WARNING"
      ]
    }
  }
}
```

**Using environment variables:**

```json
{
  "mcpServers": {
    "root-mcp": {
      "command": "/opt/homebrew/bin/uvx",
      "args": ["root-mcp"],
      "env": {
        "ROOT_MCP_DATA_PATH": "/path/to/your/data",
        "ROOT_MCP_MODE": "extended",
        "ROOT_MCP_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

#### Manual Configuration (Project Scope)

To configure ROOT-MCP for a specific project only, create `.claude/mcp_config.json` in your project root:

```json
{
  "mcpServers": {
    "root-mcp": {
      "command": "uvx",
      "args": [
        "root-mcp",
        "--data-path", ".",
        "--export-path", "./exports"
      ]
    }
  }
}
```

**With full path (recommended for macOS):**
```json
{
  "mcpServers": {
    "root-mcp": {
      "command": "/opt/homebrew/bin/uvx",
      "args": [
        "root-mcp",
        "--data-path", ".",
        "--export-path", "./exports"
      ]
    }
  }
}
```

Project-scope configuration takes precedence over user-scope configuration.

### Claude Desktop

Add to your Claude Desktop configuration file:
- **macOS**: `/Users/username/Library/Application Support/Claude/claude_desktop_config.json` (use full path)
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `/home/username/.config/Claude/claude_desktop_config.json` (use full path)

**Find the correct uvx path first:**
```bash
# macOS/Linux
which uvx  # On macOS with Homebrew: typically /opt/homebrew/bin/uvx

# Windows (PowerShell)
where.exe uvx
```

#### Quickest setup — no config file needed

Pass `--data-path` directly so Claude can access your data with zero additional setup:

**macOS/Linux:**
```json
{
  "mcpServers": {
    "root-mcp": {
      "command": "uvx",
      "args": ["root-mcp", "--data-path", "/path/to/your/data"]
    }
  }
}
```

**Windows:**
```json
{
  "mcpServers": {
    "root-mcp": {
      "command": "uvx",
      "args": ["root-mcp", "--data-path", "C:\\path\\to\\your\\data"]
    }
  }
}
```

**With explicit path (MUST be used for macOS):**
```json
{
  "mcpServers": {
    "root-mcp": {
      "command": "/opt/homebrew/bin/uvx",
      "args": ["root-mcp", "--data-path", "/path/to/your/data"]
    }
  }
}
```

Or use an environment variable instead of a command-line flag:

```json
{
  "mcpServers": {
    "root-mcp": {
      "command": "/opt/homebrew/bin/uvx",
      "args": ["root-mcp"],
      "env": {
        "ROOT_MCP_DATA_PATH": "/path/to/your/data"
      }
    }
  }
}
```

#### Extended setup — no YAML file required

All `config.yaml` fields are available as CLI flags or env vars, so you can fully configure
the server from the JSON block without writing any additional files:

```json
{
  "mcpServers": {
    "root-mcp": {
      "command": "/opt/homebrew/bin/uvx",
      "args": [
        "root-mcp",
        "--data-path", "/data/cms",
        "--mode", "extended",
        "--enable-root",
        "--allowed-root", "/data/cms",
        "--export-path", "/tmp/exports",
        "--root-timeout", "120",
        "--max-rows", "2000000",
        "--max-bins-1d", "5000",
        "--cache-size", "100",
        "--plot-dpi", "150",
        "--plot-format", "png",
        "--log-level", "WARNING"
      ]
    }
  }
}
```

**With environment variables for cleaner config:**

```json
{
  "mcpServers": {
    "root-mcp": {
      "command": "/opt/homebrew/bin/uvx",
      "args": ["root-mcp", "--enable-root"],
      "env": {
        "ROOT_MCP_DATA_PATH": "/data/cms",
        "ROOT_MCP_MODE": "extended",
        "ROOT_MCP_ALLOWED_ROOTS": "/data/cms:/data/run3",
        "ROOT_MCP_EXPORT_PATH": "/tmp/exports",
        "ROOT_MCP_ROOT_TIMEOUT": "120",
        "ROOT_MCP_MAX_ROWS": "2000000",
        "ROOT_MCP_LOG_LEVEL": "WARNING"
      }
    }
  }
}
```

With a remote XRootD resource:

```json
{
  "mcpServers": {
    "root-mcp": {
      "command": "/opt/homebrew/bin/uvx",
      "args": [
        "root-mcp",
        "--resource", "cms=root://xrootd.cern.ch//store/data|CMS open data",
        "--allow-remote",
        "--mode", "extended",
        "--max-rows", "1000000",
        "--export-path", "/tmp/cms_exports"
      ]
    }
  }
}
```

#### Persistent config file (optional)

For more control (remote resources, custom limits, native ROOT), generate a config file first:

```bash
uvx root-mcp init --permissive   # creates config.yaml pre-filled with your cwd
```

Then reference it:

```json
{
  "mcpServers": {
    "root-mcp": {
      "command": "/opt/homebrew/bin/uvx",
      "args": ["root-mcp"],
      "env": {
        "ROOT_MCP_CONFIG": "/path/to/config.yaml"
      }
    }
  }
}
```

### Gemini CLI

Gemini CLI supports MCP servers through settings files. You can configure ROOT-MCP either globally or per-project.

**Find the correct uvx path first:**
```bash
which uvx  # On macOS: typically /opt/homebrew/bin/uvx
```

#### Global Configuration (All Sessions)

Add to `/Users/username/.gemini/settings.json` (use full path, not `~`).

**Quickest setup — no config file needed:**

```json
{
  "mcpServers": {
    "root-mcp": {
      "command": "uvx",
      "args": ["root-mcp", "--data-path", "/path/to/your/data"]
    }
  }
}
```

**With explicit path (recommended for macOS):**
```json
{
  "mcpServers": {
    "root-mcp": {
      "command": "/opt/homebrew/bin/uvx",
      "args": ["root-mcp", "--data-path", "/path/to/your/data"]
    }
  }
}
```

Or use an environment variable:

```json
{
  "mcpServers": {
    "root-mcp": {
      "command": "/opt/homebrew/bin/uvx",
      "args": ["root-mcp"],
      "env": {
        "ROOT_MCP_DATA_PATH": "/path/to/your/data"
      }
    }
  }
}
```

**With a persistent config file:**

```json
{
  "mcpServers": {
    "root-mcp": {
      "command": "/opt/homebrew/bin/uvx",
      "args": ["root-mcp"],
      "env": {
        "ROOT_MCP_CONFIG": "/path/to/your/config.yaml"
      }
    }
  }
}
```

**Extended setup — no YAML file required:**

```json
{
  "mcpServers": {
    "root-mcp": {
      "command": "/opt/homebrew/bin/uvx",
      "args": [
        "root-mcp",
        "--data-path", "/data",
        "--mode", "extended",
        "--allowed-root", "/data",
        "--export-path", "/tmp/exports",
        "--max-rows", "1500000",
        "--max-bins-1d", "8000",
        "--plot-width", "12.0",
        "--plot-height", "8.0",
        "--cache-size", "75",
        "--log-level", "WARNING"
      ]
    }
  }
}
```

**Using environment variables:**

```json
{
  "mcpServers": {
    "root-mcp": {
      "command": "/opt/homebrew/bin/uvx",
      "args": ["root-mcp"],
      "env": {
        "ROOT_MCP_DATA_PATH": "/data",
        "ROOT_MCP_MODE": "extended",
        "ROOT_MCP_ALLOWED_ROOTS": "/data",
        "ROOT_MCP_EXPORT_PATH": "/tmp/exports",
        "ROOT_MCP_MAX_ROWS": "1500000",
        "ROOT_MCP_CACHE_SIZE": "75",
        "ROOT_MCP_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

This makes ROOT-MCP available in every Gemini CLI session.

#### Project-Specific Configuration

Add to `/path/to/your/project/.gemini/settings.json`:

```json
{
  "mcpServers": {
    "root-mcp": {
      "command": "root-mcp",
      "args": [
        "--data-path", ".",
        "--export-path", "./exports"
      ]
    }
  }
}
```

**With additional arguments for project-specific tuning:**

```json
{
  "mcpServers": {
    "root-mcp": {
      "command": "/opt/homebrew/bin/uvx",
      "args": [
        "root-mcp",
        "--data-path", ".",
        "--mode", "extended",
        "--export-path", "./exports",
        "--max-rows", "500000",
        "--plot-format", "pdf"
      ],
      "env": {
        "ROOT_MCP_DATA_PATH": "."
      }
    }
  }
}
```

This makes ROOT-MCP available only in Gemini CLI sessions created under that project folder.

**Recommended Configuration (Virtual Environment):**

For production use, we recommend explicitly specifying all paths for better control and debugging.

**Option 1: Using uvx (Recommended):**

```json
{
  "mcpServers": {
    "root-mcp": {
      "command": "/opt/homebrew/bin/uvx",
      "args": [
        "root-mcp",
        "--data-path",
        "/path/to/data"
      ]
    }
  }
}
```

**Option 2: Using virtual environment's Python directly:**

```json
{
  "mcpServers": {
    "root-mcp": {
      "command": "/path/to/venv/bin/python",
      "args": [
        "-m",
        "root_mcp.server",
        "--data-path",
        "/path/to/data"
      ]
    }
  }
}
```

**With additional arguments for production:**

**Using uvx:**
```json
{
  "mcpServers": {
    "root-mcp": {
      "command": "/opt/homebrew/bin/uvx",
      "args": [
        "root-mcp",
        "--data-path", "/path/to/data",
        "--mode", "extended",
        "--allowed-root", "/path/to/data",
        "--max-rows", "2000000",
        "--max-export-rows", "5000000",
        "--cache-size", "100",
        "--export-path", "/var/exports/root_mcp",
        "--plot-dpi", "200",
        "--log-level", "INFO"
      ]
    }
  }
}
```

**Using venv Python:**
```json
{
  "mcpServers": {
    "root-mcp": {
      "command": "/path/to/venv/bin/python",
      "args": [
        "-m",
        "root_mcp.server",
        "--data-path", "/path/to/data",
        "--mode", "extended",
        "--allowed-root", "/path/to/data",
        "--max-rows", "2000000",
        "--max-export-rows", "5000000",
        "--cache-size", "100",
        "--export-path", "/var/exports/root_mcp",
        "--plot-dpi", "200",
        "--log-level", "INFO"
      ]
    }
  }
}
```

This format:
- Uses `uvx` to automatically manage the root-mcp installation (Option 1)
- Or uses the virtual environment's Python interpreter explicitly (Option 2)
- Passes the data path as a command-line argument (no config file required)
- Makes debugging easier by showing all paths clearly

**With a persistent config file:**

```json
{
  "mcpServers": {
    "root-mcp": {
      "command": "/opt/homebrew/bin/uvx",
      "args": ["root-mcp"],
      "env": {
        "ROOT_MCP_CONFIG": "/path/to/config.yaml"
      }
    }
  }
}
```

**Verification:**

After configuration, restart Gemini CLI and verify ROOT-MCP tools are available by asking:
```
What MCP tools are available?
```

---

## Configuration Arguments Reference

ROOT-MCP supports ~29 configuration arguments that can be passed via CLI flags or environment variables. These can be used in **any** client configuration to customize behavior without needing a `config.yaml` file.

### Core Arguments

| CLI Flag | Environment Variable | Description | Default |
|----------|---------------------|-------------|---------|
| `--data-path DIR` | `ROOT_MCP_DATA_PATH` | Local directory with ROOT files (can repeat) | None |
| `--mode MODE` | `ROOT_MCP_MODE` | Server mode: `core` or `extended` | `extended` |
| `--config PATH` | `ROOT_MCP_CONFIG` | Path to config.yaml file | Auto-detected |
| `--log-level LEVEL` | `ROOT_MCP_LOG_LEVEL` | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR` | `INFO` |

### Security & Access Control

| CLI Flag | Environment Variable | Description | Default |
|----------|---------------------|-------------|---------|
| `--allowed-root DIR` | `ROOT_MCP_ALLOWED_ROOTS` | Restrict access to directory (colon-separated for env) | Empty (permissive) |
| `--allow-remote` | `ROOT_MCP_ALLOW_REMOTE` | Allow remote (non-file://) URIs | `false` |
| `--allowed-protocols PROTOS` | `ROOT_MCP_ALLOWED_PROTOCOLS` | Comma-separated allowed protocols | `file` |
| `--max-path-depth N` | `ROOT_MCP_MAX_PATH_DEPTH` | Maximum directory depth | `10` |

### Data Limits

| CLI Flag | Environment Variable | Description | Default |
|----------|---------------------|-------------|---------|
| `--max-rows N` | `ROOT_MCP_MAX_ROWS` | Max rows per read call | `1000000` |
| `--max-export-rows N` | `ROOT_MCP_MAX_EXPORT_ROWS` | Max rows per export | `10000000` |

### Cache Settings

| CLI Flag | Environment Variable | Description | Default |
|----------|---------------------|-------------|---------|
| `--no-cache` | `ROOT_MCP_CACHE` | Disable file metadata cache | Enabled |
| `--cache-size N` | `ROOT_MCP_CACHE_SIZE` | Number of cached file entries | `50` |

### Export Settings

| CLI Flag | Environment Variable | Description | Default |
|----------|---------------------|-------------|---------|
| `--export-path DIR` | `ROOT_MCP_EXPORT_PATH` | Directory for exported files | `/tmp/root_mcp_output` |
| `--export-formats FMTS` | `ROOT_MCP_EXPORT_FORMATS` | Comma-separated allowed formats | `json,csv,parquet` |
| `--no-export` | `ROOT_MCP_ENABLE_EXPORT` | Disable export feature | Enabled |

### Histogram & Analysis

| CLI Flag | Environment Variable | Description | Default |
|----------|---------------------|-------------|---------|
| `--max-bins-1d N` | `ROOT_MCP_MAX_BINS_1D` | Max bins for 1D histograms | `10000` |
| `--max-bins-2d N` | `ROOT_MCP_MAX_BINS_2D` | Max bins for 2D histograms | `1000` |
| `--fitting-iterations N` | `ROOT_MCP_FITTING_ITERATIONS` | Max fitting iterations | `10000` |

### Plotting

| CLI Flag | Environment Variable | Description | Default |
|----------|---------------------|-------------|---------|
| `--plot-dpi N` | `ROOT_MCP_PLOT_DPI` | Plot resolution in DPI | `100` |
| `--plot-format FMT` | `ROOT_MCP_PLOT_FORMAT` | Default format: `png`, `pdf`, `svg` | `png` |
| `--plot-width N` | `ROOT_MCP_PLOT_WIDTH` | Figure width in inches | `10.0` |
| `--plot-height N` | `ROOT_MCP_PLOT_HEIGHT` | Figure height in inches | `6.0` |

### Native ROOT Execution

| CLI Flag | Environment Variable | Description | Default |
|----------|---------------------|-------------|---------|
| `--enable-root` | N/A | Enable native ROOT/PyROOT tools | `false` |
| `--root-timeout N` | `ROOT_MCP_ROOT_TIMEOUT` | Execution timeout in seconds | `60` |
| `--root-workdir DIR` | `ROOT_MCP_ROOT_WORKDIR` | Working directory for ROOT | `/tmp/root_mcp_native` |
| `--root-max-output N` | `ROOT_MCP_ROOT_MAX_OUTPUT` | Max output size in bytes | `10000000` |
| `--root-max-code N` | `ROOT_MCP_ROOT_MAX_CODE` | Max script length in chars | `100000` |

### Remote Resources

| CLI Flag | Environment Variable | Description | Default |
|----------|---------------------|-------------|---------|
| `--resource SPEC` | `ROOT_MCP_RESOURCES` | Named resource: `NAME=URI\|DESC` (semicolon-sep for env) | None |

### Usage Examples

**Important for macOS users:** Use the full path to `uvx` rather than relying on `~` or relative paths:
```bash
# Find your uvx path
which uvx
# Common locations:
# - Homebrew (Apple Silicon): /opt/homebrew/bin/uvx
# - Homebrew (Intel): /usr/local/bin/uvx
```

**Combining multiple arguments (CLI):**
```bash
uvx root-mcp \
  --data-path /data/cms \
  --mode extended \
  --enable-root \
  --max-rows 2000000 \
  --cache-size 100 \
  --plot-dpi 150 \
  --export-path /exports \
  --log-level WARNING
```

**Combining multiple arguments (JSON config):**
```json
{
  "mcpServers": {
    "root-mcp": {
      "command": "uvx",
      "args": [
        "root-mcp",
        "--data-path", "/data/cms",
        "--mode", "extended",
        "--enable-root",
        "--max-rows", "2000000",
        "--cache-size", "100",
        "--plot-dpi", "150",
        "--export-path", "/exports",
        "--log-level", "WARNING"
      ]
    }
  }
}
```

**Or with full path (macOS):**
```json
{
  "mcpServers": {
    "root-mcp": {
      "command": "/opt/homebrew/bin/uvx",
      "args": [
        "root-mcp",
        "--data-path", "/data/cms",
        "--mode", "extended",
        "--enable-root",
        "--max-rows", "2000000",
        "--cache-size", "100",
        "--plot-dpi", "150",
        "--export-path", "/exports",
        "--log-level", "WARNING"
      ]
    }
  }
}
```

**Using environment variables:**
```json
{
  "mcpServers": {
    "root-mcp": {
      "command": "/opt/homebrew/bin/uvx",
      "args": ["root-mcp", "--enable-root"],
      "env": {
        "ROOT_MCP_DATA_PATH": "/data/cms",
        "ROOT_MCP_MODE": "extended",
        "ROOT_MCP_MAX_ROWS": "2000000",
        "ROOT_MCP_CACHE_SIZE": "100",
        "ROOT_MCP_PLOT_DPI": "150",
        "ROOT_MCP_EXPORT_PATH": "/exports",
        "ROOT_MCP_LOG_LEVEL": "WARNING"
      }
    }
  }
}
```

### Configuration Priority

When the same setting is specified in multiple places, the priority (highest to lowest) is:

1. **CLI flags** (e.g., `--data-path`)
2. **Environment variables** (e.g., `ROOT_MCP_DATA_PATH`)
3. **config.yaml file**
4. **Built-in defaults**

This allows you to:
- Set global defaults in `config.yaml`
- Override per-session with environment variables
- Override per-invocation with CLI flags

---

## The Analyst Agent Pattern

When using `ROOT-MCP`, you should view the LLM not just as a text processor, but as an **Autonomous Research Assistant**.

The LLM helps you by:
1.  **Exploring** unknown datasets to understand their content.
2.  **Formulating** analysis strategies (e.g., "I need to check the muon pT distribution").
3.  **Executing** the analysis using tools (`compute_histogram`, `read_branches`).
4.  **Interpreting** the results (e.g., "The mean value is lower than expected").

### Recommended Workflow

We recommend encouraging the LLM to follow this iterative loop:

1.  **Discovery**: "What files do I have? What is inside them?" (`list_files` -> `inspect_file` -> `list_branches`)
2.  **Sampling**: "Let me see a few real events to understand the structure." (`read_branches` with `limit` parameter)
3.  **Prototyping**: "Let's try a simple cut and see if it works." (`read_branches` with `selection` parameter)
4.  **Analysis**: "Now let's compute the full histograms." (`compute_histogram`)
5.  **Export/Plot**: "Save the data or show me a plot." (`export_data`, `plot_histogram_1d`)

## System Prompting

If you are building a custom agent using `ROOT-MCP`, consider adding the following to your system prompt:

> You are an expert High Energy Physics analyst assistant. You have access to ROOT files via a set of tools.
> When asked to analyze data, always start by exploring the file structure to verify branch names and types.
> Use `read_branches` with a small `limit` to check the actual data values before writing complex selections.
> ROOT data often contains "jagged arrays" (variable-length lists per event). Remember that operations on jagged arrays in selections usually imply "ANY" semantics (e.g., `Muon_PT > 20` means "at least one muon has PT > 20").

## Example Conversation

Here is how a typical interaction looks:

**User**: "Can you check the MET distribution for the sample events file?"

**Agent (Thought)**: I need to find the file first, then check the tree name, and finally compute the histogram.

**Agent (Tool Call)**: `list_files(pattern="*sample_events*")`
**Result**: `Found: /data/sample_events.root`

**Agent (Tool Call)**: `inspect_file(path="/data/sample_events.root")`
**Result**: `Tree "events" found.`

**Agent (Tool Call)**: `list_branches(path="/data/sample_events.root", tree="events", pattern="*met*")`
**Result**: `Found branch "met" (float).`

**Agent (Tool Call)**: `compute_histogram(path="/data/sample_events.root", tree="events", branch="met", bins=50)`
**Result**: `{ "bin_counts": [...], "mean": 29.3, ... }`

**Agent (Response)**: "I found the file `sample_events.root`. The `events` tree contains a `met` branch. I computed the histogram, and the mean MET is approximately 29.3 GeV. The distribution looks exponentially falling as expected."

## Best Practices for Users

When chatting with Claude (or other LLMs) with `ROOT-MCP` enabled:

- **Be Specific about Files**: If you know the filename, mention it. "Look at `run2024.root`".
- **Ask for "Why"**: The LLM can explain *why* it chose a certain binning or selection if you ask.
- **Iterate**: If a selection fails (e.g., "Branch not found"), the LLM can self-correct. ask it to "Check the branch names again".

## Jagged Array Handling

One of the hardest parts for LLMs is understanding jagged arrays (e.g., multiple muons per event).

- **Tip**: Remind the LLM that `nmuon_pt` or `Muon_PT` is a list.
- **Selection Logic**: `Muon_PT > 50` selects events where *any* muon has pT > 50.
- **Flattening**: Use `read_branches(flatten=True)` if you want a flat list of all muons from all events, ignoring event boundaries.

## Advanced Analysis Examples

### Kinematics: Invariant Mass Calculation

The `compute_invariant_mass` tool calculates the invariant mass of particle systems from their four-momentum components ($p_T, \eta, \phi, m$). This is essential for reconstructing resonances (e.g., $Z \to \mu^+\mu^-$) and analyzing decay chains.

**Workflow Example**:

1.  **Calculate Mass**: Use `compute_invariant_mass` to calculate the physics quantity.
2.  **Visualize**: Use `compute_histogram` with the resulting mass data (or `plot_histogram_1d` if available) or export the data.

**Example Tool Call**:

```json
{
  "tool": "compute_invariant_mass",
  "arguments": {
    "path": "/data/drell_yan.root",
    "tree_name": "events",
    "pt_branches": ["mu1_pt", "mu2_pt"],
    "eta_branches": ["mu1_eta", "mu2_eta"],
    "phi_branches": ["mu1_phi", "mu2_phi"],
    "mass_branches": ["mu1_mass", "mu2_mass"],
    "selection": "mu1_pt > 20 && mu2_pt > 20"
  }
}
```

> **Note**: Currently, `compute_invariant_mass` returns the raw array of mass values. To plot this, you would typically follow up by asking the agent to "histogram the returned values".

### Common Issues in Kinematics

- **Unit Consistency**: Ensure all branches use the same units (typically GeV or MeV).
- **Branch Matching**: The order of branches in the lists matters. `pt_branches[0]` corresponds to `eta_branches[0]`.
- **Missing Energy**: This tool calculates visible mass. For neutrinos (transverse mass), explicit calculation using `defines` in `read_branches` is recommended.
