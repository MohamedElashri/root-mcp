# Mode Selection Guide

## Overview

ROOT-MCP operates in two modes that balance simplicity and functionality. The mode is controlled through your `config.yaml` file and can be switched at runtime without restarting the server.

## Modes Explained

### Core Mode

**Purpose**: Lightweight file operations and basic data analysis

**When to Use**:
- File inspection and exploration
- Reading branch data
- Basic statistics (min, max, mean, std, median)
- Data export to JSON/CSV/Parquet
- Simple histogram creation (no fitting)
- When you want minimal resource usage

**Available Tools**:
- `list_files` - Browse ROOT files
- `inspect_file` - View file structure
- `list_branches` - List TTree branches
- `validate_file` - Check file integrity
- `read_branches` - Read branch data
- `get_branch_stats` - Compute statistics
- `export_data` - Export to standard formats
- `switch_mode` - Change modes
- `get_server_info` - Check capabilities

**Dependencies**: uproot, awkward, numpy, pandas, mcp

### Extended Mode

**Purpose**: Full physics analysis capabilities

**When to Use**:
- Histogram fitting with various models
- Particle physics kinematics calculations
- Statistical correlation analysis
- Plot generation
- Advanced 2D histograms and profiles
- Complete physics analysis workflows

**Additional Tools** (beyond core):
- `compute_histogram` - 1D histograms with fitting support
- `compute_histogram_2d` - 2D histograms
- `fit_histogram` - Model fitting (Gaussian, exponential, Crystal Ball, etc.)
- `compute_invariant_mass` - 4-vector calculations
- `compute_correlation` - Pearson/Spearman correlations
- `histogram_arithmetic` - Histogram arithmetic operations
- `plot_histogram_1d` - 1D plot generation
- `plot_histogram_2d` - 2D plot generation

**Dependencies**: Core + scipy, matplotlib

## Configuration

### Setting the Mode

Edit your `config.yaml`:

```yaml
server:
  name: "root-mcp"
  mode: "extended"  # or "core"
```

### Mode-Specific Configuration

```yaml
# Core configuration (always used)
core:
  cache:
    enabled: true
    file_cache_size: 50  # Number of open file handles to cache
  limits:
    max_rows_per_call: 1_000_000
    max_export_rows: 10_000_000

# Extended configuration (only used in extended mode)
extended:
  histogram:
    max_bins_1d: 10_000
    max_bins_2d: 1_000  # Per dimension
  plotting:
    figure_width: 10.0
    figure_height: 6.0
    dpi: 100
    default_format: "png"
  fitting_max_iterations: 10_000
```

## Runtime Mode Switching

You can switch modes without restarting the server using the `switch_mode` tool.

### Example: Switch to Extended Mode

```json
{
  "tool": "switch_mode",
  "arguments": {
    "mode": "extended"
  }
}
```

**Response**:
```json
{
  "status": "success",
  "previous_mode": "core",
  "current_mode": "extended",
  "message": "Switched from core to extended mode",
  "extended_features_available": true
}
```

### Example: Switch to Core Mode

```json
{
  "tool": "switch_mode",
  "arguments": {
    "mode": "core"
  }
}
```

**Response**:
```json
{
  "status": "success",
  "previous_mode": "extended",
  "current_mode": "core",
  "message": "Switched from extended to core mode",
  "extended_features_available": false
}
```

### Checking Current Mode

```json
{
  "tool": "get_server_info",
  "arguments": {}
}
```

**Response**:
```json
{
  "server_name": "root-mcp",
  "version": "0.1.4",
  "current_mode": "extended",
  "extended_components_loaded": true,
  "available_modes": ["core", "extended"]
}
```

## Mode Behavior

### Component Loading

**Core Mode**:
- All core components loaded immediately
- Extended components not loaded (saves memory)
- Attempting to use extended tools returns helpful error

**Extended Mode**:
- Core components loaded immediately
- Extended components lazy-loaded on first use
- If scipy/matplotlib unavailable, gracefully falls back to core mode

### Error Handling

If you try to use an extended tool in core mode:

```json
{
  "error": "mode_error",
  "message": "Tool 'fit_histogram' requires extended mode. Current mode: core",
  "hint": "Use switch_mode tool to enable extended mode"
}
```

### Graceful Degradation

If extended dependencies are missing when switching to extended mode:

```json
{
  "status": "error",
  "current_mode": "core",
  "message": "Failed to switch to extended mode: scipy not installed",
  "hint": "Install with: pip install 'root-mcp[extended]'"
}
```

