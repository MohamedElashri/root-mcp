#!/usr/bin/env python3
"""
Create sample ROOT files for testing and demonstration.

This script creates realistic HEP-style ROOT files using uproot.
"""

import numpy as np
import uproot
from pathlib import Path


def create_simple_ttree(output_path: str, num_events: int = 10_000) -> None:
    """
    Create a simple ROOT file with a TTree containing physics-like data.

    Args:
        output_path: Where to save the ROOT file
        num_events: Number of events to generate
    """
    print(f"Creating ROOT file: {output_path}")
    print(f"Generating {num_events:,} events...")

    # Generate fake physics data
    np.random.seed(42)

    # Event-level variables (one value per event)
    event_number = np.arange(num_events, dtype=np.uint64)
    run_number = np.full(num_events, 12345, dtype=np.uint32)
    met = np.random.exponential(30, size=num_events).astype(np.float32)
    met_phi = np.random.uniform(-np.pi, np.pi, size=num_events).astype(np.float32)

    # Muon variables (jagged arrays - variable number per event)
    muon_counts = np.random.poisson(1.5, size=num_events)  # Average 1.5 muons per event
    muon_pt = []
    muon_eta = []
    muon_phi = []
    muon_charge = []

    for n_muons in muon_counts:
        if n_muons > 0:
            # Generate muon kinematics
            pt = np.random.exponential(30, size=n_muons) + 10  # pT > 10 GeV
            eta = np.random.normal(0, 1.5, size=n_muons)
            phi = np.random.uniform(-np.pi, np.pi, size=n_muons)
            charge = np.random.choice([-1, 1], size=n_muons)

            muon_pt.append(pt.astype(np.float32))
            muon_eta.append(eta.astype(np.float32))
            muon_phi.append(phi.astype(np.float32))
            muon_charge.append(charge.astype(np.int32))
        else:
            # Empty event (no muons)
            muon_pt.append(np.array([], dtype=np.float32))
            muon_eta.append(np.array([], dtype=np.float32))
            muon_phi.append(np.array([], dtype=np.float32))
            muon_charge.append(np.array([], dtype=np.int32))

    # Electron variables (jagged)
    electron_counts = np.random.poisson(1.0, size=num_events)
    electron_pt = []
    electron_eta = []
    electron_phi = []

    for n_electrons in electron_counts:
        if n_electrons > 0:
            pt = np.random.exponential(40, size=n_electrons) + 15
            eta = np.random.normal(0, 1.2, size=n_electrons)
            phi = np.random.uniform(-np.pi, np.pi, size=n_electrons)

            electron_pt.append(pt.astype(np.float32))
            electron_eta.append(eta.astype(np.float32))
            electron_phi.append(phi.astype(np.float32))
        else:
            electron_pt.append(np.array([], dtype=np.float32))
            electron_eta.append(np.array([], dtype=np.float32))
            electron_phi.append(np.array([], dtype=np.float32))

    # Jet variables (jagged)
    jet_counts = np.random.poisson(3.0, size=num_events)
    jet_pt = []
    jet_eta = []
    jet_phi = []
    jet_btag = []

    for n_jets in jet_counts:
        if n_jets > 0:
            pt = np.random.exponential(50, size=n_jets) + 20
            eta = np.random.normal(0, 2.0, size=n_jets)
            phi = np.random.uniform(-np.pi, np.pi, size=n_jets)
            btag = np.random.uniform(0, 1, size=n_jets)  # b-tagging score

            jet_pt.append(pt.astype(np.float32))
            jet_eta.append(eta.astype(np.float32))
            jet_phi.append(phi.astype(np.float32))
            jet_btag.append(btag.astype(np.float32))
        else:
            jet_pt.append(np.array([], dtype=np.float32))
            jet_eta.append(np.array([], dtype=np.float32))
            jet_phi.append(np.array([], dtype=np.float32))
            jet_btag.append(np.array([], dtype=np.float32))

    # Create ROOT file with uproot
    output_path_obj = Path(output_path)
    output_path_obj.parent.mkdir(parents=True, exist_ok=True)

    with uproot.recreate(output_path) as file:
        # Create TTree using mktree (for uproot 5.7.0+ compatibility)
        file.mktree("events", {
            # Event-level variables
            "event_number": np.uint64,
            "run_number": np.uint32,
            "met": np.float32,
            "met_phi": np.float32,
            # Muon variables (jagged) - use awkward array types
            "muon_pt": "var * float32",
            "muon_eta": "var * float32",
            "muon_phi": "var * float32",
            "muon_charge": "var * int32",
            # Electron variables (jagged)
            "electron_pt": "var * float32",
            "electron_eta": "var * float32",
            "electron_phi": "var * float32",
            # Jet variables (jagged)
            "jet_pt": "var * float32",
            "jet_eta": "var * float32",
            "jet_phi": "var * float32",
            "jet_btag": "var * float32",
        })

        # Extend the tree with data
        file["events"].extend({
            "event_number": event_number,
            "run_number": run_number,
            "met": met,
            "met_phi": met_phi,
            "muon_pt": muon_pt,
            "muon_eta": muon_eta,
            "muon_phi": muon_phi,
            "muon_charge": muon_charge,
            "electron_pt": electron_pt,
            "electron_eta": electron_eta,
            "electron_phi": electron_phi,
            "jet_pt": jet_pt,
            "jet_eta": jet_eta,
            "jet_phi": jet_phi,
            "jet_btag": jet_btag,
        })

        # Create metadata tree
        file.mktree("metadata", {
            "total_events": np.int64,
            "run_number": np.uint32,
        })

        file["metadata"].extend({
            "total_events": np.array([num_events], dtype=np.int64),
            "run_number": np.array([12345], dtype=np.uint32),
        })

    print(f"✓ Created: {output_path}")
    print(f"  - events tree: {num_events:,} entries, 16 branches")
    print(f"  - metadata tree: 1 entry, 2 branches")
    print(f"  - File size: {output_path_obj.stat().st_size / 1024 / 1024:.2f} MB")


