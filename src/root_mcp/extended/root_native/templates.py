"""Pre-built code templates for common ROOT operations.

Templates generate Python/PyROOT code strings that can be passed to
RootCodeExecutor.execute(). Each template function returns a complete,
runnable Python script as a string.
"""

from __future__ import annotations

import json


def rdataframe_histogram(
    file_path: str,
    tree_name: str,
    branch: str,
    bins: int,
    range_min: float,
    range_max: float,
    selection: str | None = None,
    weight: str | None = None,
    output_path: str | None = None,
) -> str:
    """Generate RDataFrame code to compute a 1D histogram.

    Parameters
    ----------
    file_path : str
        Path to the ROOT file.
    tree_name : str
        Name of the TTree.
    branch : str
        Branch to histogram.
    bins : int
        Number of bins.
    range_min, range_max : float
        Histogram range.
    selection : str | None
        Optional cut expression (C++ syntax for RDF Filter).
    weight : str | None
        Optional weight column name.
    output_path : str | None
        If provided, save histogram as PNG to this path.

    Returns
    -------
    str
        Complete Python script.
    """
    lines = [
        "import ROOT",
        "import json",
        "",
        "ROOT.gROOT.SetBatch(True)",
        "",
        f"rdf = ROOT.RDataFrame({tree_name!r}, {file_path!r})",
    ]

    if selection:
        lines.append(f"rdf = rdf.Filter({selection!r})")

    model = f'ROOT.RDF.TH1DModel("h", "{branch}", {bins}, {range_min}, {range_max})'

    if weight:
        lines.append(f"h = rdf.Histo1D({model}, {branch!r}, {weight!r})")
    else:
        lines.append(f"h = rdf.Histo1D({model}, {branch!r})")

    lines.extend(
        [
            "",
            "# Extract histogram data",
            "result = {",
            '    "entries": int(h.GetEntries()),',
            '    "mean": h.GetMean(),',
            '    "std_dev": h.GetStdDev(),',
            '    "underflow": h.GetBinContent(0),',
            '    "overflow": h.GetBinContent(h.GetNbinsX() + 1),',
            '    "bin_contents": [h.GetBinContent(i) for i in range(1, h.GetNbinsX() + 1)],',
            '    "bin_errors": [h.GetBinError(i) for i in range(1, h.GetNbinsX() + 1)],',
            f'    "bin_edges": [{range_min} + i * ({range_max} - {range_min}) / {bins} for i in range({bins} + 1)],',
            "}",
            "print(json.dumps(result))",
        ]
    )

    if output_path:
        lines.extend(
            [
                "",
                "# Save plot",
                'c = ROOT.TCanvas("c", "c", 800, 600)',
                "h.Draw()",
                f"c.SaveAs({output_path!r})",
            ]
        )

    return "\n".join(lines)


def rdataframe_snapshot(
    file_path: str,
    tree_name: str,
    branches: list[str],
    output_path: str,
    output_tree_name: str | None = None,
    selection: str | None = None,
) -> str:
    """Generate RDataFrame code to write a filtered/selected subset to a new ROOT file.

    Parameters
    ----------
    file_path : str
        Input ROOT file path.
    tree_name : str
        Input TTree name.
    branches : list[str]
        Branches to include in output.
    output_path : str
        Output ROOT file path.
    output_tree_name : str | None
        Output tree name (defaults to input tree name).
    selection : str | None
        Optional cut expression.

    Returns
    -------
    str
        Complete Python script.
    """
    out_tree = output_tree_name or tree_name
    branch_vec = "ROOT.std.vector['string']()"
    lines = [
        "import ROOT",
        "import json",
        "",
        f"rdf = ROOT.RDataFrame({tree_name!r}, {file_path!r})",
    ]

    if selection:
        lines.append(f"rdf = rdf.Filter({selection!r})")

    lines.extend(
        [
            "",
            f"branches = {branch_vec}",
        ]
    )
    for b in branches:
        lines.append(f"branches.push_back({b!r})")

    lines.extend(
        [
            "",
            f"rdf.Snapshot({out_tree!r}, {output_path!r}, branches)",
            "",
            "# Report",
            f"rdf_out = ROOT.RDataFrame({out_tree!r}, {output_path!r})",
            "n_entries = rdf_out.Count().GetValue()",
            "result = {",
            f'    "output_file": {output_path!r},',
            f'    "tree_name": {out_tree!r},',
            '    "entries": int(n_entries),',
            f'    "branches": {branches!r},',
            "}",
            "print(json.dumps(result))",
        ]
    )

    return "\n".join(lines)


