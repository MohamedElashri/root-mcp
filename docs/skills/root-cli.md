# ROOT CLI Skills

You have access to `root-cli` for analyzing CERN ROOT files. This tool provides a command-line interface that is token-efficient and human-readable.

## Setup

```bash
# Set data path once
export ROOT_MCP_DATA_PATH=/path/to/data

# Or specify per command
root-cli -d /path/to/data <command>
```

## Command Reference

### File Operations

#### `ls` - List ROOT Files
List ROOT files in the data directory.

**Usage:**
```bash
root-cli ls [pattern] [-l limit]
```

**Options:**
- `pattern` - Glob pattern (default: `*.root`)
- `-l, --limit` - Max files to list (default: 100)

**Examples:**
```bash
root-cli ls
root-cli ls "run_*.root"
root-cli ls --limit 10
```

**Output:**
```
Found 5 ROOT files in /data:
  sample.root          1.2 MB
  run_001.root        15.3 MB
```

---

#### `inspect` - Inspect ROOT File
Show file structure including TTrees and RNTuples, branches, and histograms.

**Usage:**
```bash
root-cli inspect <file.root>
```

**Options:**
- `--no-trees` - Skip tree metadata
- `--no-histograms` - Skip histogram metadata

**Examples:**
```bash
root-cli inspect /data/sample.root
```

**Output:**
```
File: /data/sample.root
Size: 1.1 MB

TTrees and RNTuples (2):
  events;1             10,000 entries, 26 branches
  metadata;1              1 entries, 2 branches

JSON: /tmp/root_mcp/sample_info.json
```

---

#### `branches` - List Branches
List branches in a TTree or RNTuple with type information.

**Usage:**
```bash
root-cli branches <file.root> <tree> [-p pattern] [-l limit] [-s]
```

**Options:**
- `-p, --pattern` - Glob pattern for branch names
- `-l, --limit` - Max branches to list (default: 100)
- `-s, --stats` - Compute statistics (slower)

**Examples:**
```bash
root-cli branches /data/sample.root events
root-cli branches /data/sample.root events --pattern "muon_*"
root-cli branches /data/sample.root events --stats
```

**Output:**
```
Tree: events in /data/sample.root
Total entries: 10,000

Branches (10):
  event_number         uint64_t
  met                  float
  muon_pt              float[]
  muon_eta             float[]

JSON: /tmp/root_mcp/events_branches.json
```

---

#### `validate` - Validate File
Check ROOT file integrity and readability.

**Usage:**
```bash
root-cli validate <file.root>
```z

**Examples:**
```bash
root-cli validate /data/sample.root
```

**Output:**
```
File: /data/sample.root
Status: ✓ Valid
Readable: ✓ Yes
Compression: 2.3
Trees: 2
  - events;1
  - metadata;1
```

---

### Data Access

#### `read` - Read Branch Data
Read data from a TTree or RNTuple branches with optional selection.

**Usage:**
```bash
root-cli read <file.root> <tree> <branches...> [options]
```

**Options:**
- `-s, --selection` - Cut expression (C++ syntax)
- `-l, --limit` - Max entries to read
- `-o, --offset` - Skip first N entries
- `--flatten` - Flatten jagged arrays
- `-d, --defines` - Derived variables (name=expr)

**Examples:**
```bash
root-cli read /data/sample.root events met muon_pt
root-cli read /data/sample.root events met muon_pt --selection "met > 50"
root-cli read /data/sample.root events jet_pt --limit 1000
root-cli read /data/sample.root events pt eta phi --defines "pT=pt*1.1"
```

**Output:**
```
Read 100 entries from events
Branches: met, muon_pt
Selection: met > 50

First 3 entries:
  0: {'met': 52.3, 'muon_pt': [25.1, 30.2]}
  1: {'met': 78.9, 'muon_pt': [45.6]}

JSON: /tmp/root_mcp/events_data.json
```

---

#### `stats` - Compute Statistics
Compute statistics for branches.

**Usage:**
```bash
root-cli stats <file.root> <tree> <branches...> [-s selection]
```

