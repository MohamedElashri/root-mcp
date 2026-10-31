# Tool Reference

This reference describes the MCP tool schemas shipped in ROOT-MCP **0.3.1**.
There are nine core tools, eight additional extended tools and three optional
native ROOT tools. Deployment policy can hide or deny any tool; central services
disable `switch_mode` and native code execution. Use `tools/list` for the catalog
available to your connection and `get_server_info` for resources and limits.

## Calls and results

The following is a complete JSON-RPC tool request (transport metadata is omitted):

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "read_branches",
    "arguments": {
      "path": "@data/sample.root",
      "tree_name": "events",
      "branches": ["pt"],
      "entry_start": 0,
      "entry_stop": 100
    }
  }
}
```

Clients supply protocol metadata and HTTP routing headers through their MCP SDK.
For 2026-07-28 requests, every call carries its protocol version; no handshake or
session ID is required. The SDK also serves older clients using initialization.

Tool results contain the same payload in `structuredContent` and a JSON text
content block. Most analysis payloads have `data`, `metadata` and `suggestions`;
management tools and native execution have their own result fields. Failures
carry `isError: true` with an `error` code and actionable details. Invalid tool
arguments are rejected before execution. Unknown or unavailable tool names
produce JSON-RPC invalid-params errors. Omit optional arguments you do not need;
unknown arguments are rejected, and `null` is not accepted unless listed in the
schema. A JSON object argument is an object, not a JSON-encoded string.

Use the `resource` names returned by `get_server_info` with `list_files`, then
reuse returned paths. Central paths use `@resource/relative.root`; physical
server paths are not exposed. `resources/list` and `resources/read` expose
ACL-filtered JSON catalog descriptors, not binary ROOT data.

Statistics and histograms keep output smaller than raw reads. `read_branches`
supports either `limit`/`offset` or `entry_start`/`entry_stop`; stop is exclusive
and must be greater than start. `flatten` removes event boundaries from jagged
arrays. Check units and branch types before combining physics quantities.

Exports and plots write files and can overwrite outputs. Central deployments
require artifact-relative output paths and export permissions. Native tools run
code in a local subprocess and are reserved for trusted local use; they are not
an operating-system security sandbox. Do not automatically retry writes or
native execution after an ambiguous timeout.

## Core tools

### `list_files`

List CERN ROOT files in a configured named resource. Use pattern and limit to bound discovery; inspect a returned path next. Does not modify files.

| Argument | Type | Required | Details |
|---|---|---|---|
| `resource` | string | Yes | Resource name |
| `pattern` | string | No | Optional glob pattern |
| `limit` | integer | No | Default: `100` Minimum: `1` Maximum: `1000` |

### `inspect_file`

Inspect a ROOT file's directories, TTrees, RNTuples and histograms before reading data. Accepts a returned path or @resource/relative.root reference. Does not modify files.

| Argument | Type | Required | Details |
|---|---|---|---|
| `path` | string | Yes | File path |

### `list_branches`

List branch names and types in a ROOT TTree or RNTuple. Use before selecting branches for reads, statistics or histograms. Does not modify files.

| Argument | Type | Required | Details |
|---|---|---|---|
| `path` | string | Yes | File path |
| `tree_name` | string | Yes | Tree name |
| `pattern` | string | No | Optional glob pattern |

### `validate_file`

Validate ROOT file integrity

| Argument | Type | Required | Details |
|---|---|---|---|
| `path` | string | Yes | File path |

### `read_branches`

Read selected branches from a ROOT TTree or RNTuple, optionally with a cut expression. Set entry_start/entry_stop to bound rows; prefer get_branch_stats or histograms for large datasets. Does not modify files.

| Argument | Type | Required | Details |
|---|---|---|---|
| `path` | string | Yes | File path |
| `tree_name` | string | Yes | Tree name |
| `branches` | array of string | Yes | Minimum items: `1` |
| `entry_start` | integer | No | Start entry Minimum: `0` |
| `entry_stop` | integer | No | Exclusive stop entry Minimum: `1` |
| `limit` | integer | No | Maximum rows to return (alternative to entry_stop) Minimum: `1` |
| `offset` | integer | No | Rows to skip (alternative to entry_start) Minimum: `0` |
| `flatten` | boolean | No | Flatten jagged arrays; loses event boundaries |
| `defines` | object | No | Derived branch names mapped to expressions Values: string |
| `selection` | string | No | Optional cut expression |

### `get_branch_stats`

Get statistics for branches (supports derived variables via defines)

| Argument | Type | Required | Details |
|---|---|---|---|
| `path` | string | Yes | File path |
| `tree_name` | string | Yes | Tree name |
| `branches` | array of string | Yes | Minimum items: `1` |
| `selection` | string | No | Optional cut expression |
| `defines` | object | No | Derived variable definitions (dict of name: expression) |

### `export_data`

Export selected ROOT branches to a JSON, CSV or Parquet file. Writes output_path and may overwrite it. Central deployments require an artifact-relative output path and export permission.

| Argument | Type | Required | Details |
|---|---|---|---|
| `path` | string | Yes | File path |
| `tree_name` | string | Yes | Tree name |
| `branches` | array of string | Yes | Minimum items: `1` |
| `output_path` | string | Yes | Output file path |
| `format` | string | Yes | Values: `["json", "csv", "parquet"]` |
| `selection` | string | No | Optional cut expression |
| `compress` | boolean | No | Compress output |

### `switch_mode`

Change the local server-wide analysis tier between core and extended. Affects all calls to this process; list tools again afterward. Disabled in central deployments.

| Argument | Type | Required | Details |
|---|---|---|---|
| `mode` | string | Yes | Values: `["core", "extended"]` |

### `get_server_info`

Discover ROOT analysis mode, capabilities, accessible named resources and request limits. Use before choosing analysis tools; native ROOT requires a separate installation.

No arguments. Call with `{}`. The result includes the server version, mode, deployment profile, native ROOT availability, accessible resource descriptors, limits and metrics.

## Extended tools

Requires extended mode. In local deployments, switch modes and refresh the tool catalog; central deployments keep a fixed tier.

### `compute_histogram`

Compute a 1D histogram from branch data. Use `fit_histogram` for a separate fit.

| Argument | Type | Required | Details |
|---|---|---|---|
| `path` | string or array of string | Yes | See the runtime schema for details. |
| `tree_name` | string | Yes | See the runtime schema for details. |
| `branch` | string | Yes | See the runtime schema for details. |
| `bins` | integer | Yes | Minimum: `1` |
| `range` | array of number | No | Minimum items: `2` Maximum items: `2` |
| `selection` | string | No | See the runtime schema for details. |
| `weights` | string | No | See the runtime schema for details. |

### `compute_histogram_2d`

Compute 2D histogram (supports derived variables via defines)

| Argument | Type | Required | Details |
|---|---|---|---|
| `path` | string or array of string | Yes | See the runtime schema for details. |
| `tree_name` | string | Yes | Tree name |
| `x_branch` | string | Yes | X-axis branch |
| `y_branch` | string | Yes | Y-axis branch |
| `x_bins` | integer | Yes | Number of bins in X Minimum: `1` |
| `y_bins` | integer | Yes | Number of bins in Y Minimum: `1` |
| `x_range` | array of number | No | X-axis range [min, max] Minimum items: `2` Maximum items: `2` |
| `y_range` | array of number | No | Y-axis range [min, max] Minimum items: `2` Maximum items: `2` |
| `selection` | string | No | Optional cut expression |
| `defines` | object | No | Derived variable definitions (dict of name: expression) |

### `fit_histogram`

Fit histogram with model function

| Argument | Type | Required | Details |
|---|---|---|---|
| `path` | string | Yes | See the runtime schema for details. |
| `tree_name` | string | Yes | See the runtime schema for details. |
| `branch` | string | Yes | See the runtime schema for details. |
| `bins` | integer | Yes | Minimum: `1` |
| `model` | string or array of string or array of object or object | Yes | See the runtime schema for details. |
| `range` | array of number | No | Minimum items: `2` Maximum items: `2` |
| `selection` | string | No | See the runtime schema for details. |
| `weights` | string | No | See the runtime schema for details. |
| `defines` | object | No | Derived variable definitions |
| `initial_guess` | array of number | No | See the runtime schema for details. |
| `bounds` | array of array of number | No | See the runtime schema for details. |
| `fixed_parameters` | object | No | Values: number |

### `compute_invariant_mass`

Compute invariant mass from 4-vectors

| Argument | Type | Required | Details |
|---|---|---|---|
| `path` | string | Yes | See the runtime schema for details. |
| `tree_name` | string | Yes | See the runtime schema for details. |
| `pt_branches` | array of string | Yes | See the runtime schema for details. |
| `eta_branches` | array of string | Yes | See the runtime schema for details. |
| `phi_branches` | array of string | Yes | See the runtime schema for details. |
| `mass_branches` | array of string | No | See the runtime schema for details. |

### `compute_correlation`

Compute correlation between branches

| Argument | Type | Required | Details |
|---|---|---|---|
| `path` | string | Yes | See the runtime schema for details. |
| `tree_name` | string | Yes | See the runtime schema for details. |
| `branch_x` | string | Yes | See the runtime schema for details. |
| `branch_y` | string | Yes | See the runtime schema for details. |
| `method` | string | No | Values: `["pearson", "spearman"]` |

### `plot_histogram_1d`

Plot a 1D histogram of ROOT branch data with optional cuts and weights. Writes a plot file and may overwrite output_path; use an explicit output path.

| Argument | Type | Required | Details |
|---|---|---|---|
| `data` | object | No | Pre-calculated histogram data (bin_counts, bin_edges, etc.) |
| `path` | string | No | File path (required if data not provided) |
| `tree_name` | string | No | Tree name (required if data not provided) |
| `branch` | string | No | Branch to histogram (required if data not provided) |
| `bins` | integer | No | Number of bins (required if data not provided) Minimum: `1` |
| `range` | array of number | No | Histogram range [min, max] Minimum items: `2` Maximum items: `2` |
| `selection` | string | No | Optional cut expression |
| `weights` | string | No | Optional weight branch |
| `defines` | object | No | Derived variable definitions (dict of name: expression) |
| `output_path` | string | Yes | Output file path (e.g., /tmp/plot.png) |
| `title` | string | No | Plot title |
| `xlabel` | string | No | X-axis label |
| `ylabel` | string | No | Y-axis label |
| `log_y` | boolean | No | Use log scale for y-axis |
| `style` | string | No | Plot style Values: `["default", "publication", "presentation"]` |

### `plot_histogram_2d`

Plot a 2D histogram of ROOT branch data with optional cuts. Writes a plot file and may overwrite output_path; use an explicit output path.

| Argument | Type | Required | Details |
|---|---|---|---|
| `data` | object | No | Pre-calculated histogram data (bin_counts, x_edges, y_edges, etc.) |
| `path` | string | No | File path (required if data not provided) |
| `tree_name` | string | No | Tree name (required if data not provided) |
| `branch_x` | string | No | X-axis branch (required if data not provided) |
| `branch_y` | string | No | Y-axis branch (required if data not provided) |
| `bins_x` | integer | No | Number of bins in X (required if data not provided) |
| `bins_y` | integer | No | Number of bins in Y (required if data not provided) |
| `range_x` | array of number | No | X-axis range [min, max] |
| `range_y` | array of number | No | Y-axis range [min, max] |
| `selection` | string | No | Optional cut expression |
| `weights` | string | No | Optional weight branch |
| `defines` | object | No | Derived variable definitions (dict of name: expression) |
| `output_path` | string | Yes | Output file path |
| `title` | string | No | Plot title |
| `xlabel` | string | No | X-axis label |
| `ylabel` | string | No | Y-axis label |
| `colormap` | string | No | Matplotlib colormap name |
| `log_z` | boolean | No | Use log scale for color |
| `style` | string | No | Values: `["default", "publication", "presentation"]` |

### `histogram_arithmetic`

Perform bin-by-bin arithmetic on two histograms (e.g. asymmetry, difference, ratio)

| Argument | Type | Required | Details |
|---|---|---|---|
| `operation` | string | Yes | Operation to perform: data1 [op] data2. Asymmetry is (d1-d2)/(d1+d2). Values: `["add", "subtract", "multiply", "divide", "asymmetry"]` |
| `data1` | object | Yes | First histogram data (result from compute_histogram) |
| `data2` | object | Yes | Second histogram data |

## Native ROOT tools

Requires extended mode, an external ROOT/PyROOT installation, `features.enable_root: true` and the `local_subprocess` backend. These tools are disabled centrally.

### `run_root_code`

Execute PyROOT/Python code with native ROOT. Use for operations not possible with uproot: RDataFrame, RooFit, custom classes, TCanvas plots, C++ interop, etc. IMPORTANT: Always start code with 'import ROOT' and 'ROOT.gROOT.SetBatch(True)' (prevents GUI). The variable '_output_dir' is available in code as a writable directory for saving files (plots, ROOT files). The variable '_input_files' contains the list of input file paths. To return structured data, call '_set_result(value)' where value is a JSON-serializable object, or print JSON to stdout. Prefer run_rdataframe for simple histograms.

| Argument | Type | Required | Details |
|---|---|---|---|
| `code` | string | Yes | Python code to execute. Must import ROOT explicitly. Use ROOT.gROOT.SetBatch(True) to prevent GUI. Use _output_dir for file output, _set_result() for structured results. |
| `output_dir` | string | No | Directory for output files (optional, defaults to temp dir) |
| `timeout` | integer | No | Execution timeout in seconds (default: 60). Increase for large files or complex fits. Minimum: `1` |
| `input_files` | array of string | No | Paths to ROOT files the code needs. Available inside code as _input_files list. |

### `run_rdataframe`

Compute a 1D histogram using ROOT RDataFrame. Only supports 1D histograms of a single branch. For 2D histograms, profiles, Define() columns, or other RDataFrame operations, use run_root_code instead. Preferred over run_root_code for simple 1D histograms — no boilerplate needed. Returns JSON with entries, mean, std_dev, bin_contents, bin_errors, bin_edges. Use inspect_file first to discover tree and branch names. Selection uses C++ syntax (e.g. 'pt > 20 && abs(eta) < 2.5'). Requires native ROOT.

| Argument | Type | Required | Details |
|---|---|---|---|
| `file_path` | string | Yes | Path to the ROOT file |
| `tree_name` | string | Yes | Name of the TTree or RNTuple |
| `branch` | string | Yes | Branch to histogram |
| `bins` | integer | Yes | Number of bins Minimum: `1` |
| `range_min` | number | Yes | Histogram range minimum |
| `range_max` | number | Yes | Histogram range maximum |
| `selection` | string | No | Optional cut expression (C++ syntax for RDF Filter) |
| `weight` | string | No | Optional weight column name |
| `output_path` | string | No | Save histogram plot to this path (png, pdf, svg) |
| `timeout` | integer | No | Execution timeout in seconds Minimum: `1` |

### `run_root_macro`

Execute a ROOT C++ macro via gROOT.ProcessLine. Use for short C++ snippets (e.g. 'TH1F h("h","h",100,-5,5); h.FillRandom("gaus",10000);'). Multi-line code is supported. For complex analysis, prefer run_root_code with Python. Requires native ROOT.

| Argument | Type | Required | Details |
|---|---|---|---|
| `macro_code` | string | Yes | C++ code to execute |
| `output_path` | string | No | Save any canvas output to this path (optional) |
| `timeout` | integer | No | Execution timeout in seconds Minimum: `1` |

## Typical workflow

1. `get_server_info` → choose an accessible resource and check limits.
2. `list_files` → `inspect_file` → `list_branches` → verify paths and branch types.
3. `read_branches` with a small bound → inspect a sample.
4. `get_branch_stats`, `compute_histogram` or `fit_histogram` → summarize data.
5. `plot_histogram_1d`, `plot_histogram_2d` or `export_data` → create requested files.

`fit_histogram` fits branch data from the specified file. It does not accept a
cached histogram JSON argument; the CLI's separate `fit` command does. Likewise,
MCP plotting tools read branch data, while CLI plotting commands consume cached
histogram JSON. Consult `root-cli <command> --help` for CLI arguments.
