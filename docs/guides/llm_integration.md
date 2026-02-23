# LLM Integration Guide

`ROOT-MCP` is designed primarily to give LLMs like Claude and Gemini Models through clients capabilities to interact with HEP data. This guide explains how to effectively use `ROOT-MCP` in an agentic workflow.

## Setup with Different LLM Clients

### Claude Desktop

Add to your Claude Desktop configuration file (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS).

#### Quickest setup — no config file needed

Pass `--data-path` directly so Claude can access your data with zero additional setup:

```json
{
  "mcpServers": {
    "root-mcp": {
      "command": "root-mcp",
      "args": ["--data-path", "/path/to/your/data"]
    }
  }
}
```

Or use an environment variable instead of a command-line flag:

```json
{
  "mcpServers": {
    "root-mcp": {
      "command": "root-mcp",
      "env": {
        "ROOT_MCP_DATA_PATH": "/path/to/your/data"
      }
    }
  }
}
```

#### Persistent config file (optional)

For more control (remote resources, custom limits, native ROOT), generate a config file first:

```bash
root-mcp init --permissive   # creates config.yaml pre-filled with your cwd
```

Then reference it:

```json
{
  "mcpServers": {
    "root-mcp": {
      "command": "root-mcp",
      "env": {
        "ROOT_MCP_CONFIG": "/path/to/config.yaml"
      }
    }
  }
}
```

### Gemini CLI

Gemini CLI supports MCP servers through settings files. You can configure ROOT-MCP either globally or per-project.

#### Global Configuration (All Sessions)

Add to `~/.gemini/settings.json`.

**Quickest setup — no config file needed:**

```json
{
  "mcpServers": {
    "root-mcp": {
      "command": "root-mcp",
      "args": ["--data-path", "/path/to/your/data"]
    }
  }
}
```

Or use an environment variable:

```json
{
  "mcpServers": {
    "root-mcp": {
      "command": "root-mcp",
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
      "command": "root-mcp",
      "env": {
        "ROOT_MCP_CONFIG": "/path/to/your/config.yaml"
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
      "args": ["--data-path", "."],
      "env": {
        "ROOT_MCP_DATA_PATH": "."
      }
    }
  }
}
```

This makes ROOT-MCP available only in Gemini CLI sessions created under that project folder.

**Recommended Configuration (Virtual Environment):**

For production use, we recommend explicitly specifying all paths for better control and debugging:

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

This format:
- Uses the virtual environment's Python interpreter explicitly
- Passes the data path as a command-line argument (no config file required)
- Makes debugging easier by showing all paths clearly

**With a persistent config file:**

```json
{
  "mcpServers": {
    "root-mcp": {
      "command": "/path/to/venv/bin/python",
      "args": ["-m", "root_mcp.server"],
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
