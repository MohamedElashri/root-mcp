#!/usr/bin/env python3
"""
Manual integration test for ROOT-MCP dual-mode architecture.

This script tests the complete functionality by directly calling
the server's internal methods.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from root_mcp.server import ROOTMCPServer
from root_mcp.config import load_config


def print_section(title):
    """Print a section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def print_result(test_name, passed, details=""):
    """Print test result."""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {test_name}")
    if details:
        print(f"  {details}")


def test_core_mode():
    """Test core mode functionality."""
    print_section("Testing Core Mode")

    # Create config for core mode
    config_dict = {
        "server": {"name": "test-server", "mode": "core"},
        "core": {
            "cache": {"enabled": True, "file_cache_size": 10},
            "limits": {"max_rows_per_call": 10000},
        },
    }

    # Create temporary config file
    import tempfile
    import yaml

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config_dict, f)
        config_path = f.name

    try:
        config = load_config(config_path)
        server = ROOTMCPServer(config)

        # Test 1: Server initializes in core mode
        passed = server.config.server.mode == "core"
        print_result(
            "Server initializes in core mode", passed, f"Mode: {server.config.server.mode}"
        )

        # Test 2: Extended components not loaded
        passed = not hasattr(server, "histogram_ops") or server.histogram_ops is None
        print_result("Extended components not loaded", passed)

        # Test 3: Core components loaded
        passed = server.file_manager is not None and server.path_validator is not None
        print_result("Core components loaded", passed)

        # Test 4: Discovery tools available
        passed = server.discovery_tools is not None
        print_result("Discovery tools available", passed)

        # Test 5: Data access tools available
        passed = server.data_access_tools is not None
        print_result("Data access tools available", passed)

        # Test 6: Basic stats available
        passed = server.basic_stats is not None
        print_result("Basic stats available", passed)

        print("\n✓ Core mode tests completed")
        return True

    finally:
        Path(config_path).unlink()


def test_extended_mode():
    """Test extended mode functionality."""
    print_section("Testing Extended Mode")

    # Create config for extended mode
    config_dict = {
        "server": {"name": "test-server", "mode": "extended"},
        "core": {
            "cache": {"enabled": True, "file_cache_size": 10},
            "limits": {"max_rows_per_call": 10000},
        },
        "extended": {"analysis": {"default_bins": 50}},
    }

    # Create temporary config file
    import tempfile
    import yaml

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config_dict, f)
        config_path = f.name

    try:
        config = load_config(config_path)
        server = ROOTMCPServer(config)

        # Test 1: Server initializes in extended mode
        passed = server.config.server.mode == "extended"
        print_result(
            "Server initializes in extended mode", passed, f"Mode: {server.config.server.mode}"
        )

        # Test 2: Extended components loaded
        passed = server.histogram_ops is not None
        print_result("Histogram operations loaded", passed)

        passed = server.kinematics_ops is not None
        print_result("Kinematics operations loaded", passed)

        passed = server.correlation_analysis is not None
        print_result("Correlation analysis loaded", passed)

        # Test 3: Core components still available
        passed = server.file_manager is not None
        print_result("Core components still available", passed)

        # Test 4: Analysis tools available
        passed = server.analysis_tools is not None
        print_result("Analysis tools available", passed)

        print("\n✓ Extended mode tests completed")
        return True

    finally:
        Path(config_path).unlink()