def create_histogram_file(output_path: str) -> None:
    """
    Create a ROOT file with histograms.

    Args:
        output_path: Where to save the ROOT file
    """
    print(f"\nCreating ROOT file with histograms: {output_path}")

    # Generate data for histograms
    np.random.seed(42)

    # Create 1D histogram data
    pt_data = np.random.exponential(30, size=100_000) + 10
    eta_data = np.random.normal(0, 1.5, size=100_000)

    # Histogram bins
    pt_bins = 100
    pt_range = (0, 200)
    eta_bins = 50
    eta_range = (-5, 5)

    # Compute histograms
    pt_counts, pt_edges = np.histogram(pt_data, bins=pt_bins, range=pt_range)
    eta_counts, eta_edges = np.histogram(eta_data, bins=eta_bins, range=eta_range)

    # 2D histogram
    counts_2d, eta_edges_2d, phi_edges_2d = np.histogram2d(
        np.random.normal(0, 1.5, size=50_000),
        np.random.uniform(-np.pi, np.pi, size=50_000),
        bins=[50, 50],
        range=[[-5, 5], [-np.pi, np.pi]]
    )

    output_path_obj = Path(output_path)
    output_path_obj.parent.mkdir(parents=True, exist_ok=True)

    with uproot.recreate(output_path) as file:
        # Write 1D histograms
        file["h_muon_pt"] = (pt_counts, pt_edges)
        file["h_muon_eta"] = (eta_counts, eta_edges)

        # Write 2D histogram
        file["h_eta_phi"] = (counts_2d, eta_edges_2d, phi_edges_2d)

        # Add a cutflow histogram
        cutflow_labels = [
            "All events",
            "Trigger",
            "≥1 lepton",
            "≥2 jets",
            "MET > 20",
            "Final selection"
        ]
        cutflow_counts = np.array([100000, 85000, 45000, 23000, 12000, 8500], dtype=np.float64)
        cutflow_edges = np.arange(len(cutflow_counts) + 1, dtype=np.float64)

        file["cutflow"] = (cutflow_counts, cutflow_edges)

    print(f"✓ Created: {output_path}")
    print(f"  - h_muon_pt: 1D histogram, {pt_bins} bins")
    print(f"  - h_muon_eta: 1D histogram, {eta_bins} bins")
    print(f"  - h_eta_phi: 2D histogram, 50x50 bins")
    print(f"  - cutflow: 1D histogram, {len(cutflow_counts)} bins")