**Options:**
- `-s, --selection` - Cut expression

**Examples:**
```bash
root-cli stats /data/sample.root events met muon_pt jet1_pt
root-cli stats /data/sample.root events met --selection "met > 20"
```

**Output:**
```
Statistics for events in /data/sample.root:

met:
  count:        10,000
  mean:         29.325 ± 14.615
  std:          29.231
  range:  [0.000, 245.173]
  median:       20.349

JSON: /tmp/root_mcp/events_stats.json
```

---

#### `sample` - Sample Data
Get a sample from a TTree or RNTuple.

**Usage:**
```bash
root-cli sample <file.root> <tree> [--size N] [--method first|random]
```

**Options:**
- `--size` - Sample size (default: 100)
- `--method` - Sampling method: `first` or `random`
- `--branches` - Branches to include
- `--seed` - Random seed (for random sampling)

**Examples:**
```bash
root-cli sample /data/sample.root events --size 100
root-cli sample /data/sample.root events --method random --size 50 --seed 42
```

**Output:**
```
Sampled 100 entries from events
Method: first

First 3 entries:
  0: {'event_number': 0, 'met': 14.08, ...}

JSON: /tmp/root_mcp/events_sample.json
```

---

#### `export` - Export Data
Export branch data to CSV, JSON, or Parquet.

**Usage:**
```bash
root-cli export <file.root> <tree> <branches...> -o <output> [--format csv|json|parquet]
```

**Options:**
- `-o, --output` - Output file path (required)
- `--format` - Output format (default: csv)
- `-s, --selection` - Cut expression
- `-l, --limit` - Max entries to export

**Examples:**
```bash
root-cli export /data/sample.root events met muon_pt -o data.csv
root-cli export /data/sample.root events met pt -o data.parquet --format parquet
root-cli export /data/sample.root events met --selection "met > 50" -o selected.json
```

**Output:**
```
Exported 5,057 entries
Format: csv
Output: data.csv
File size: 245,678 bytes
```

---

### Histogram Analysis

#### `histogram` - Create 1D Histogram
Create a 1D histogram with optional fit.

**Usage:**
```bash
root-cli histogram <file.root> <tree> <branch> [options]
```

**Options:**
- `-b, --bins` - Number of bins (default: 100)
- `-r, --range` - Range as two values (min max)
- `-s, --selection` - Cut expression
- `-w, --weights` - Weight branch
- `-f, --fit` - Fit model: gaussian, exponential, polynomial, crystal_ball
- `--fit-range` - Fit range (min max)
- `-d, --defines` - Derived variables (name=expr)

**Examples:**
```bash
root-cli histogram /data/sample.root events met --bins 50
root-cli histogram /data/sample.root events met --bins 50 --range 0 200
root-cli histogram /data/sample.root events dimuon_mass --fit gaussian --fit-range 80 100
root-cli histogram /data/sample.root events pt --selection "pt > 20"
```

**Output:**
```
Histogram: met in events
File: /data/sample.root (10,000 entries)

Statistics:
  mean:  29.325
  std:   29.231
  min:   0.000
  max:   245.173

gaussian fit:
  amplitude:  1250.5000 ± 15.2000
  mean:       30.1000 ± 0.5000
  sigma:      15.2000 ± 0.3000
  χ²/ndof: 45.3/47 = 0.96

JSON: /tmp/root_mcp/met_hist.json
```

---

#### `histogram2d` - Create 2D Histogram
Create a 2D histogram for correlation studies.

**Usage:**
```bash
root-cli histogram2d <file.root> <tree> <x_branch> <y_branch> [options]
```

**Options:**
- `--xbins` - Number of X bins (default: 50)
- `--ybins` - Number of Y bins (default: 50)
- `--xrange` - X range (min max)
- `--yrange` - Y range (min max)
- `-s, --selection` - Cut expression
- `-d, --defines` - Derived variables

