
# ROOT-MCP Examples

This directory contains example scripts demonstrating how to use `root-mcp` for various physics analysis tasks.

## 1. Z Boson Resonance Search (`z_boson_analysis.py`)

A complete High Energy Physics (HEP) analysis example that searches for a Z boson resonance in synthetic data.

**Features:**
- **Data Generation**: Simulates a Gaussian Signal (Z boson) and Exponential Background.
- **Histogramming**: Computes invariant mass histograms.
- **Composite Fitting**: Fits the data with a `Gaussian + Exponential` model.
- **Plotting**: Generates a publication-quality plot with log scale, grid, and units.

**Usage:**

```bash
# From repository root
python examples/z_boson_analysis.py
```

The script will produce a `z_boson_fit.png` file showing the fitted spectrum.

## 2. Creating Sample Data (`create_sample_data.py`)

A utility script to generate sample ROOT files for testing the server.

**Usage:**

```bash
python examples/create_sample_data.py
```
