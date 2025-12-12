# ROOT-MCP Demo: AI Model Interactions

This document shows realistic AI model interactions with the ROOT-MCP server, demonstrating how an LLM would use the tools to perform physics analysis.

## Scenario 1: First-Time Data Exploration

**User**: "I have a ROOT file with collision data. Can you help me explore it?"

**AI Model's Internal Process**:

### Step 1: Discover Available Files

```json
Tool: list_files
Arguments: {}

Response:
{
  "data": {
    "files": [
      {
        "path": "/data/root_files/sample_events.root",
        "size_bytes": 1245678,
        "modified": 1710504600.0,
        "resource": "local_data"
      }
    ],
    "total_matched": 1
  },
  "suggestions": [
    "Inspect sample_events.root with inspect_file()"
  ]
}
```

### Step 2: Inspect File Structure

```json
Tool: inspect_file
Arguments: {
  "path": "/data/root_files/sample_events.root"
}

Response:
{
  "data": {
    "path": "/data/root_files/sample_events.root",
    "size_bytes": 1245678,
    "compression": "LZMA:4",
    "trees": [
      {
        "name": "events",
        "path": "events",
        "entries": 10000,
        "branches": 16
      },
      {
        "name": "metadata",
        "path": "metadata",
        "entries": 1,
        "branches": 4
      }
    ],
    "histograms": [],
    "directories": []
  },
  "suggestions": [
    "Explore 'events' tree with 10,000 entries using list_branches()"
  ]
}
```

### Step 3: List Available Branches

```json
Tool: list_branches
Arguments: {
  "path": "/data/root_files/sample_events.root",
  "tree": "events",
  "limit": 20
}

Response:
{
  "data": {
    "tree": "events",
    "total_entries": 10000,
    "total_branches": 16,
    "branches": [
      {
        "name": "event_number",
        "type": "uint64",
        "title": "",
        "is_jagged": false
      },
      {
        "name": "run_number",
        "type": "uint32",
        "title": "",
        "is_jagged": false
      },
      {
        "name": "met",
        "type": "float32",
        "title": "",
        "is_jagged": false
      },
      {
        "name": "muon_pt",
        "type": "float32[]",
        "title": "",
        "is_jagged": true
      },
      {
        "name": "muon_eta",
        "type": "float32[]",
        "title": "",
        "is_jagged": true
      },
      {
        "name": "muon_phi",
        "type": "float32[]",
        "title": "",
        "is_jagged": true
      },
      {
        "name": "muon_charge",
        "type": "int32[]",
        "title": "",
        "is_jagged": true
      },
      {
        "name": "electron_pt",
        "type": "float32[]",
        "title": "",
        "is_jagged": true
      },
      {
        "name": "jet_pt",
        "type": "float32[]",
        "title": "",
        "is_jagged": true
      },
      {
        "name": "jet_btag",
        "type": "float32[]",
        "title": "",
        "is_jagged": true
      }
    ],
    "matched": 16
  },
  "suggestions": [
    "Sample data with read_branches(branches=['muon_pt', 'muon_eta', 'muon_phi'])"
  ]
}
```

### Step 4: Sample Data to Understand Structure

```json
Tool: sample_tree
Arguments: {
  "path": "/data/root_files/sample_events.root",
  "tree": "events",
  "size": 5,
  "branches": ["event_number", "muon_pt", "muon_eta", "muon_charge"]
}

Response:
{
  "data": {
    "branches": ["event_number", "muon_pt", "muon_eta", "muon_charge"],
    "entries": 5,
    "is_jagged": true,
    "records": [
      {
        "event_number": 0,
        "muon_pt": [45.2, 28.3],
        "muon_eta": [0.5, -1.2],
        "muon_charge": [1, -1]
      },
      {
        "event_number": 1,
        "muon_pt": [67.8],
        "muon_eta": [-0.3],
        "muon_charge": [1]
      },
      {
        "event_number": 2,
        "muon_pt": [],
        "muon_eta": [],
        "muon_charge": []
      },
      {
        "event_number": 3,
        "muon_pt": [34.5, 22.1, 19.8],
        "muon_eta": [1.8, 0.2, -0.9],
        "muon_charge": [-1, 1, 1]
      },
      {
        "event_number": 4,
        "muon_pt": [52.3],
        "muon_eta": [1.1],
        "muon_charge": [-1]
      }
    ]
  },
  "suggestions": [
    "Data has variable-length arrays - use flatten=true for flat output"
  ]
}
```

**AI Response to User**:

"I found your ROOT file! It contains collision data with **10,000 events**. Here's what's in it:

**Physics Objects**:
- **Muons**: pT, η, φ, charge (variable number per event)
- **Electrons**: pT, η, φ
- **Jets**: pT, η, φ, b-tagging scores
- **Missing ET**: magnitude and φ

**Data Structure**:
- Events have 0-3 muons (jagged arrays)
- Example: Event 0 has 2 muons (pT: 45.2, 28.3 GeV)
- Event 2 has no muons
- Event 3 has 3 muons