**Examples:**
```bash
root-cli histogram2d /data/sample.root events met met_phi
root-cli histogram2d /data/sample.root events muon_eta muon_phi --xbins 30 --ybins 30
root-cli histogram2d /data/sample.root events jet1_pt jet2_pt --xrange 0 200 --yrange 0 200
```

**Output:**
```
2D Histogram: met vs met_phi
Tree: events in /data/sample.root
Bins: 50 x 50
Total entries: 10,000

JSON: /tmp/root_mcp/met_vs_met_phi_hist2d.json
```

---

#### `fit` - Fit Histogram
Fit a mathematical model to histogram data.

**Usage:**
```bash
root-cli fit <histogram.json> <model> [options]
```

**Options:**
- `--fit-range` - Fit range (min max)
- `-i, --initial-params` - Initial parameters (name=value)

**Models:** gaussian, exponential, polynomial, crystal_ball

**Examples:**
```bash
root-cli fit /tmp/root_mcp/met_hist.json gaussian
root-cli fit /tmp/root_mcp/mass_hist.json crystal_ball --fit-range 80 100
root-cli fit /tmp/root_mcp/pt_hist.json exponential -i amplitude=1000 -i lambda=0.1
```

**Output:**
```
Fit model: gaussian
Source: /tmp/root_mcp/met_hist.json

Fit parameters:
  amplitude:  1250.5000 ± 15.2000
  mean:       30.1000 ± 0.5000
  sigma:      15.2000 ± 0.3000

Fit quality:
  χ²/ndof: 45.3/47 = 0.96
  Success: True

JSON: /tmp/root_mcp/fit_results.json
```

---

#### `hist-arithmetic` - Histogram Arithmetic
Perform bin-by-bin arithmetic on histograms.

**Usage:**
```bash
root-cli hist-arithmetic <operation> <hist1.json> <hist2.json> [-o output]
```

**Operations:** add, subtract, multiply, divide, asymmetry

**Examples:**
```bash
root-cli hist-arithmetic add /tmp/data.json /tmp/mc.json
root-cli hist-arithmetic divide /tmp/data.json /tmp/mc.json -o ratio.json
root-cli hist-arithmetic asymmetry /tmp/pos.json /tmp/neg.json
```

**Output:**
```
Histogram divide:
  Input 1: /tmp/data.json
  Input 2: /tmp/mc.json
  Entries: 10,000
  Result range: [0.850, 1.150]
  Result mean:  1.000

JSON: /tmp/root_mcp/hist_divide.json
```

---

### Statistical Analysis

#### `correlation` - Compute Correlation
Compute correlation matrix between branches.

**Usage:**
```bash
root-cli correlation <file.root> <tree> <branches...> [options]
```

**Options:**
- `--method` - pearson or spearman (default: pearson)
- `-s, --selection` - Cut expression

**Examples:**
```bash
root-cli correlation /data/sample.root events met jet1_pt jet2_pt
root-cli correlation /data/sample.root events muon_pt muon_eta --method spearman
```

**Output:**
```
Pearson correlation matrix
Tree: events in /data/sample.root
Branches: met, jet1_pt, jet2_pt

                    met     jet1_pt   jet2_pt
met                 1.000     0.234     0.187
jet1_pt             0.234     1.000     0.456
jet2_pt             0.187     0.456     1.000

JSON: /tmp/root_mcp/correlation_matrix.json
```

---

### Kinematics

#### `invariant-mass` - Compute Invariant Mass
Calculate invariant mass from particle 4-vectors.

**Usage:**
```bash
root-cli invariant-mass <file.root> <tree> --pt <branches> --eta <branches> --phi <branches>
```

**Options:**
- `--pt` - PT branches (can specify multiple)
- `--eta` - Eta branches (can specify multiple)
- `--phi` - Phi branches (can specify multiple)
- `--mass` - Mass branches (optional)
- `-s, --selection` - Cut expression
- `-l, --limit` - Max entries