def tcanvas_plot(
    file_path: str,
    tree_name: str,
    draw_expr: str,
    output_path: str,
    selection: str | None = None,
    title: str | None = None,
    width: int = 800,
    height: int = 600,
) -> str:
    """Generate TTree::Draw + TCanvas code to create a plot.

    Parameters
    ----------
    file_path : str
        Path to the ROOT file.
    tree_name : str
        Name of the TTree.
    draw_expr : str
        TTree::Draw expression (e.g. "px:py", "mass>>h(100,0,200)").
    output_path : str
        Output file path for the plot (png, pdf, svg).
    selection : str | None
        Optional cut expression.
    title : str | None
        Plot title.
    width, height : int
        Canvas dimensions in pixels.

    Returns
    -------
    str
        Complete Python script.
    """
    lines = [
        "import ROOT",
        "import json",
        "",
        "ROOT.gROOT.SetBatch(True)",
        "",
        f"f = ROOT.TFile.Open({file_path!r})",
        f"t = f.Get({tree_name!r})",
        "",
        f'c = ROOT.TCanvas("c", "c", {width}, {height})',
    ]

    sel = selection or ""
    lines.append(f"t.Draw({draw_expr!r}, {sel!r})")

    if title:
        lines.extend(
            [
                "",
                "# Set title",
                f'ROOT.gPad.GetPrimitive("htemp").SetTitle({title!r})',
            ]
        )

    lines.extend(
        [
            "",
            f"c.SaveAs({output_path!r})",
            "",
            "result = {",
            f'    "output_file": {output_path!r},',
            f'    "draw_expr": {draw_expr!r},',
            '    "entries_drawn": int(t.GetSelectedRows()) if t.GetSelectedRows() > 0 else int(t.GetEntries()),',
            "}",
            "print(json.dumps(result))",
            "",
            "f.Close()",
        ]
    )

    return "\n".join(lines)


def roofit_fit(
    file_path: str,
    workspace_name: str,
    model_name: str,
    data_name: str,
    output_path: str | None = None,
) -> str:
    """Generate RooFit code to perform a fit from a workspace.

    Parameters
    ----------
    file_path : str
        Path to ROOT file containing the workspace.
    workspace_name : str
        Name of the RooWorkspace.
    model_name : str
        Name of the PDF model in the workspace.
    data_name : str
        Name of the dataset in the workspace.
    output_path : str | None
        If provided, save fit plot to this path.

    Returns
    -------
    str
        Complete Python script.
    """
    lines = [
        "import ROOT",
        "import json",
        "",
        "ROOT.gROOT.SetBatch(True)",
        "",
        f"f = ROOT.TFile.Open({file_path!r})",
        f"w = f.Get({workspace_name!r})",
        "",
        f"model = w.pdf({model_name!r})",
        f"data = w.data({data_name!r})",
        "",
        "# Perform fit",
        "fit_result = model.fitTo(data, ROOT.RooFit.Save(), ROOT.RooFit.PrintLevel(-1))",
        "",
        "# Extract parameters",
        "params = fit_result.floatParsFinal()",
        "param_dict = {}",
        "for i in range(params.getSize()):",
        "    p = params.at(i)",
        "    param_dict[p.GetName()] = {",
        '        "value": p.getVal(),',
        '        "error": p.getError(),',
        '        "min": p.getMin(),',
        '        "max": p.getMax(),',
        "    }",
        "",
        "result = {",
        '    "status": fit_result.status(),',
        '    "cov_quality": fit_result.covQual(),',
        '    "edm": fit_result.edm(),',
        '    "min_nll": fit_result.minNll(),',
        '    "parameters": param_dict,',
        "}",
        "print(json.dumps(result))",
    ]

    if output_path:
        lines.extend(
            [
                "",
                "# Plot fit result",
                "obs = w.var(model.getObservables(data).first().GetName())",
                "frame = obs.frame()",
                "data.plotOn(frame)",
                "model.plotOn(frame)",
                "",
                'c = ROOT.TCanvas("c", "c", 800, 600)',
                "frame.Draw()",
                f"c.SaveAs({output_path!r})",
            ]
        )

    lines.append("")
    lines.append("f.Close()")

    return "\n".join(lines)


