"""Analysis commands for root-cli - histograms, fitting, kinematics."""

import json
import click
from pathlib import Path


@click.command()
@click.argument("root_file", type=click.Path(exists=True))
@click.argument("tree_name")
@click.argument("branch")
@click.option("--bins", "-b", default=100, help="Number of bins")
@click.option("--range", "-r", "rng", nargs=2, type=float, help="Range [min max]")
@click.option("--selection", "-s", help="Cut expression")
@click.option("--weights", "-w", help="Weight branch")
@click.option("--fit", "-f", help="Fit model (gaussian, exponential, polynomial, crystal_ball)")
@click.option("--fit-range", "fit_rng", nargs=2, type=float, help="Fit range [min max]")
@click.option("--defines", "-d", multiple=True, help="Derived variables (name=expr)")
@click.pass_context
def histogram(
    ctx, root_file, tree_name, branch, bins, rng, selection, weights, fit, fit_rng, defines
):
    """Create 1D histogram with optional fit."""
    from root_mcp.extended.tools.analysis import AnalysisTools

    # Parse defines
    defines_dict = {}
    for item in defines:
        if "=" in item:
            name, expr = item.split("=", 1)
            defines_dict[name.strip()] = expr.strip()

    config = ctx.obj["config"]
    analysis = AnalysisTools(
        config,
        ctx.obj["file_manager"],
        ctx.obj["path_validator"],
        ctx.obj["analysis_ops"],
        ctx.obj["tree_reader"],
    )

    result = analysis.compute_histogram(
        str(root_file),
        tree_name,
        branch,
        bins=bins,
        range=rng,
        selection=selection,
        weights=weights,
        defines=defines_dict if defines_dict else None,
    )

    if "error" in result:
        click.echo(f"Error: {result['message']}", err=True)
        ctx.exit(1)

    # Apply fit if requested
    if fit and "error" not in result:
        from root_mcp.extended.analysis.fitting import fit_histogram

        # Pass the full result dict to fit_histogram
        fit_result = fit_histogram(data=result, model=fit)

        if "error" not in fit_result:
            result["data"]["fit"] = fit_result.get("data", {})

    if ctx.obj.get("json_output"):
        click.echo(json.dumps(result, indent=2, default=str))
    else:
        data = result.get("data", {})
        click.echo(f"Histogram: {branch} in {tree_name}")
        click.echo(f"File: {root_file} ({data.get('entries', 0):,} entries)")
        if rng:
            click.echo(f"Range: {rng[0]}-{rng[1]}, {bins} bins")

        click.echo("\nStatistics:")
        click.echo(f"  mean:  {data.get('mean', 0):.3f}")
        click.echo(f"  std:   {data.get('std', 0):.3f}")
        click.echo(f"  min:   {data.get('min', 0):.3f}")
        click.echo(f"  max:   {data.get('max', 0):.3f}")

        if "fit" in data:
            fit_data = data["fit"]
            click.echo(f"\n{fit} fit:")
            for param, value in fit_data.get("parameters", {}).items():
                err = fit_data.get("errors", {}).get(param, 0)
                click.echo(f"  {param:<12}: {value:.4f} ± {err:.4f}")
            chi2 = fit_data.get("chi2", 0)
            ndof = fit_data.get("ndof", 1)
            click.echo(f"  χ²/ndof: {chi2:.1f}/{ndof} = {fit_data.get('chi2_ndof', 0):.2f}")

        # Save JSON
        output_file = Path("/tmp/root_mcp") / f"{branch}_hist.json"
        output_file.parent.mkdir(exist_ok=True)
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2, default=str)
        click.echo(f"\nJSON: {output_file}")


@click.command()
@click.argument("root_file", type=click.Path(exists=True))
@click.argument("tree_name")
@click.argument("x_branch")
@click.argument("y_branch")
@click.option("--xbins", default=50, help="Number of bins in X")
@click.option("--ybins", default=50, help="Number of bins in Y")
@click.option("--xrange", "x_rng", nargs=2, type=float, help="X range [min max]")
@click.option("--yrange", "y_rng", nargs=2, type=float, help="Y range [min max]")
@click.option("--selection", "-s", help="Cut expression")
@click.option("--defines", "-d", multiple=True, help="Derived variables (name=expr)")
@click.pass_context
def histogram2d(
    ctx, root_file, tree_name, x_branch, y_branch, xbins, ybins, x_rng, y_rng, selection, defines
):
    """Create 2D histogram."""
    from root_mcp.extended.tools.analysis import AnalysisTools

    # Parse defines
    defines_dict = {}
    for item in defines:
        if "=" in item:
            name, expr = item.split("=", 1)
            defines_dict[name.strip()] = expr.strip()

    config = ctx.obj["config"]
    analysis = AnalysisTools(
        config,
        ctx.obj["file_manager"],
        ctx.obj["path_validator"],
        ctx.obj["analysis_ops"],
        ctx.obj["tree_reader"],
    )

    result = analysis.compute_histogram_2d(
        str(root_file),
        tree_name,
        x_branch=x_branch,
        y_branch=y_branch,
        x_bins=xbins,
        y_bins=ybins,
        x_range=x_rng,
        y_range=y_rng,
        selection=selection,
        defines=defines_dict if defines_dict else None,
    )

    if "error" in result:
        click.echo(f"Error: {result['message']}", err=True)
        ctx.exit(1)

    if ctx.obj.get("json_output"):
        click.echo(json.dumps(result, indent=2, default=str))
    else:
        data = result.get("data", {})
        click.echo(f"2D Histogram: {x_branch} vs {y_branch}")
        click.echo(f"Tree: {tree_name} in {root_file}")
        click.echo(f"Bins: {xbins} x {ybins}")
        click.echo(f"Total entries: {data.get('total_entries', 0):,}")

        if x_rng:
            click.echo(f"X range: {x_rng[0]} - {x_rng[1]}")
        if y_rng:
            click.echo(f"Y range: {y_rng[0]} - {y_rng[1]}")

        # Save JSON
        output_file = Path("/tmp/root_mcp") / f"{x_branch}_vs_{y_branch}_hist2d.json"
        output_file.parent.mkdir(exist_ok=True)
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2, default=str)
        click.echo(f"\nJSON: {output_file}")