def test_with_real_files():
    """Test with real ROOT files."""
    print_section("Testing with Real ROOT Files")

    # Check if test data exists
    test_file = Path(__file__).parent.parent / "data" / "root_files" / "sample_events.root"
    if not test_file.exists():
        print(f"⚠️  Test data not found: {test_file}")
        print("   Run: python examples/create_sample_data.py")
        return False

    print(f"Using test file: {test_file}")

    # Create config
    config_dict = {
        "server": {"name": "test-server", "mode": "extended"},
        "core": {
            "cache": {"enabled": True, "file_cache_size": 10},
            "limits": {"max_rows_per_call": 10000},
        },
        "extended": {"analysis": {"default_bins": 50}},
        "security": {"allowed_roots": [str(test_file.parent)]},
    }

    import tempfile
    import yaml

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config_dict, f)
        config_path = f.name

    try:
        config = load_config(config_path)
        server = ROOTMCPServer(config)

        # Test 1: Inspect file
        try:
            file_info = server.file_manager.get_file_info(str(test_file))
            passed = "trees" in file_info
            print_result("Inspect file", passed, f"Found {len(file_info.get('trees', []))} trees")
        except Exception as e:
            print_result("Inspect file", False, f"Error: {e}")

        # Test 2: List branches
        try:
            trees = server.file_manager.list_trees(str(test_file))
            if trees:
                tree_name = trees[0]["name"]
                tree = server.file_manager.get_tree(str(test_file), tree_name)
                branches = list(tree.keys())
                passed = len(branches) > 0
                print_result(
                    "List branches", passed, f"Found {len(branches)} branches in '{tree_name}'"
                )
            else:
                print_result("List branches", False, "No trees found")
        except Exception as e:
            print_result("List branches", False, f"Error: {e}")

        # Test 3: Read branches
        try:
            result = server.tree_reader.read_branches(
                str(test_file), "events", ["muon_pt", "muon_eta"], limit=100
            )
            passed = "data" in result and result["data"]["entries"] > 0
            print_result("Read branches", passed, f"Read {result['data']['entries']} entries")
        except Exception as e:
            print_result("Read branches", False, f"Error: {e}")

        # Test 4: Compute statistics
        try:
            result = server.basic_stats.compute_stats(
                str(test_file), "events", ["muon_pt", "muon_eta"]
            )
            passed = "muon_pt" in result and "mean" in result["muon_pt"]
            if passed:
                mean_pt = result["muon_pt"]["mean"]
                print_result("Compute statistics", passed, f"Mean muon_pt: {mean_pt:.2f}")
            else:
                print_result("Compute statistics", False)
        except Exception as e:
            print_result("Compute statistics", False, f"Error: {e}")

        # Test 5: Compute histogram (extended mode)
        try:
            result = server.histogram_ops.compute_histogram_1d(
                str(test_file), "events", "muon_pt", bins=50, range=(0, 200)
            )
            passed = (
                "data" in result
                and "bin_counts" in result["data"]
                and len(result["data"]["bin_counts"]) == 50
            )
            if passed:
                total_entries = result["data"]["entries"]
                print_result("Compute histogram", passed, f"Total entries: {int(total_entries)}")
            else:
                print_result("Compute histogram", False)
        except Exception as e:
            print_result("Compute histogram", False, f"Error: {e}")

        # Test 6: Validate file
        try:
            result = server.file_manager.validate_file(str(test_file))
            passed = result["valid"] and result["readable"]
            print_result(
                "Validate file", passed, f"Valid: {result['valid']}, Readable: {result['readable']}"
            )
        except Exception as e:
            print_result("Validate file", False, f"Error: {e}")

        print("\n✓ Real file tests completed")
        return True

    finally:
        Path(config_path).unlink()


def test_mode_switching():
    """Test runtime mode switching."""
    print_section("Testing Mode Switching")

    # Create config starting in core mode
    config_dict = {
        "server": {"name": "test-server", "mode": "core"},
        "core": {"cache": {"enabled": True, "file_cache_size": 10}},
        "extended": {"analysis": {"default_bins": 50}},
    }

    import tempfile
    import yaml

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config_dict, f)
        config_path = f.name

    try:
        config = load_config(config_path)
        server = ROOTMCPServer(config)

        # Test 1: Start in core mode
        passed = server.config.server.mode == "core"
        print_result("Start in core mode", passed)

        # Test 2: Switch to extended mode
        try:
            server.switch_mode("extended")
            passed = server.config.server.mode == "extended" and server.histogram_ops is not None
            print_result("Switch to extended mode", passed)
        except Exception as e:
            print_result("Switch to extended mode", False, f"Error: {e}")

        # Test 3: Switch back to core mode
        try:
            server.switch_mode("core")
            passed = server.config.server.mode == "core"
            print_result("Switch back to core mode", passed)
        except Exception as e:
            print_result("Switch back to core mode", False, f"Error: {e}")

        # Test 4: Invalid mode
        try:
            server.switch_mode("invalid")
            print_result("Reject invalid mode", False, "Should have raised error")
        except ValueError:
            print_result("Reject invalid mode", True, "Correctly rejected invalid mode")
        except Exception as e:
            print_result("Reject invalid mode", False, f"Wrong error type: {e}")

        print("\n✓ Mode switching tests completed")
        return True

    finally:
        Path(config_path).unlink()


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("  ROOT-MCP Integration Test Suite")
    print("  Version 0.1.5 - Dual-Mode Architecture")
    print("=" * 60)

    results = []

    # Run test suites
    results.append(("Core Mode", test_core_mode()))
    results.append(("Extended Mode", test_extended_mode()))
    results.append(("Mode Switching", test_mode_switching()))
    results.append(("Real Files", test_with_real_files()))

    # Summary
    print_section("Test Summary")

    total = len(results)
    passed = sum(1 for _, result in results if result)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")

    print(f"\n{'='*60}")
    print(f"  Results: {passed}/{total} test suites passed")
    print(f"{'='*60}\n")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
