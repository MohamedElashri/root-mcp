"""Tests for ROOT code templates and higher-level tools."""

from __future__ import annotations

import ast
import tempfile


from root_mcp.extended.root_native.templates import (
    rdataframe_histogram,
    rdataframe_snapshot,
    tcanvas_plot,
    roofit_fit,
    root_file_write,
    root_macro,
)
from root_mcp.extended.tools.root_native import RootNativeTools
from root_mcp.config import Config, RootNativeConfig

# ---------------------------------------------------------------------------
# Template generation tests — verify templates produce valid Python
# ---------------------------------------------------------------------------


class TestRDataFrameHistogramTemplate:
    """Tests for rdataframe_histogram template."""

    def test_generates_valid_python(self):
        code = rdataframe_histogram(
            file_path="/data/test.root",
            tree_name="Events",
            branch="pt",
            bins=100,
            range_min=0.0,
            range_max=200.0,
        )
        ast.parse(code)  # Should not raise

    def test_contains_rdataframe(self):
        code = rdataframe_histogram(
            file_path="/data/test.root",
            tree_name="Events",
            branch="pt",
            bins=50,
            range_min=0.0,
            range_max=100.0,
        )
        assert "ROOT.RDataFrame" in code
        assert "Histo1D" in code

    def test_includes_selection(self):
        code = rdataframe_histogram(
            file_path="/data/test.root",
            tree_name="Events",
            branch="pt",
            bins=50,
            range_min=0.0,
            range_max=100.0,
            selection="pt > 20",
        )
        assert "Filter" in code
        assert "pt > 20" in code

    def test_includes_weight(self):
        code = rdataframe_histogram(
            file_path="/data/test.root",
            tree_name="Events",
            branch="pt",
            bins=50,
            range_min=0.0,
            range_max=100.0,
            weight="weight",
        )
        assert "weight" in code

    def test_includes_output_path(self):
        code = rdataframe_histogram(
            file_path="/data/test.root",
            tree_name="Events",
            branch="pt",
            bins=50,
            range_min=0.0,
            range_max=100.0,
            output_path="/tmp/hist.png",
        )
        assert "SaveAs" in code
        assert "/tmp/hist.png" in code
        assert "SetBatch" in code

    def test_no_output_path_no_canvas(self):
        code = rdataframe_histogram(
            file_path="/data/test.root",
            tree_name="Events",
            branch="pt",
            bins=50,
            range_min=0.0,
            range_max=100.0,
        )
        assert "SaveAs" not in code

    def test_outputs_json(self):
        code = rdataframe_histogram(
            file_path="/data/test.root",
            tree_name="Events",
            branch="pt",
            bins=50,
            range_min=0.0,
            range_max=100.0,
        )
        assert "json.dumps" in code
        assert "GetMean" in code
        assert "GetStdDev" in code


class TestRDataFrameSnapshotTemplate:
    """Tests for rdataframe_snapshot template."""

    def test_generates_valid_python(self):
        code = rdataframe_snapshot(
            file_path="/data/test.root",
            tree_name="Events",
            branches=["pt", "eta", "phi"],
            output_path="/tmp/output.root",
        )
        ast.parse(code)

    def test_contains_snapshot(self):
        code = rdataframe_snapshot(
            file_path="/data/test.root",
            tree_name="Events",
            branches=["pt", "eta"],
            output_path="/tmp/output.root",
        )
        assert "Snapshot" in code
        assert "RDataFrame" in code

    def test_includes_selection(self):
        code = rdataframe_snapshot(
            file_path="/data/test.root",
            tree_name="Events",
            branches=["pt"],
            output_path="/tmp/output.root",
            selection="pt > 20",
        )
        assert "Filter" in code

    def test_custom_output_tree_name(self):
        code = rdataframe_snapshot(
            file_path="/data/test.root",
            tree_name="Events",
            branches=["pt"],
            output_path="/tmp/output.root",
            output_tree_name="SelectedEvents",
        )
        assert "SelectedEvents" in code


