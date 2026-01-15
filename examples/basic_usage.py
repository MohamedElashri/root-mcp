#!/usr/bin/env python3
"""
Basic ROOT-MCP Usage Example
============================

This example demonstrates the core functionality of ROOT-MCP:
- Initializing the server in different modes
- Inspecting ROOT files
- Reading and analyzing data
- Computing statistics and histograms

Run this after creating sample data:
    python examples/create_sample_data.py
    python examples/basic_usage.py
"""

import sys
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from root_mcp.server import ROOTMCPServer
from root_mcp.config import load_config


def main():
    """Demonstrate basic ROOT-MCP usage."""

    print("\n" + "=" * 70)
    print("ROOT-MCP Basic Usage Example")
    print("=" * 70)

    # Check for sample data
    sample_file = Path(__file__).parent.parent / "data" / "root_files" / "sample_events.root"

    if not sample_file.exists():
        print("\nSample data not found!")
        print("Please run: python examples/create_sample_data.py")
        print(f"Expected file: {sample_file}")
        return 1

    # Initialize server
    print("\n1. Initializing ROOT-MCP server...")
    config = load_config("config.yaml")

    # Add sample data directory to allowed roots
    data_dir = str(sample_file.parent)
    if data_dir not in config.security.allowed_roots:
        config.security.allowed_roots.append(data_dir)

    server = ROOTMCPServer(config)

    print(f"   ✓ Server mode: {server.config.server.mode}")
    print(f"   ✓ Extended mode available: {server.histogram_ops is not None}")

    # Inspect file
    print(f"\n2. Inspecting ROOT file: {sample_file.name}")
    file_info = server.discovery_tools.inspect_file(str(sample_file))

    if "error" in file_info:
        print(f"   ❌ Error: {file_info['error']}")
        return 1

    print(f"   ✓ File size: {file_info['data']['size_bytes'] / 1024 / 1024:.2f} MB")
    print(f"   ✓ Trees: {len(file_info['data']['trees'])}")

    for tree in file_info["data"]["trees"]:
        print(f"     - {tree['name']}: {tree['entries']:,} entries")

    # List branches
    print("\n3. Listing branches in 'events' tree...")
    branches = server.discovery_tools.list_branches(str(sample_file), "events")

    if "error" not in branches:
        print(f"   ✓ Total branches: {branches['data']['total_branches']}")
        print("   ✓ Sample branches:")
        for branch in branches["data"]["branches"][:5]:
            jagged = " (jagged)" if branch["is_jagged"] else ""
            print(f"     - {branch['name']}: {branch['type']}{jagged}")

    # Read data
    print("\n4. Reading muon data (first 100 events)...")
    data = server.data_access_tools.read_branches(
        str(sample_file), "events", ["muon_pt", "muon_eta", "muon_phi"], limit=100
    )

    if "error" not in data:
        print(f"   ✓ Entries read: {data['data']['entries']}")
        print(f"   ✓ Branches: {', '.join(data['data']['branches'])}")

    # Compute statistics
    print("\n5. Computing statistics...")
    stats = server.basic_stats.compute_stats(str(sample_file), "events", ["muon_pt", "muon_eta"])

    print("\n   Muon pT:")
    print(f"     - Mean: {stats['muon_pt']['mean']:.2f} GeV")
    print(f"     - Std Dev: {stats['muon_pt']['std']:.2f} GeV")
    print(f"     - Median: {stats['muon_pt']['median']:.2f} GeV")
    print(f"     - Range: [{stats['muon_pt']['min']:.2f}, {stats['muon_pt']['max']:.2f}] GeV")

    print("\n   Muon η:")
    print(f"     - Mean: {stats['muon_eta']['mean']:.3f}")
    print(f"     - Std Dev: {stats['muon_eta']['std']:.3f}")

    # Create histogram (if in extended mode)
    if server.histogram_ops is not None:
        print("\n6. Creating histogram (extended mode)...")
        hist = server.histogram_ops.compute_histogram_1d(
            str(sample_file), "events", "muon_pt", bins=50, range=(0, 200)
        )

        print(f"   ✓ Bins: {len(hist['data']['bin_counts'])}")
        print(f"   ✓ Total entries: {hist['data']['entries']}")
        print(
            f"   ✓ Mean from histogram: {sum(c * (hist['data']['bin_centers'][i]) for i, c in enumerate(hist['data']['bin_counts'])) / hist['data']['entries']:.2f} GeV"
        )
    else:
        print("\n6. Histogram creation (extended mode only)")
        print("    Server is in core mode - histograms not available")
        print("    To enable: Set mode: 'extended' in config.yaml")

    # Validate file
    print("\n7. Validating file integrity...")
    validation = server.file_manager.validate_file(str(sample_file))

    print(f"   ✓ Valid: {validation['valid']}")
    print(f"   ✓ Readable: {validation['readable']}")
    print(f"   ✓ Number of trees: {validation['metadata']['num_trees']}")

    # Summary
    print("\n" + "=" * 70)
    print("✓ Example completed successfully!")
    print("=" * 70)

    print("\nWhat you learned:")
    print("  • How to initialize the ROOT-MCP server")
    print("  • How to inspect ROOT files and list their contents")
    print("  • How to read branch data with limits")
    print("  • How to compute basic statistics")
    print("  • How to create histograms (extended mode)")
    print("  • How to validate file integrity")

    print("\nNext steps:")
    print("  • Explore the integration tests: tests/integration_test.py")
    print("  • Read the documentation: docs/README.md")
    print("  • Try different modes: docs/guides/modes.md")

    return 0


if __name__ == "__main__":
    sys.exit(main())