**Examples:**
```bash
# Dimuon invariant mass
root-cli invariant-mass /data/sample.root events \
  --pt mu1_pt mu2_pt \
  --eta mu1_eta mu2_eta \
  --phi mu1_phi mu2_phi

# With explicit masses
root-cli invariant-mass /data/sample.root events \
  --pt mu1_pt mu2_pt \
  --eta mu1_eta mu2_eta \
  --phi mu1_phi mu2_phi \
  --mass mu1_mass mu2_mass

# With selection
root-cli invariant-mass /data/sample.root events \
  --pt mu1_pt mu2_pt \
  --eta mu1_eta mu2_eta \
  --phi mu1_phi mu2_phi \
  --selection "mu1_pt > 20 && mu2_pt > 20"
```

**Output:**
```
Invariant mass computed
Tree: events in /data/sample.root

Statistics:
  Entries: 5,432
  Mean:    91.212
  Std:     2.515
  Min:     80.123
  Max:     105.678
  Median:  90.987

JSON: /tmp/root_mcp/invariant_mass.json
```

---

### Visualization

#### `plot1d` - Plot 1D Histogram
Create a plot from histogram data.

**Usage:**
```bash
root-cli plot1d <histogram.json> -o <output.png> [options]
```

**Options:**
- `-o, --output` - Output file path (required)
- `-t, --title` - Plot title
- `-x, --xlabel` - X-axis label
- `-y, --ylabel` - Y-axis label (default: Events)
- `--log-y` - Log scale Y axis
- `--style` - default, publication, presentation

**Examples:**
```bash
root-cli plot1d /tmp/root_mcp/met_hist.json -o met.png
root-cli plot1d /tmp/root_mcp/mass_hist.json -o mass.pdf \
  --title "Dimuon Invariant Mass" \
  --xlabel "m_{#mu#mu} (GeV)" \
  --ylabel "Events / 2 GeV"
root-cli plot1d /tmp/root_mcp/pt_hist.json -o pt_log.png --log-y --style publication
```

**Output:**
```
Plot created: met.png
Source: /tmp/root_mcp/met_hist.json
Title: MET Distribution
```

---

#### `plot2d` - Plot 2D Histogram
Create a 2D plot from histogram data.

**Usage:**
```bash
root-cli plot2d <histogram2d.json> -o <output.png> [options]
```

**Options:**
- `-o, --output` - Output file path (required)
- `-t, --title` - Plot title
- `-x, --xlabel` - X-axis label
- `-y, --ylabel` - Y-axis label
- `--colormap` - Matplotlib colormap (default: viridis)
- `--log-z` - Log scale color
- `--style` - default, publication, presentation

**Examples:**
```bash
root-cli plot2d /tmp/root_mcp/eta_phi_hist2d.json -o eta_phi.png
root-cli plot2d /tmp/root_mcp/correlation_hist2d.json -o corr.pdf \
  --colormap inferno \
  --title "MET vs MET Phi"
```

**Output:**
```
2D Plot created: eta_phi.png
Source: /tmp/root_mcp/eta_phi_hist2d.json
Colormap: viridis
```

---

### Utility

#### `info` - Show CLI Information
Display available commands and configuration.

**Usage:**
```bash
root-cli info
```

**Output:**
```
ROOT CLI v0.1.0
Data path: /data
Output directory: /tmp/root_mcp
Backend: Available

Available commands (17):
  - ls
  - inspect
  - branches
  - validate
  - read
  - stats
  - export
  - sample
  - histogram
  - histogram2d
  - fit
  - invariant-mass
  - correlation
  - plot1d
  - plot2d
  - hist-arithmetic
  - info
```

---

## Common Workflows

### Workflow 1: Exploratory Analysis
```bash
# 1. List available files
root-cli ls

# 2. Inspect file structure
root-cli inspect /data/sample.root

# 3. Check available branches
root-cli branches /data/sample.root events --pattern "muon_*"

# 4. Get basic statistics
root-cli stats /data/sample.root events met muon_pt muon_eta
```

