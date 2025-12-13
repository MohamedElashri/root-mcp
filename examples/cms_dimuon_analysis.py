import logging
import os

import numpy as np
import awkward as ak
import uproot
import matplotlib.pyplot as plt

# Force IPv4 and disable TLS for XRootD at CERN (fixes timeouts/certs)
os.environ["XRD_NETWORKSTACK"] = "IPv4"
os.environ["XRD_TLSCHECK"] = "0"

# Import ROOT-MCP components
from root_mcp.config import Config, SecurityConfig
from root_mcp.io import FileManager  # , PathValidator
from root_mcp.io.readers import TreeReader

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cms_dimuon")


def main():
    logger.info("Initializing CMS Dimuon Analysis...")

    # CMS Open Data URL (XRootD)
    file_url = "root://eospublic.cern.ch//eos/opendata/cms/derived-data/AOD2NanoAODOutreachTool/Run2012BC_DoubleMuParked_Muons.root"

    # 1. Setup ROOT-MCP Server Components
    # -----------------------------------
    # We configure it to allow remote files
    cwd = os.getcwd()
    config = Config(
        resources=[],  # accessible via direct URL
        security=SecurityConfig(
            allowed_roots=[cwd],
            allow_remote=True,
            allowed_protocols=["file", "root", "http", "https"],
        ),
        features={"enable_remote_files": True},
    )

    file_manager = FileManager(config)
    # path_validator = PathValidator(config)
    # analysis_ops = AnalysisOperations(config, file_manager)
    tree_reader = TreeReader(config, file_manager)
    # tools = AnalysisTools(config, file_manager, path_validator, analysis_ops, tree_reader)

    # 2. Inspect File
    # ---------------
    logger.info(f"Inspecting {file_url}...")
    try:
        # Use TreeReader to get branch info
        branches_info = tree_reader.get_branch_info(file_url, "Events")
        branch_names = [b["name"] for b in branches_info]
        logger.info(f"File structure (first 10 branches): {branch_names[:10]}")
    except Exception as e:
        logger.error(f"Failed to inspect file: {e}")
        # Continue anyway if possible or return
        if "Events" not in str(e):  # If tree doesn't exist, we can't proceed
            pass

    # 3. Perform Dimuon Analysis
    # ---------------------------
    # We do the following:
    # 1. Select events with exactly 2 muons
    # 2. Select events with opposite charge
    # 3. Compute invariant mass using vector math
    # 4. Plot on log-log scale with resonance labels

    logger.info("Reading muon data (this may take a while)...")
    # We use file_manager to get the uproot tree, behaving as the MCP server would
    # For full analysis (61M events), efficient reading is key.
    # We read only necessary branches.
    branches = ["nMuon", "Muon_pt", "Muon_eta", "Muon_phi", "Muon_mass", "Muon_charge"]

    # 3. Perform Dimuon Analysis (Chunked)
    # ---------------------------
    logger.info("Starting chunked analysis...")
    branches = ["nMuon", "Muon_pt", "Muon_eta", "Muon_phi", "Muon_mass", "Muon_charge"]

    # Initialize histogram containers
    bins = 30000
    mass_range = (0.25, 300.0)
    # Get edges
    _, bin_edges = np.histogram([], bins=bins, range=mass_range)
    total_hist_counts = np.zeros(bins, dtype=np.int64)

    # Counters
    total_events = 0
    total_2mu = 0
    total_os = 0

    # Chunk size
    step = 100_000  # 100k events per chunk to avoid timeouts

    import vector

    vector.register_awkward()

    # Iterate
    # Note: uproot.iterate can iterate over multiple files, here just one
    # We use the file_url directly with uproot to leverage its efficient iteration
    try:
        # Limit total events for this example execution to avoid running for hours
        # In a real batch job, we would remove this limit.
        max_events = 1_000_000

        logger.info(f"Iterating over {file_url} with step_size={step}...")

        # Use MCP config/environment if needed (env vars set globally)
        for i, events in enumerate(
            uproot.iterate(f"{file_url}:Events", branches, step_size=step, library="ak")
        ):
            if total_events >= max_events:
                logger.info(f"Reached limit of {max_events} events. Stopping.")
                break

            chunk_size = len(events)
            total_events += chunk_size

            # 1. Filter: exactly 2 muons
            events_2mu = events[events.nMuon == 2]
            n_2mu = len(events_2mu)
            total_2mu += n_2mu

            if n_2mu == 0:
                # logger.info(f"Chunk {i}: 0/{chunk_size} passed 2mu")
                continue

            # 2. Zip
            muons = ak.zip(
                {
                    "pt": events_2mu.Muon_pt,
                    "eta": events_2mu.Muon_eta,
                    "phi": events_2mu.Muon_phi,
                    "mass": events_2mu.Muon_mass,
                    "charge": events_2mu.Muon_charge,
                },
                with_name="Momentum4D",
            )

            # 3. Filter: Opposite Charge
            os_mask = muons[:, 0].charge != muons[:, 1].charge
            dimuons = muons[os_mask]
            n_os = len(dimuons)
            total_os += n_os

            if n_os == 0:
                # logger.info(f"Chunk {i}: 0/{chunk_size} passed OS")
                continue

            # 4. Compute Mass
            mu1 = dimuons[:, 0]
            mu2 = dimuons[:, 1]
            dimuon_system = mu1 + mu2
            mass = dimuon_system.mass

            # Histogramming for this chunk
            counts, _ = np.histogram(mass, bins=bin_edges)
            total_hist_counts += np.array(counts, dtype=np.int64)

            logger.info(f"Chunk {i}: Processed {total_events} events total.")

        logger.info("Processing complete.")
        logger.info(f"Total entries: {total_events}")
        if total_events > 0:
            logger.info(
                f"Events with 2 muons: {total_2mu} (Efficiency: {total_2mu / total_events:.2%})"
            )
            if total_2mu > 0:
                logger.info(
                    f"Events with opposite charge: {total_os} (Efficiency relative to 2mu: {total_os / total_2mu:.2%})"
                )
            else:
                logger.info("No events with 2 muons found.")
        else:
            logger.warning("No events processed.")

        # Use accumulated histogram
        hist = total_hist_counts

        logger.info("Generating plot...")

        # Use matplotlib to generate the plot
        fig, ax = plt.subplots(figsize=(10, 8))

        # Plot histogram (using centers for log plot or stairs)

        # Using step plot basically
        ax.stairs(hist, bin_edges, color="black", linewidth=1)

        # Log scales
        ax.set_xscale("log")
        ax.set_yscale("log")

        # Axis labels
        ax.set_xlabel(r"$m_{\mu\mu}$ (GeV)", fontsize=14)
        ax.set_ylabel(r"$N_{Events}$", fontsize=14)

        # Limits (implied by range)
        ax.set_xlim(mass_range)

        # Grid
        ax.grid(True, which="both", alpha=0.3)

        # Decorations / Labels
        # Translation of ROOT TLatex coordinates
        # (x, y, text)
        labels = [
            (0.55, 3.0e4, r"$\eta$"),
            (0.77, 7.0e4, r"$\rho,\omega$"),
            (1.20, 4.0e4, r"$\phi$"),
            (4.40, 1.0e5, r"$J/\psi$"),
            (4.60, 1.0e4, r"$\psi'$"),
            (12.0, 2.0e4, r"$\Upsilon(1,2,3S)$"),
            (91.0, 1.5e4, r"$Z$"),
        ]

        # Grid
        ax.grid(True, which="both", alpha=0.3)

        # Set Y limits to be safe for log scale and labels
        # Find max count to scale top margin
        max_count = np.max(hist)
        ax.set_ylim(bottom=0.5, top=max_count * 50)  # Generous top margin for labels

        # Decorations / Labels
        # Translation of ROOT TLatex coordinates
        # We need to scale the Y positions because we might have processed fewer events
        # The original labels are for ~61.5M events
        full_stats = 61540413
        y_scale = total_events / full_stats

        # (x, y (full stats), text)
        labels = [
            (0.55, 3.0e4, r"$\eta$"),
            (0.77, 7.0e4, r"$\rho,\omega$"),
            (1.20, 4.0e4, r"$\phi$"),
            (4.40, 1.0e5, r"$J/\psi$"),
            (4.60, 1.0e4, r"$\psi'$"),
            (12.0, 2.0e4, r"$\Upsilon(1,2,3S)$"),
            (91.0, 1.5e4, r"$Z$"),
        ]

        for x, y, text in labels:
            # Scale Y position and ensure it's not below 1
            scaled_y = max(1.1, y * y_scale)
            ax.text(x, scaled_y, text, fontsize=12, ha="center", va="bottom")

        # CMS Label
        # ROOT: 0.10, 0.92 NDC (Normalized Device Coordinates) -> axes fraction
        ax.text(
            0.05,
            0.95,
            "CMS Open Data",
            transform=ax.transAxes,
            fontsize=14,
            fontweight="bold",
            ha="left",
            va="top",
        )

        # Luminosity Label
        # ROOT: 0.90, 0.92 NDC
        ax.text(
            0.95,
            0.95,
            r"$\sqrt{s} = 8$ TeV, $L_{int} = 11.6$ fb$^{-1}$",
            transform=ax.transAxes,
            fontsize=12,
            ha="right",
            va="top",
        )

        output_file = "dimuonSpectrum.pdf"
        logger.info(f"Saving to {output_file}...")
        fig.savefig(output_file)
        plt.close(fig)

        logger.info("Done!")

    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    print("DEBUG: Calling main()")
    main()