def root_file_write(
    data: dict[str, list[float]],
    output_path: str,
    tree_name: str = "tree",
) -> str:
    """Generate code to write columnar data to a new ROOT file.

    Parameters
    ----------
    data : dict[str, list[float]]
        Column name -> values mapping.
    output_path : str
        Output ROOT file path.
    tree_name : str
        Name of the TTree to create.

    Returns
    -------
    str
        Complete Python script.
    """
    data_json = json.dumps(data)
    lines = [
        "import ROOT",
        "import json",
        "import array",
        "",
        f"data = json.loads({data_json!r})",
        "",
        f'f = ROOT.TFile({output_path!r}, "RECREATE")',
        f"t = ROOT.TTree({tree_name!r}, {tree_name!r})",
        "",
        "# Create branches",
        "buffers = {}",
        "for name in data:",
        '    buffers[name] = array.array("d", [0.0])',
        '    t.Branch(name, buffers[name], f"{name}/D")',
        "",
        "# Fill tree",
        "n_entries = len(next(iter(data.values())))",
        "for i in range(n_entries):",
        "    for name in data:",
        "        buffers[name][0] = data[name][i]",
        "    t.Fill()",
        "",
        "t.Write()",
        "f.Close()",
        "",
        "result = {",
        f'    "output_file": {output_path!r},',
        f'    "tree_name": {tree_name!r},',
        '    "entries": n_entries,',
        '    "branches": list(data.keys()),',
        "}",
        "print(json.dumps(result))",
    ]

    return "\n".join(lines)


def root_macro(
    macro_code: str,
    output_path: str | None = None,
) -> str:
    """Generate code to execute a ROOT C++ macro via gROOT.ProcessLine.

    Parameters
    ----------
    macro_code : str
        C++ code to execute.
    output_path : str | None
        If provided, save any canvas output to this path.

    Returns
    -------
    str
        Complete Python script.
    """
    # For multi-line macros, wrap in braces so ProcessLine handles them
    # as a single compound statement. Single-line macros work as-is.
    macro_lines = macro_code.strip().splitlines()
    if len(macro_lines) > 1:
        # Wrap in { } block for multi-line C++ code
        wrapped = "{ " + " ".join(line.strip() for line in macro_lines) + " }"
    else:
        wrapped = macro_code.strip()

    # Escape for embedding in a Python string
    escaped = wrapped.replace("\\", "\\\\").replace('"', '\\"')

    lines = [
        "import ROOT",
        "import json",
        "",
        "ROOT.gROOT.SetBatch(True)",
        "",
        f'ROOT.gROOT.ProcessLine("{escaped}")',
    ]

    if output_path:
        lines.extend(
            [
                "",
                "# Save canvas if one exists",
                "c = ROOT.gPad.GetCanvas() if ROOT.gPad else None",
                "if c:",
                f"    c.SaveAs({output_path!r})",
            ]
        )

    lines.extend(
        [
            "",
            'result = {"status": "executed"}',
            "print(json.dumps(result))",
        ]
    )

    return "\n".join(lines)