@click.command()
@click.argument("histogram_json", type=click.Path(exists=True))
@click.argument("model")
@click.option("--fit-range", "fit_rng", nargs=2, type=float, help="Fit range [min max]")
@click.option("--initial-params", "-i", multiple=True, help="Initial parameters (name=value)")
@click.pass_context
def fit(ctx, histogram_json, model, fit_rng, initial_params):
    """Fit a histogram model."""
    from root_mcp.extended.analysis.fitting import fit_histogram

    # Load histogram data
    with open(histogram_json, "r") as f:
        hist_data = json.load(f)

    # Parse initial parameters
    initial_params_dict = {}
    for item in initial_params:
        if "=" in item:
            name, value = item.split("=", 1)
            try:
                initial_params_dict[name.strip()] = float(value.strip())
            except ValueError:
                pass

    # Prepare data dict for fit_histogram
    data_dict = {"data": hist_data} if "bin_edges" not in hist_data else hist_data

    result = fit_histogram(data=data_dict, model=model)

    if "error" in result:
        click.echo(f"Error: {result['message']}", err=True)
        ctx.exit(1)

    if ctx.obj.get("json_output"):
        click.echo(json.dumps(result, indent=2, default=str))
    else:
        fit_data = result.get("data", {})
        click.echo(f"Fit model: {model}")
        click.echo(f"Source: {histogram_json}")

        click.echo("\nFit parameters:")
        for param, value in fit_data.get("parameters", {}).items():
            err = fit_data.get("errors", {}).get(param, 0)
            click.echo(f"  {param:<12}: {value:.4f} ± {err:.4f}")

        chi2 = fit_data.get("chi2", 0)
        ndof = fit_data.get("ndof", 1)
        click.echo("\nFit quality:")
        click.echo(f"  χ²/ndof: {chi2:.1f}/{ndof} = {fit_data.get('chi2_ndof', 0):.2f}")
        click.echo(f"  Success: {fit_data.get('success', False)}")

        # Save JSON
        output_file = Path("/tmp/root_mcp") / "fit_results.json"
        output_file.parent.mkdir(exist_ok=True)
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2, default=str)
        click.echo(f"\nJSON: {output_file}")


@click.command()
@click.argument("root_file", type=click.Path(exists=True))
@click.argument("tree_name")
@click.option("--pt", "pt_branches", multiple=True, required=True, help="PT branches")
@click.option("--eta", "eta_branches", multiple=True, required=True, help="Eta branches")
@click.option("--phi", "phi_branches", multiple=True, required=True, help="Phi branches")
@click.option("--mass", "mass_branches", multiple=True, help="Mass branches (optional)")
@click.option("--selection", "-s", help="Cut expression")
@click.option("--limit", "-l", type=int, help="Max entries")
@click.pass_context
def invariant_mass(
    ctx,
    root_file,
    tree_name,
    pt_branches,
    eta_branches,
    phi_branches,
    mass_branches,
    selection,
    limit,
):
    """Compute invariant mass from particle 4-vectors."""
    from root_mcp.extended.analysis.kinematics import KinematicsOperations
    import numpy as np

    config = ctx.obj["config"]
    kinematics = KinematicsOperations(config, ctx.obj["file_manager"])

    # Use the existing compute_invariant_mass method
    result = kinematics.compute_invariant_mass(
        path=str(root_file),
        tree_name=tree_name,
        pt_branches=list(pt_branches),
        eta_branches=list(eta_branches),
        phi_branches=list(phi_branches),
        mass_branches=list(mass_branches) if mass_branches else None,
        selection=selection,
    )

    if ctx.obj.get("json_output"):
        click.echo(json.dumps(result, indent=2, default=str))
    else:
        # Result is already the data dict
        click.echo("Invariant mass computed")
        click.echo(f"Tree: {tree_name} in {root_file}")

        inv_mass = result.get("invariant_mass", [])
        if inv_mass:
            arr = np.array(inv_mass)
            click.echo("\nStatistics:")
            click.echo(f"  Entries: {len(arr):,}")
            click.echo(f"  Mean:    {np.mean(arr):.3f}")
            click.echo(f"  Std:     {np.std(arr):.3f}")
            click.echo(f"  Min:     {np.min(arr):.3f}")
            click.echo(f"  Max:     {np.max(arr):.3f}")
            click.echo(f"  Median:  {np.median(arr):.3f}")

        # Save JSON
        output_file = Path("/tmp/root_mcp") / "invariant_mass.json"
        output_file.parent.mkdir(exist_ok=True)
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2, default=str)
        click.echo(f"\nJSON: {output_file}")


