---
name: root-cli
description: >
  Analyze CERN ROOT files using the root-cli command-line tool. Use this skill
  for any task involving ROOT files (.root), TTree/RNTuple inspection, branch reading,
  histogram computation, kinematic reconstruction, fitting, correlation analysis,
  or exporting HEP data. Trigger whenever the user mentions ROOT files, TTrees, RNTuples,
  for any task involving ROOT files (.root), TTree inspection, branch reading,
  histogram computation, kinematic reconstruction, fitting, correlation analysis,
  or exporting HEP data. Trigger whenever the user mentions ROOT files, TTrees,
  branches, histograms, invariant mass, MET, particle physics data, or asks to
  inspect/plot/fit/export data from .root files. Prefer root-cli over PyROOT/
  uproot scripting for interactive analysis — it saves thousands of tokens and
  provides a clean, composable command surface. Also trigger when the user asks
  to use root-mcp in CLI mode.
---

# ROOT CLI Skill

`root-cli` is a token-efficient CLI for CERN ROOT files. It replaces verbose MCP JSON
exchanges with terse, composable shell commands. Intermediate results (histograms, fits)
are cached as JSON under `/tmp/root_mcp/` and consumed by downstream commands.

## Setup

```bash
# Set data path once (or use -d per command)
export ROOT_MCP_DATA_PATH=/path/to/data

# Verify installation
root-cli info
```

All commands accept `--json` for machine-readable output piped into other tools.

---

## Command Reference

### File Operations

| Command | Purpose |
|---|---|
| `root-cli ls [pattern] [--limit N]` | List ROOT files in data dir |
| `root-cli inspect <file.root>` | Show TTrees, RNTuples, histograms, directories |
| `root-cli inspect <file.root>` | Show TTrees, histograms, directories |
| `root-cli branches <file.root> <tree> [-p pattern] [-s]` | List branches + types; `-s` adds stats |
| `root-cli validate <file.root>` | Check file integrity |

### Data Access

| Command | Purpose |
|---|---|
| `root-cli stats <file.root> <tree> <branches...> [-s cut]` | mean/std/min/max/median |
| `root-cli read <file.root> <tree> <branches...> [-s cut] [-l N] [--flatten] [-d name=expr]` | Read raw data |
| `root-cli sample <file.root> <tree> [--size N] [--method first\|random]` | Quick sample |
| `root-cli export <file.root> <tree> <branches...> -o out [-s cut] [--format csv\|json\|parquet]` | Export data |

**Cut syntax**: C++ expressions — `"pt > 20 && abs(eta) < 2.4"`, `"n_jets >= 2"`
**Derived variables**: `-d met_x="met*cos(met_phi)"` — defines new branches inline

### Histogram Analysis

```bash
# 1D histogram (result cached to /tmp/root_mcp/<branch>_hist.json)
root-cli histogram <file.root> <tree> <branch> \
  [--bins 100] [--range MIN MAX] [-s cut] \
  [--fit gaussian|exponential|polynomial|crystal_ball] [--fit-range MIN MAX]

# 2D histogram
root-cli histogram2d <file.root> <tree> <x_branch> <y_branch> \
  [--xbins 50] [--ybins 50] [--xrange MIN MAX] [--yrange MIN MAX]

# Fit a cached histogram JSON
root-cli fit /tmp/root_mcp/<hist>.json <model> \
  [--fit-range MIN MAX] [-i param=value]

# Histogram arithmetic (signal/background ratio, efficiency, etc.)
root-cli hist-arithmetic <add|subtract|multiply|divide|asymmetry> hist1.json hist2.json
```

### Statistical Analysis & Kinematics

```bash
# Pearson or Spearman correlation matrix
root-cli correlation <file.root> <tree> <branches...> [--method pearson|spearman]

# Invariant mass from (pt, eta, phi[, mass]) 4-vectors
root-cli invariant-mass <file.root> <tree> \
  --pt mu1_pt mu2_pt \
  --eta mu1_eta mu2_eta \
  --phi mu1_phi mu2_phi \
  [--mass mu1_m mu2_m] [-s cut] [-l N]
```

### Visualization

```bash
# 1D plot from cached histogram JSON
root-cli plot1d /tmp/root_mcp/<hist>.json -o out.png \
  [-t "Title"] [-x "X label"] [-y "Y label"] [--log-y] \
  [--style default|publication|presentation]

# 2D plot
root-cli plot2d /tmp/root_mcp/<hist2d>.json -o out.png \
  [-t "Title"] [--colormap viridis|inferno|...] [--log-z]
```

---

## Canonical Workflows

### Exploratory Analysis
```bash
root-cli ls                                          # discover files
root-cli inspect data.root                           # top-level structure
root-cli branches data.root events --pattern "mu*"   # branch listing
root-cli stats data.root events met muon_pt jet1_pt  # quick sanity check
root-cli sample data.root events --size 10           # eyeball data
```

### Histogram → Fit → Plot (e.g. J/ψ peak)
```bash
root-cli histogram data.root events dimuon_mass \
  --bins 100 --range 2.8 3.4 --fit gaussian --fit-range 3.0 3.2

root-cli plot1d /tmp/root_mcp/dimuon_mass_hist.json \
  -o jpsi.png --title "J/ψ → μμ" --xlabel "m(μμ) [GeV]" --style publication
```

### Selection → Export Pipeline
```bash
root-cli export data.root events met muon_pt muon_eta \
  --selection "met > 50 && muon_pt > 20" \
  -o selected.parquet --format parquet
```

### Signal/Background Efficiency
```bash
root-cli histogram2d data.root events muon_pt muon_eta -o
root-cli hist-arithmetic divide /tmp/root_mcp/sig.json /tmp/root_mcp/bkg.json
```

### Kinematic Reconstruction
```bash
root-cli invariant-mass data.root events \
  --pt mu1_pt mu2_pt --eta mu1_eta mu2_eta --phi mu1_phi mu2_phi \
  --selection "mu1_pt > 20 && mu2_pt > 10" --limit 50000
```

---

## Key Behaviours & Gotchas

- **Intermediate JSON lives in `/tmp/root_mcp/`** — histogram and fit commands write there automatically; `plot1d`/`plot2d`/`fit` consume those files by path.
- **Jagged arrays** (e.g. per-event muon collections): use `--flatten` with `read` or `root-cli` handles them implicitly for stats/histograms.
- **Mode fallback**: root-cli is always available; it does not require the MCP server to be running.
- **Token efficiency**: prefer root-cli over issuing raw PyROOT/uproot Python scripts unless custom logic is unavoidable.
- **Fit models available**: `gaussian`, `exponential`, `polynomial`, `crystal_ball` — use `crystal_ball` for asymmetric tails (e.g. B meson mass peaks).
- **`--json` output**: pipe into `jq` or consume programmatically; useful when chaining commands in scripts.

---

## Decision Guide

| Task | Recommended command |
|---|---|
| First look at a new file | `inspect` → `branches` |
| Quick numerical sanity | `stats` |
| Mass peak / signal extraction | `histogram --fit gaussian` or `crystal_ball` |
| Correlation study | `correlation` |
| Particle reconstruction | `invariant-mass` |
| Downstream ML / pandas | `export --format parquet` |
| Publication plot | `plot1d --style publication` |
| Compare data vs MC | `hist-arithmetic divide` or `asymmetry` |
