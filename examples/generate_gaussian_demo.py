#!/usr/bin/env python3
"""
Generate a demo ROOT file with a Gaussian muon pT distribution.

Designed to demonstrate the following LLM + root-mcp workflow:

  Prompt: "What branches are in this file? Show me the muon pT distribution and fit it with a Gaussian"

  Expected LLM steps:
    1. list_branches      — discovers tree structure
    2. get_branch_stats   — quick summary statistics
    3. fit_histogram      — Gaussian fit on pT
    4. plot_histogram_1d  — saves PNG plot
    5. Summarise results in plain language

Physics motivation
------------------
Muons from Z → μμ decays have pT ≈ mZ/2 ≈ 45 GeV.  Near the Jacobian
peak the spectrum is well described by a Gaussian, making it a clean
textbook example for fitting.

Usage
-----
    python examples/generate_gaussian_demo.py
    python examples/generate_gaussian_demo.py --output data/root_files/muon_gaussian_demo.root
    python examples/generate_gaussian_demo.py --events 20000 --seed 1234
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import uproot

# ---------------------------------------------------------------------------
# Data generation
# ---------------------------------------------------------------------------


def generate_z_mumu_events(n_events: int, rng: np.random.Generator) -> dict:
    """
    Simulate simplified Z → μμ events.

    Each event contains exactly two muons (one μ⁺, one μ⁻) stored as
    flat scalar branches (mu1_*, mu2_*).  This avoids jagged-array
    complexity and works directly with root-mcp's fit_histogram and
    get_branch_stats tools.

    The pT of each muon is drawn from N(45, 8) GeV — the Jacobian peak
    expected from Z → μμ — making it a clean textbook Gaussian.
    """
    # --- muon kinematics ---
    # pT ~ N(45, 8) GeV — Jacobian peak from Z decay
    mu1_pt = rng.normal(loc=45.0, scale=8.0, size=n_events).clip(10.0).astype(np.float32)
    mu2_pt = rng.normal(loc=45.0, scale=8.0, size=n_events).clip(10.0).astype(np.float32)

    mu1_eta = rng.normal(0.0, 1.2, size=n_events).astype(np.float32)
    mu2_eta = rng.normal(0.0, 1.2, size=n_events).astype(np.float32)

    mu1_phi = rng.uniform(-np.pi, np.pi, size=n_events).astype(np.float32)
    # second muon roughly back-to-back in φ
    mu2_phi = (
        (mu1_phi + np.pi + rng.normal(0, 0.3, size=n_events) + np.pi) % (2 * np.pi) - np.pi
    ).astype(np.float32)

    mu1_charge = np.ones(n_events, dtype=np.int32)
    mu2_charge = -np.ones(n_events, dtype=np.int32)

    # --- dimuon invariant mass: Z peak N(91.2, 2.5) GeV ---
    dimuon_mass = rng.normal(91.2, 2.5, size=n_events).clip(70.0, 110.0).astype(np.float32)

    # --- event-level variables ---
    event_number = np.arange(n_events, dtype=np.uint64)
    run_number = np.full(n_events, 400000, dtype=np.uint32)

    # MET: small for Z → μμ (no genuine MET)
    met = rng.exponential(8.0, size=n_events).astype(np.float32)
    met_phi = rng.uniform(-np.pi, np.pi, size=n_events).astype(np.float32)

    return {
        "event_number": event_number,
        "run_number": run_number,
        "dimuon_mass": dimuon_mass,
        "met": met,
        "met_phi": met_phi,
        # leading muon (μ⁺)
        "mu1_pt": mu1_pt,
        "mu1_eta": mu1_eta,
        "mu1_phi": mu1_phi,
        "mu1_charge": mu1_charge,
        # subleading muon (μ⁻)
        "mu2_pt": mu2_pt,
        "mu2_eta": mu2_eta,
        "mu2_phi": mu2_phi,
        "mu2_charge": mu2_charge,
    }


# ---------------------------------------------------------------------------
# File writing
# ---------------------------------------------------------------------------


def write_demo_file(output_path: str, n_events: int, seed: int) -> None:
    rng = np.random.default_rng(seed)
    data = generate_z_mumu_events(n_events, rng)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    with uproot.recreate(str(out)) as f:
        # Main events tree — all flat scalar branches (one value per event)
        f.mktree(
            "events",
            {
                # event-level
                "event_number": np.uint64,
                "run_number": np.uint32,
                "dimuon_mass": np.float32,  # Z → μμ invariant mass
                "met": np.float32,
                "met_phi": np.float32,
                # leading muon (μ⁺)
                "mu1_pt": np.float32,
                "mu1_eta": np.float32,
                "mu1_phi": np.float32,
                "mu1_charge": np.int32,
                # subleading muon (μ⁻)
                "mu2_pt": np.float32,
                "mu2_eta": np.float32,
                "mu2_phi": np.float32,
                "mu2_charge": np.int32,
            },
            title="Z -> mumu candidate events",
        )
        f["events"].extend(data)

        # Small metadata tree
        f.mktree(
            "metadata",
            {"n_events": np.int64, "run_number": np.uint32},
            title="File metadata",
        )
        f["metadata"].extend(
            {
                "n_events": np.array([n_events], dtype=np.int64),
                "run_number": np.array([400000], dtype=np.uint32),
            }
        )

    size_kb = out.stat().st_size / 1024
    print(f"Created: {out}")
    print(f"  events tree : {n_events:,} entries, 13 branches")
    print("  metadata    : 1 entry,  2 branches")
    print(f"  File size   : {size_kb:.1f} kB")
    print()
    print("Branch summary:")
    print("  Event-level : event_number, run_number, dimuon_mass, met, met_phi")
    print("  Leading μ⁺  : mu1_pt, mu1_eta, mu1_phi, mu1_charge")
    print("  Subleading μ⁻: mu2_pt, mu2_eta, mu2_phi, mu2_charge")
    print()
    print("mu1_pt / mu2_pt drawn from  N(mu=45 GeV, sigma=8 GeV)  — clean Gaussian.")
    print("dimuon_mass drawn from      N(mu=91.2 GeV, sigma=2.5 GeV)  — Z peak.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a Gaussian muon pT demo ROOT file for root-mcp",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    default_out = str(
        Path(__file__).parent.parent / "data" / "root_files" / "muon_gaussian_demo.root"
    )
    parser.add_argument(
        "--output",
        "-o",
        default=default_out,
        help=f"Output ROOT file path  (default: {default_out})",
    )
    parser.add_argument(
        "--events",
        "-n",
        type=int,
        default=10_000,
        help="Number of Z → μμ events to generate  (default: 10 000)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility  (default: 42)",
    )
    args = parser.parse_args()

    write_demo_file(args.output, args.events, args.seed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