@click.command()
@click.argument("root_file", type=click.Path(exists=True))
@click.argument("tree_name")
@click.argument("branches", nargs=-1, required=True)
@click.option(
    "--method",
    default="pearson",
    type=click.Choice(["pearson", "spearman"]),
    help="Correlation method",
)
@click.option("--selection", "-s", help="Cut expression")
@click.pass_context
def correlation(ctx, root_file, tree_name, branches, method, selection):
    """Compute correlation matrix between branches."""
    from root_mcp.extended.analysis.correlations import CorrelationAnalysis
    import awkward as ak
    import numpy as np
    from scipy import stats

    config = ctx.obj["config"]
    corr_analysis = CorrelationAnalysis(config, ctx.obj["file_manager"])

    if len(branches) < 2:
        click.echo("Error: Need at least 2 branches for correlation", err=True)
        ctx.exit(1)

    # Compute pairwise correlations
    corr_matrix = []
    p_values = []

    for i, branch_x in enumerate(branches):
        row = []
        p_row = []
        for j, branch_y in enumerate(branches):
            if i == j:
                row.append(1.0)
                p_row.append(0.0)
            elif j < i:
                # Use symmetric property
                row.append(corr_matrix[j][i])
                p_row.append(p_values[j][i])
            else:
                # Compute correlation
                tree = ctx.obj["file_manager"].get_tree(str(root_file), tree_name)
                arrays = tree.arrays(filter_name=[branch_x, branch_y], cut=selection, library="ak")

                data_x = (
                    ak.flatten(arrays[branch_x])
                    if corr_analysis._is_jagged(arrays[branch_x])
                    else arrays[branch_x]
                )
                data_y = (
                    ak.flatten(arrays[branch_y])
                    if corr_analysis._is_jagged(arrays[branch_y])
                    else arrays[branch_y]
                )

                x_np = ak.to_numpy(data_x)
                y_np = ak.to_numpy(data_y)

                mask = np.isfinite(x_np) & np.isfinite(y_np)
                x_np = x_np[mask]
                y_np = y_np[mask]

                if len(x_np) < 2:
                    row.append(float("nan"))
                    p_row.append(float("nan"))
                elif method == "pearson":
                    corr_coef, p_value = stats.pearsonr(x_np, y_np)
                    row.append(float(corr_coef))
                    p_row.append(float(p_value))
                else:
                    corr_coef, p_value = stats.spearmanr(x_np, y_np)
                    row.append(float(corr_coef))
                    p_row.append(float(p_value))

        corr_matrix.append(row)
        p_values.append(p_row)

    result = {
        "data": {
            "correlation_matrix": corr_matrix,
            "p_values": p_values,
            "branches": list(branches),
            "method": method,
        },
        "metadata": {"operation": "correlation", "selection": selection},
    }

    if ctx.obj.get("json_output"):
        click.echo(json.dumps(result, indent=2, default=str))
    else:
        data = result.get("data", {})
        click.echo(f"{method.capitalize()} correlation matrix")
        click.echo(f"Tree: {tree_name} in {root_file}")
        click.echo(f"Branches: {', '.join(branches)}\n")

        corr_matrix = data.get("correlation_matrix", [])
        if corr_matrix:
            # Print header
            click.echo(f"{'':<15}", nl=False)
            for b in branches:
                click.echo(f"{b:>12}", nl=False)
            click.echo()

            # Print matrix
            for i, branch in enumerate(branches):
                click.echo(f"{branch:<15}", nl=False)
                for j in range(len(branches)):
                    if i < len(corr_matrix) and j < len(corr_matrix[i]):
                        val = corr_matrix[i][j]
                        if np.isnan(val):
                            click.echo(f"{'NaN':>12}", nl=False)
                        else:
                            click.echo(f"{val:>12.3f}", nl=False)
                click.echo()

        # Save JSON
        output_file = Path("/tmp/root_mcp") / "correlation_matrix.json"
        output_file.parent.mkdir(exist_ok=True)
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2, default=str)
        click.echo(f"\nJSON: {output_file}")
