"""
Z Boson Resonance Analysis Example
==================================

This example demonstrates how to use ROOT-MCP as a library to perform a typical High Energy Physics analysis:
searching for a Z boson resonance in an invariant mass spectrum.

It showcases:
1.  Generating synthetic data (Signal + Background).
2.  Interfacing with the ROOT-MCP server components programmatically.
3.  Defining derived physics variables.
4.  Fitting a Composite Model (Gaussian Signal + Exponential Background).
5.  Visualizing the results with publication-quality plots.

"""

import asyncio
import logging
import os
import numpy as np
import uproot

# Import ROOT-MCP components
from root_mcp.config import Config, ResourceConfig, SecurityConfig
from root_mcp.io import FileManager, PathValidator
from root_mcp.analysis import AnalysisOperations
from root_mcp.tools import AnalysisTools
from root_mcp.io.readers import TreeReader

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("z_analysis")


async def main():
    logger.info("Initializing Z Boson Analysis...")
    filename = "data/z_boson_data.root"
    os.makedirs("data", exist_ok=True)

    # 1. Generate Synthetic Data
    # --------------------------
    # We simulate an invariant mass spectrum with:
    # - Signal: Z boson peak (Gaussian approx) at 91.2 GeV, width ~2.5 GeV
    # - Background: Exponentially falling spectrum (Combinatorial background)

    n_sig = 5000
    n_bkg = 10000

    # Signal
    m_z = 91.2
    width_z = 2.5
    mass_sig = np.random.normal(m_z, width_z, n_sig)

    # Background (e.g. DY, QCD)
    # Exp decay from 50 GeV to 150 GeV
    # f(x) ~ exp(-x/tau)
    mass_bkg = np.random.exponential(scale=30, size=n_bkg) + 50
    mass_bkg = mass_bkg[mass_bkg < 150]  # Cut off high tail

    all_mass = np.concatenate([mass_sig, mass_bkg])

    # Save to ROOT file
    with uproot.recreate(filename) as f:
        f["events"] = {"mass": all_mass}

    logger.info(f"Generated {len(all_mass)} events to {filename}")

    # 2. Setup ROOT-MCP Server
    # ------------------------
    cwd = os.getcwd()
    config = Config(
        resources=[ResourceConfig(name="data", uri=f"file://{cwd}/data", path=f"{cwd}/data")],
        security=SecurityConfig(allowed_roots=[cwd]),
    )

    file_manager = FileManager(config)
    path_validator = PathValidator(config)
    analysis_ops = AnalysisOperations(config, file_manager)
    tree_reader = TreeReader(config, file_manager)
    tools = AnalysisTools(config, file_manager, path_validator, analysis_ops, tree_reader)

    file_path = os.path.abspath(filename)

    # 3. Perform Analysis
    # -------------------

    # Define range for analysis
    mass_range = (60.0, 120.0)
    bins = 60  # 1 GeV bins

    # A. Compute Histogram
    logger.info("Computing invariant mass histogram...")
    hist_result = tools.compute_histogram(
        path=file_path, tree="events", branch="mass", bins=bins, range=mass_range
    )

    if "error" in hist_result:
        logger.error(f"Error computing histogram: {hist_result['message']}")
        return

    # B. Fit Model
    # We fit a Composite Model: Gaussian (Signal) + Exponential (Background)
    # The tool returns parameter names like "gaussian_0_amp", "exponential_1_decay", etc.
    # or takes custom prefixes if we configure dicts.

    logger.info("Fitting Composite Model (Gaussian + Exponential)...")

    # Initial guesses:
    # 1. Gaussian Amp ~ n_sig / (sqrt(2pi)*sigma) * bin_width
    #    bin_width = 1.0. sigma=2.5. n_sig=5000. -> ~ 800
    # 2. Mean = 91.0
    # 3. Sigma = 2.5
    # 4. Exp Amp ~ n_bkg... let's say 200
    # 5. Decay = 30

    initial_guess = [800.0, 91.0, 2.5, 500.0, 30.0]

    fit_model = ["gaussian", "exponential"]

    fit_result = tools.fit_histogram(data=hist_result, model=fit_model, initial_guess=initial_guess)

    if "error" in fit_result:
        logger.error(f"Fit failed: {fit_result['message']}")
        # Fallback to plot data only
        plot_result = tools.generate_plot(
            hist_result, options={"title": "Z Boson Search (Fit Failed)"}
        )
    else:
        logger.info("Fit converged!")
        logger.info(f"Chi2/NDF: {fit_result['chi2']:.1f} / {fit_result['ndof']}")

        # Extract parameters
        params = fit_result["parameters"]
        names = fit_result["parameter_names"]
        for n, p, e in zip(names, params, fit_result["errors"]):
            logger.info(f"  {n}: {p:.3f} +/- {e:.3f}")

        # C. Generate Plot
        logger.info("Generating plot...")
        plot_options = {
            "title": "Invariant Mass Spectrum (Z -> ll)",
            "xlabel": "Invariant Mass",
            "ylabel": "Events / 1 GeV",
            "unit": "GeV",
            "grid": True,
            "log_y": False,
        }

        plot_result = tools.generate_plot(
            data=hist_result, fit_data=fit_result, options=plot_options
        )

        # Save plot to file
        import base64

        with open("z_boson_fit.pdf", "wb") as f:
            f.write(base64.b64decode(plot_result["image_data"]))

        logger.info("Plot saved to z_boson_fit.pdf")

    # Cleanup
    if os.path.exists(filename):
        os.remove(filename)
    if os.path.exists("data"):
        try:
            os.rmdir("data")
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(main())