class TestTCanvasPlotTemplate:
    """Tests for tcanvas_plot template."""

    def test_generates_valid_python(self):
        code = tcanvas_plot(
            file_path="/data/test.root",
            tree_name="Events",
            draw_expr="pt",
            output_path="/tmp/plot.png",
        )
        ast.parse(code)

    def test_contains_draw(self):
        code = tcanvas_plot(
            file_path="/data/test.root",
            tree_name="Events",
            draw_expr="px:py",
            output_path="/tmp/plot.png",
        )
        assert "Draw" in code
        assert "TCanvas" in code
        assert "SaveAs" in code

    def test_includes_selection(self):
        code = tcanvas_plot(
            file_path="/data/test.root",
            tree_name="Events",
            draw_expr="pt",
            output_path="/tmp/plot.png",
            selection="eta < 2.5",
        )
        assert "eta < 2.5" in code

    def test_includes_title(self):
        code = tcanvas_plot(
            file_path="/data/test.root",
            tree_name="Events",
            draw_expr="pt",
            output_path="/tmp/plot.png",
            title="pT distribution",
        )
        assert "pT distribution" in code

    def test_custom_dimensions(self):
        code = tcanvas_plot(
            file_path="/data/test.root",
            tree_name="Events",
            draw_expr="pt",
            output_path="/tmp/plot.png",
            width=1200,
            height=800,
        )
        assert "1200" in code
        assert "800" in code


class TestRooFitFitTemplate:
    """Tests for roofit_fit template."""

    def test_generates_valid_python(self):
        code = roofit_fit(
            file_path="/data/workspace.root",
            workspace_name="w",
            model_name="model",
            data_name="data",
        )
        ast.parse(code)

    def test_contains_roofit_calls(self):
        code = roofit_fit(
            file_path="/data/workspace.root",
            workspace_name="w",
            model_name="model",
            data_name="data",
        )
        assert "fitTo" in code
        assert "RooFit" in code
        assert "floatParsFinal" in code

    def test_includes_output_path(self):
        code = roofit_fit(
            file_path="/data/workspace.root",
            workspace_name="w",
            model_name="model",
            data_name="data",
            output_path="/tmp/fit.png",
        )
        assert "SaveAs" in code
        assert "/tmp/fit.png" in code
        assert "plotOn" in code

    def test_outputs_json(self):
        code = roofit_fit(
            file_path="/data/workspace.root",
            workspace_name="w",
            model_name="model",
            data_name="data",
        )
        assert "json.dumps" in code
        assert "min_nll" in code
        assert "parameters" in code


class TestRootFileWriteTemplate:
    """Tests for root_file_write template."""

    def test_generates_valid_python(self):
        code = root_file_write(
            data={"x": [1.0, 2.0, 3.0], "y": [4.0, 5.0, 6.0]},
            output_path="/tmp/output.root",
        )
        ast.parse(code)

    def test_contains_tree_creation(self):
        code = root_file_write(
            data={"x": [1.0, 2.0]},
            output_path="/tmp/output.root",
        )
        assert "TTree" in code
        assert "TFile" in code
        assert "Branch" in code
        assert "Fill" in code
        assert "Write" in code

    def test_custom_tree_name(self):
        code = root_file_write(
            data={"x": [1.0]},
            output_path="/tmp/output.root",
            tree_name="MyTree",
        )
        assert "MyTree" in code

    def test_outputs_json(self):
        code = root_file_write(
            data={"x": [1.0, 2.0, 3.0]},
            output_path="/tmp/output.root",
        )
        assert "json.dumps" in code


class TestRootMacroTemplate:
    """Tests for root_macro template."""

    def test_generates_valid_python(self):
        code = root_macro(macro_code='cout << "hello" << endl;')
        ast.parse(code)

    def test_contains_process_line(self):
        code = root_macro(macro_code='TH1F h("h","h",100,-5,5);')
        assert "ProcessLine" in code

    def test_includes_output_path(self):
        code = root_macro(
            macro_code='TH1F h("h","h",100,-5,5); h.FillRandom("gaus",10000); h.Draw();',
            output_path="/tmp/macro.png",
        )
        assert "SaveAs" in code
        assert "/tmp/macro.png" in code

    def test_escapes_special_chars(self):
        code = root_macro(macro_code='cout << "value = " << x << "\\n";')
        ast.parse(code)  # Should still be valid Python

    def test_batch_mode(self):
        code = root_macro(macro_code="int x = 42;")
        assert "SetBatch" in code