### Workflow 2: Histogram with Fit
```bash
# 1. Create histogram with fit
root-cli histogram /data/sample.root events dimuon_mass \
  --bins 100 --range 80 100 \
  --fit gaussian --fit-range 85 95

# 2. Review fit quality in output

# 3. Create publication plot
root-cli plot1d /tmp/root_mcp/dimuon_mass_hist.json \
  -o dimuon_mass.png \
  --title "Dimuon Invariant Mass" \
  --xlabel "m_{#mu#mu} (GeV)" \
  --style publication
```

### Workflow 3: Data Selection and Export
```bash
# 1. Read data with selection
root-cli read /data/sample.root events \
  run event met muon_pt \
  --selection "met > 50 && muon_pt > 20" \
  --limit 10000

# 2. Export to parquet
root-cli export /data/sample.root events \
  met muon_pt muon_eta \
  -o selected.parquet --format parquet \
  --selection "met > 50"
```

### Workflow 4: Correlation Study
```bash
# 1. Compute correlations
root-cli correlation /data/sample.root events met jet1_pt jet2_pt

# 2. Create 2D histogram
root-cli histogram2d /data/sample.root events jet1_pt jet2_pt \
  --xbins 50 --ybins 50 \
  --xrange 0 200 --yrange 0 200

# 3. Plot correlation
root-cli plot2d /tmp/root_mcp/jet1_pt_vs_jet2_pt_hist2d.json \
  -o jet_correlation.png --colormap viridis
```

### Workflow 5: Kinematic Analysis
```bash
# 1. Compute dimuon invariant mass
root-cli invariant-mass /data/sample.root events \
  --pt mu1_pt mu2_pt \
  --eta mu1_eta mu2_eta \
  --phi mu1_phi mu2_phi

# 2. Histogram the result
root-cli histogram /data/sample.root events dimuon_mass \
  --bins 100 --range 80 100

# 3. Fit for Z boson peak
root-cli fit /tmp/root_mcp/dimuon_mass_hist.json gaussian \
  --fit-range 85 95
```

---

## Selection Expressions

Selection expressions use C++ syntax:

```bash
# Simple cuts
--selection "muon_pt > 20"
--selection "abs(muon_eta) < 2.4"

# Combined cuts
--selection "muon_pt > 20 && abs(muon_eta) < 2.4"
--selection "met > 50 || jet_pt > 100"

# Complex expressions
--selection "nMuons == 2 && dimuon_mass > 80 && dimuon_mass < 100"
```

**Supported operations:**
- Comparison: `>`, `<`, `>=`, `<=`, `==`, `!=`
- Logical: `&&` (and), `||` (or), `!` (not)
- Math: `+`, `-`, `*`, `/`, `**` (power)
- Functions: `abs()`, `sqrt()`, `log()`, `exp()`, `sin()`, `cos()`, `tan()`

---

## Output Files

All commands save structured output to `/tmp/root_mcp/`:

```
/tmp/root_mcp/
├── events_data.json        # Read branch data
├── met_hist.json           # Histogram data
├── hist2d.json             # 2D histogram data
├── correlation_matrix.json # Correlation results
├── fit_results.json        # Fit parameters
├── events_stats.json       # Statistics
└── plots/
    ├── met.png             # 1D plots
    └── correlation.png     # 2D plots
```

Use these JSON files as input to subsequent commands:
```bash
# Create histogram
root-cli histogram file.root events met --bins 50

# Use histogram JSON for plotting
root-cli plot1d /tmp/root_mcp/met_hist.json -o plot.png

# Use histogram JSON for fitting
root-cli fit /tmp/root_mcp/met_hist.json gaussian
```

---

## Tips

**Performance:**
- Use `--limit` to test commands on small samples first
- Apply `--selection` early to reduce data processed
- Use `--offset` and `--limit` for chunked processing of large files

**Quality:**
- Check fit quality (χ²/ndof close to 1 indicates good fit)
- Verify statistics make physical sense
- Use appropriate binning for your data range

**Debugging:**
- Run commands manually in terminal to test
- Check `/tmp/root_mcp/` for detailed JSON output
- Use `root-cli <command> --help` for full options

**JSON Output:**
- Add `--json` flag for machine-readable output
- JSON files are always saved for programmatic chaining