What would you like to analyze? I can:
- Plot distributions (e.g., muon pT spectrum)
- Apply selections (e.g., find events with high-pT muons)
- Calculate statistics
- Export filtered data"

---

## Scenario 2: Physics Analysis - Finding High-pT Muons

**User**: "What's the distribution of transverse momentum for muons with pT > 20 GeV and |η| < 2.4?"

**AI Model's Internal Process**:

### Step 1: Check Selection Efficiency

```json
Tool: apply_selection
Arguments: {
  "path": "/data/root_files/sample_events.root",
  "tree": "events",
  "selection": "muon_pt > 20 && abs(muon_eta) < 2.4"
}

Response:
{
  "data": {
    "entries_total": 10000,
    "entries_selected": 4523,
    "efficiency": 0.4523,
    "selection": "muon_pt > 20 && abs(muon_eta) < 2.4"
  },
  "suggestions": [
    "45.2% of events pass selection (4,523/10,000)",
    "Proceed with compute_histogram() or read_branches() using this selection"
  ]
}
```

### Step 2: Compute Histogram

```json
Tool: compute_histogram
Arguments: {
  "path": "/data/root_files/sample_events.root",
  "tree": "events",
  "branch": "muon_pt",
  "bins": 50,
  "range": [20, 200],
  "selection": "muon_pt > 20 && abs(muon_eta) < 2.4"
}

Response:
{
  "data": {
    "bin_edges": [20, 23.6, 27.2, 30.8, ..., 196.4, 200],
    "bin_counts": [245, 312, 389, 421, ..., 5, 2],
    "bin_errors": [15.65, 17.66, 19.72, 20.52, ..., 2.24, 1.41],
    "underflow": 0,
    "overflow": 34,
    "entries": 6847,
    "sum_weights": 6847,
    "mean": 42.3,
    "std": 28.7
  },
  "metadata": {
    "operation": "compute_histogram",
    "branch": "muon_pt",
    "bins": 50,
    "range": [20, 200],
    "selection": "muon_pt > 20 && abs(muon_eta) < 2.4"
  },
  "suggestions": [
    "34 entries overflow (pT > 200 GeV) - consider extending range"
  ]
}
```

**AI Response to User**:

"Here's the muon pT distribution for your selection:

**Selection**: pT > 20 GeV and |η| < 2.4
- **Events passing cut**: 4,523 out of 10,000 (45.2%)
- **Total muons**: 6,847 (after selection)

**Distribution**:
- **Range**: 20-200 GeV (50 bins)
- **Mean**: 42.3 GeV
- **Std dev**: 28.7 GeV
- **Overflow**: 34 muons with pT > 200 GeV

**Shape**:
- Peak around 25-30 GeV (typical for muons from W/Z decays)
- Exponential tail extending to high pT
- Consistent with QCD + electroweak production

The bin counts are: [245, 312, 389, 421, ...] for edges [20, 23.6, 27.2, 30.8, ...]

Would you like me to:
- Plot η vs φ correlation?
- Compare to electrons?
- Export this data for further analysis?"

---

## Scenario 3: Comparative Analysis

**User**: "Compare the pT distributions of muons vs electrons"

**AI Model's Internal Process**:

### Step 1: Get Muon Statistics

```json
Tool: get_branch_stats
Arguments: {
  "path": "/data/root_files/sample_events.root",
  "tree": "events",
  "branches": ["muon_pt"],
  "selection": "muon_pt > 0"
}

Response:
{
  "data": {
    "statistics": {
      "muon_pt": {
        "count": 14532,
        "mean": 38.5,
        "std": 26.2,
        "min": 10.1,
        "max": 487.3,
        "median": 32.1
      }
    }
  }
}
```

### Step 2: Get Electron Statistics

```json
Tool: get_branch_stats
Arguments: {
  "path": "/data/root_files/sample_events.root",
  "tree": "events",
  "branches": ["electron_pt"]
}

Response:
{
  "data": {
    "statistics": {
      "electron_pt": {
        "count": 9876,
        "mean": 52.4,
        "std": 35.8,
        "min": 15.3,
        "max": 523.1,
        "median": 42.7
      }
    }
  }
}
```

### Step 3: Compute Overlapping Histograms

```json
Tool: compute_histogram
Arguments: {
  "path": "/data/root_files/sample_events.root",
  "tree": "events",
  "branch": "muon_pt",
  "bins": 40,
  "range": [0, 200]
}

[Muon histogram result...]

Tool: compute_histogram
Arguments: {
  "path": "/data/root_files/sample_events.root",
  "tree": "events",
  "branch": "electron_pt",
  "bins": 40,
  "range": [0, 200]
}

[Electron histogram result...]
```

**AI Response to User**:

"Here's a comparison of muon vs electron pT distributions:

**Muons**:
- Count: 14,532
- Mean: 38.5 ± 26.2 GeV
- Median: 32.1 GeV
- Range: 10.1 - 487.3 GeV

**Electrons**:
- Count: 9,876 (32% fewer than muons)
- Mean: 52.4 ± 35.8 GeV (36% higher)
- Median: 42.7 GeV
- Range: 15.3 - 523.1 GeV