# ---------------------------------------------------------------------------
# Higher-level tool tests
# ---------------------------------------------------------------------------


class TestRunRDataFrameTool:
    """Tests for the run_rdataframe convenience tool."""

    def setup_method(self):
        self.work_dir = tempfile.mkdtemp(prefix="test_rdf_")
        self.config = Config(
            root_native=RootNativeConfig(
                execution_timeout=10,
                working_directory=self.work_dir,
            )
        )
        self.tools = RootNativeTools(config=self.config)

    def test_generates_and_executes_code(self):
        """run_rdataframe should generate code and attempt execution."""
        # Without ROOT installed, the code will fail at import ROOT,
        # but we can verify the tool generates and runs code
        result = self.tools.run_rdataframe(
            file_path="/nonexistent.root",
            tree_name="Events",
            branch="pt",
            bins=50,
            range_min=0.0,
            range_max=100.0,
            timeout=5,
        )
        # Should either succeed (if ROOT installed) or error (if not)
        assert result["status"] in ("success", "error")
        assert "execution_time_seconds" in result

    def test_skips_validation(self):
        """Template-generated code should skip AST validation."""
        # The template imports json which could trigger warnings,
        # but skip_validation=True means no validation result
        result = self.tools.run_rdataframe(
            file_path="/nonexistent.root",
            tree_name="Events",
            branch="pt",
            bins=50,
            range_min=0.0,
            range_max=100.0,
            timeout=5,
        )
        # No "warnings" key since validation was skipped
        assert "warnings" not in result


class TestRunRootMacroTool:
    """Tests for the run_root_macro convenience tool."""

    def setup_method(self):
        self.work_dir = tempfile.mkdtemp(prefix="test_macro_")
        self.config = Config(
            root_native=RootNativeConfig(
                execution_timeout=10,
                working_directory=self.work_dir,
            )
        )
        self.tools = RootNativeTools(config=self.config)

    def test_generates_and_executes_code(self):
        """run_root_macro should generate code and attempt execution."""
        result = self.tools.run_root_macro(
            macro_code="int x = 42;",
            timeout=5,
        )
        assert result["status"] in ("success", "error")
        assert "execution_time_seconds" in result

    def test_skips_validation(self):
        """Template-generated code should skip AST validation."""
        result = self.tools.run_root_macro(
            macro_code="int x = 1;",
            timeout=5,
        )
        assert "warnings" not in result


class TestToolSchemas:
    """Tests for tool schema registration."""

    def test_root_native_tools_includes_all_three(self):
        """_get_root_native_tools should return all 3 tools."""
        config = Config()
        from root_mcp.server import ROOTMCPServer

        server = ROOTMCPServer(config)
        tools = server._get_root_native_tools()
        names = [t.name for t in tools]
        assert "run_root_code" in names
        assert "run_rdataframe" in names
        assert "run_root_macro" in names

    def test_run_rdataframe_schema_has_required_fields(self):
        config = Config()
        from root_mcp.server import ROOTMCPServer

        server = ROOTMCPServer(config)
        tools = server._get_root_native_tools()
        rdf_tool = next(t for t in tools if t.name == "run_rdataframe")
        required = rdf_tool.inputSchema["required"]
        assert "file_path" in required
        assert "tree_name" in required
        assert "branch" in required
        assert "bins" in required
        assert "range_min" in required
        assert "range_max" in required

    def test_run_root_macro_schema_has_required_fields(self):
        config = Config()
        from root_mcp.server import ROOTMCPServer

        server = ROOTMCPServer(config)
        tools = server._get_root_native_tools()
        macro_tool = next(t for t in tools if t.name == "run_root_macro")
        required = macro_tool.inputSchema["required"]
        assert "macro_code" in required