def create_multiple_trees_file(output_path: str) -> None:
    """
    Create a ROOT file with multiple TTrees and directories.

    Args:
        output_path: Where to save the ROOT file
    """
    print(f"\nCreating complex ROOT file: {output_path}")

    np.random.seed(42)

    output_path_obj = Path(output_path)
    output_path_obj.parent.mkdir(parents=True, exist_ok=True)

    with uproot.recreate(output_path) as file:
        # Main analysis tree
        n_events = 5000

        # Create signal tree
        file.mktree("analysis/signal", {
            "mass": np.float32,
            "pt": np.float32,
            "event_weight": np.float32,
        })
        file["analysis/signal"].extend({
            "mass": np.random.normal(125, 5, size=n_events).astype(np.float32),
            "pt": np.random.exponential(40, size=n_events).astype(np.float32) + 20,
            "event_weight": np.random.normal(1.0, 0.1, size=n_events).astype(np.float32),
        })

        # Background tree
        file.mktree("analysis/background", {
            "mass": np.float32,
            "pt": np.float32,
            "event_weight": np.float32,
        })
        file["analysis/background"].extend({
            "mass": np.random.normal(100, 20, size=n_events).astype(np.float32),
            "pt": np.random.exponential(35, size=n_events).astype(np.float32) + 15,
            "event_weight": np.random.normal(1.0, 0.15, size=n_events).astype(np.float32),
        })

        # Systematics tree
        file.mktree("systematics/nominal", {
            "yield": np.float32,
            "uncertainty": np.float32,
        })
        file["systematics/nominal"].extend({
            "yield": np.array([8500.0], dtype=np.float32),
            "uncertainty": np.array([450.0], dtype=np.float32),
        })

    print(f"✓ Created: {output_path}")
    print(f"  - analysis/signal tree: {n_events:,} entries")
    print(f"  - analysis/background tree: {n_events:,} entries")
    print(f"  - systematics/nominal tree: 1 entry")


def main():
    """Create all sample ROOT files."""
    print("=" * 60)
    print("Creating Sample ROOT Files for ROOT-MCP Demo")
    print("=" * 60)

    # Create output directory
    output_dir = Path("data/root_files")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create various sample files
    create_simple_ttree(
        output_path=str(output_dir / "sample_events.root"),
        num_events=10_000
    )

    create_simple_ttree(
        output_path=str(output_dir / "large_sample.root"),
        num_events=100_000
    )

    create_histogram_file(
        output_path=str(output_dir / "histograms.root")
    )

    create_multiple_trees_file(
        output_path=str(output_dir / "analysis.root")
    )

    print("\n" + "=" * 60)
    print("✓ All sample files created successfully!")
    print("=" * 60)
    print(f"\nFiles are in: {output_dir.absolute()}")
    print("\nYou can now:")
    print("1. Configure ROOT-MCP to use this directory")
    print("2. Start the server: root-mcp")
    print("3. Test with list_files, inspect_file, etc.")
    print("\nExample config.yaml:")
    print(f"""
resources:
  - name: "local_data"
    uri: "file://{output_dir.absolute()}"
    description: "Sample ROOT files"
    allowed_patterns: ["*.root"]

security:
  allowed_roots:
    - "{output_dir.absolute()}"
""")


if __name__ == "__main__":
    main()