## Use Case Examples

### Example 1: Quick File Inspection (Core Mode)

**Scenario**: You want to quickly check what's in a ROOT file.

**Configuration**:
```yaml
server:
  mode: "core"
```

**Workflow**:
1. `inspect_file` - See file structure
2. `list_branches` - List available branches
3. `read_branches` - Read some data
4. `get_branch_stats` - Get basic statistics

**Benefits**: Fast startup, minimal memory usage

### Example 2: Physics Analysis (Extended Mode)

**Scenario**: You need to fit a mass peak and compute kinematics.

**Configuration**:
```yaml
server:
  mode: "extended"
```

**Workflow**:
1. `read_branches` - Read pt, eta, phi, mass
2. `compute_invariant_mass` - Calculate invariant mass
3. `compute_histogram` - Create mass histogram
4. `fit_histogram` - Fit Gaussian to peak
5. `plot_histogram_1d` - Create visualization

**Benefits**: Full analysis capabilities available

### Example 3: Adaptive Workflow (Runtime Switching)

**Scenario**: Start with exploration, then do detailed analysis.

**Initial Configuration**:
```yaml
server:
  mode: "core"
```

**Workflow**:
1. Start in core mode for exploration
2. `inspect_file`, `list_branches` - Explore data
3. `switch_mode` to extended when ready for analysis
4. `fit_histogram`, `compute_correlation` - Detailed analysis
5. `switch_mode` back to core to free memory

**Benefits**: Optimal resource usage throughout workflow

## Performance Considerations

### Memory Usage

**Core Mode**:
- Minimal memory footprint
- Only file handles and basic operations in memory
- Suitable for resource-constrained environments

**Extended Mode**:
- Additional memory for scipy/matplotlib
- Analysis results cached when appropriate
- Can be unloaded by switching to core mode

### Startup Time

**Core Mode**:
- Fast initialization (~1 second)
- No scipy/matplotlib import overhead

**Extended Mode**:
- Slightly slower initialization (~2-3 seconds)
- Extended components lazy-loaded on first use
- Subsequent operations are fast

### Switching Overhead

- Core → Extended: ~1-2 seconds (load scipy/matplotlib)
- Extended → Core: Immediate (unload components)
- No server restart required

## Best Practices

### 1. Start with Core Mode

Begin in core mode for exploration, then switch to extended when needed:

```yaml
server:
  mode: "core"
```

### 2. Use Extended for Analysis

If you know you'll need analysis features, start in extended mode:

```yaml
server:
  mode: "extended"
```

### 3. Switch Modes Strategically

Use `switch_mode` to optimize resource usage:
- Core mode for browsing and reading
- Extended mode for analysis
- Back to core when done

### 4. Check Server Info

Before complex operations, verify mode and capabilities:

```json
{
  "tool": "get_server_info",
  "arguments": {}
}
```

### 5. Handle Mode Errors Gracefully

If a tool fails due to mode mismatch, switch modes and retry:

```
1. Try extended tool
2. If mode_error, call switch_mode
3. Retry the tool
```

## Troubleshooting

### Extended Mode Not Available

**Problem**: Cannot switch to extended mode

**Cause**: scipy or matplotlib not installed

**Solution**:
```bash
pip install scipy matplotlib
# or reinstall root-mcp to ensure all dependencies
pip install --upgrade --force-reinstall root-mcp
```

### Mode Switch Fails

**Problem**: `switch_mode` returns error

**Possible Causes**:
1. Invalid mode name (must be "core" or "extended")
2. Missing dependencies for extended mode
3. Server initialization issue

**Solution**:
- Check mode name spelling
- Verify dependencies installed
- Check server logs for details

### Tools Not Available

**Problem**: Tool returns "unknown tool" error

**Cause**: Tool only available in extended mode

**Solution**:
1. Check current mode with `get_server_info`
2. Switch to extended mode with `switch_mode`
3. Retry the tool

## Summary

| Aspect | Core Mode | Extended Mode |
|--------|-----------|---------------|
| **Purpose** | File I/O & basic stats | Full physics analysis |
| **Dependencies** | Minimal | + scipy, matplotlib |
| **Memory** | Low | Moderate |
| **Startup** | Fast (~1s) | Moderate (~2-3s) |
| **Tools** | 9 core tools | Core + 8 extended tools |
| **Use Case** | Exploration, reading | Analysis, fitting, plotting |
| **Switching** | To extended: ~2s | To core: immediate |

Choose the mode that fits your workflow, and remember you can always switch at runtime!