**Key Differences**:
1. Electrons have higher average pT (52.4 vs 38.5 GeV)
2. Electrons show broader distribution (σ = 35.8 vs 26.2 GeV)
3. Fewer electrons overall (typical due to reconstruction efficiency)

This is consistent with expected detector behavior where:
- Muons are easier to reconstruct (minimal ionization)
- Electrons have electromagnetic shower, harder to measure precisely
- Both follow expected pT spectra from Standard Model processes

[Histogram data for both available for plotting]"

---

## Scenario 4: Data Export for Machine Learning

**User**: "Export all jet features for events with at least 2 jets, for ML training"

**AI Model's Internal Process**:

### Step 1: Check Selection

```json
Tool: apply_selection
Arguments: {
  "path": "/data/root_files/sample_events.root",
  "tree": "events",
  "selection": "jet_pt.size() >= 2"
}

Response:
{
  "data": {
    "entries_total": 10000,
    "entries_selected": 7234,
    "efficiency": 0.7234
  }
}
```

### Step 2: Export Data

```json
Tool: export_branches
Arguments: {
  "path": "/data/root_files/sample_events.root",
  "tree": "events",
  "branches": ["jet_pt", "jet_eta", "jet_phi", "jet_btag", "event_number"],
  "selection": "jet_pt.size() >= 2",
  "output_path": "/tmp/root_mcp_output/jets_for_ml.parquet",
  "output_format": "parquet",
  "limit": 100000
}

Response:
{
  "data": {
    "output_path": "/tmp/root_mcp_output/jets_for_ml.parquet",
    "format": "parquet",
    "entries_written": 7234,
    "size_bytes": 892456
  },
  "suggestions": [
    "Exported 7,234 entries to Parquet (0.85 MB)",
    "Use pandas.read_parquet() or PyArrow to read"
  ]
}
```

**AI Response to User**:

"I've exported the jet data for ML training:

**Export Summary**:
- **File**: /tmp/root_mcp_output/jets_for_ml.parquet
- **Format**: Parquet (efficient columnar storage)
- **Events**: 7,234 (72.3% of dataset)
- **Size**: 0.85 MB
- **Selection**: Events with ≥2 jets

**Features Included**:
- jet_pt (transverse momentum)
- jet_eta (pseudorapidity)
- jet_phi (azimuthal angle)
- jet_btag (b-tagging discriminant)
- event_number (for tracking)

**Next Steps**:
```python
import pandas as pd
import pyarrow.parquet as pq

# Load data
df = pd.read_parquet('/tmp/root_mcp_output/jets_for_ml.parquet')

# Each row contains jagged arrays (variable number of jets per event)
# You may want to:
# 1. Flatten for per-jet features
# 2. Pad/truncate to fixed number
# 3. Use graph neural networks for variable-length input
```

The data is ready for ML frameworks (PyTorch, TensorFlow, scikit-learn)!"

---

## Scenario 5: Error Recovery

**User**: "Plot the momentum distribution"

### Initial Attempt (Ambiguous)

```json
Tool: compute_histogram
Arguments: {
  "path": "/data/root_files/sample_events.root",
  "tree": "events",
  "branch": "momentum",
  "bins": 50
}

Response:
{
  "error": "branch_not_found",
  "message": "Branch 'momentum' not found in tree 'events'",
  "suggestion": "Use list_branches() to see available branches. Did you mean 'muon_pt'?",
  "available_branches": ["muon_pt", "electron_pt", "jet_pt", "met"]
}
```

### Recovery: List Relevant Branches

```json
Tool: list_branches
Arguments: {
  "path": "/data/root_files/sample_events.root",
  "tree": "events",
  "pattern": "*_pt"
}

Response:
{
  "data": {
    "branches": [
      {"name": "muon_pt", "type": "float32[]"},
      {"name": "electron_pt", "type": "float32[]"},
      {"name": "jet_pt", "type": "float32[]"}
    ]
  }
}
```

### Corrected Request

```json
Tool: compute_histogram
Arguments: {
  "path": "/data/root_files/sample_events.root",
  "tree": "events",
  "branch": "muon_pt",
  "bins": 50,
  "range": [0, 200]
}

[Success - returns histogram]
```

**AI Response to User**:

"I couldn't find a branch called 'momentum'. The file has separate pT branches for different particle types:
- muon_pt
- electron_pt
- jet_pt

I've plotted the **muon pT distribution** (most common choice). Would you like electrons or jets instead?"

---

## Summary: AI Interaction Patterns

These examples show how the ROOT-MCP server enables:

1. **Progressive Discovery**: Start broad (list files) → narrow down (inspect) → detailed (branches)
2. **Error Guidance**: Helpful suggestions when tools fail
3. **Efficiency Checks**: Test selections before expensive operations
4. **Domain Knowledge**: Understand physics conventions and typical workflows
5. **Multi-Step Analysis**: Compose tools to answer complex questions

The declarative tool interface allows AI models to:
- Explore unfamiliar data autonomously
- Validate assumptions before committing to expensive operations
- Receive actionable feedback from errors
- Build complex analyses from simple primitives
