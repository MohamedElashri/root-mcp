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

By default, this example runs in INTERACTIVE mode to help you learn.
Use --quiet flag for non-interactive execution.
"""

import sys
import argparse
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from root_mcp.server import ROOTMCPServer
from root_mcp.config import load_config

# Try to import colorama for colored output
try:
    from colorama import Fore, Style, init

    init(autoreset=True)
    HAS_COLOR = True
except ImportError:
    # Fallback if colorama not available
    class Fore:
        GREEN = CYAN = YELLOW = RED = BLUE = MAGENTA = ""

    class Style:
        BRIGHT = RESET_ALL = ""

    HAS_COLOR = False


def wait_for_user(interactive: bool, message: str = "Press Enter to continue..."):
    """Wait for user input if in interactive mode."""
    if interactive:
        try:
            input(f"\n{Fore.CYAN}💡 {message}{Style.RESET_ALL}")
        except (KeyboardInterrupt, EOFError):
            print(f"\n\n{Fore.YELLOW}👋 Exiting...{Style.RESET_ALL}")
            sys.exit(0)


def print_section(title: str, interactive: bool = False):
    """Print a section header."""
    print(f"\n{Fore.CYAN}{Style.BRIGHT}" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + Style.RESET_ALL)
    if interactive:
        print()


def explain(text: str, interactive: bool = False):
    """Print explanatory text if in interactive mode."""
    if interactive:
        print(f"\n{Fore.BLUE}📚 {text}{Style.RESET_ALL}")


def success(text: str):
    """Print success message in green."""
    print(f"{Fore.GREEN}   ✓ {text}{Style.RESET_ALL}")


def info(text: str):
    """Print info message in cyan."""
    print(f"{Fore.CYAN}   ℹ️  {text}{Style.RESET_ALL}")


def warning(text: str):
    """Print warning message in yellow."""
    print(f"{Fore.YELLOW}   ⚠️  {text}{Style.RESET_ALL}")


def error(text: str):
    """Print error message in red."""
    print(f"{Fore.RED}   ❌ {text}{Style.RESET_ALL}")


def main():
    """Demonstrate basic ROOT-MCP usage."""

    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Interactive ROOT-MCP usage example",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="By default, runs in interactive mode to help you learn.",
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true", help="Run in non-interactive mode (no prompts)"
    )
    args = parser.parse_args()
    interactive = not args.quiet

    print_section("ROOT-MCP Basic Usage Example", interactive)

    if interactive:
        print(
            f"\n{Fore.MAGENTA}{Style.BRIGHT}👋 Welcome to the ROOT-MCP interactive tutorial!{Style.RESET_ALL}"
        )
        print(
            f"\n{Fore.WHITE}This example will walk you through the core features of ROOT-MCP.{Style.RESET_ALL}"
        )
        print(f"{Fore.WHITE}You'll learn how to:{Style.RESET_ALL}")
        print(f"{Fore.GREEN}  • Initialize the server{Style.RESET_ALL}")
        print(f"{Fore.GREEN}  • Inspect ROOT files{Style.RESET_ALL}")
        print(f"{Fore.GREEN}  • Read and analyze data{Style.RESET_ALL}")
        print(f"{Fore.GREEN}  • Compute statistics{Style.RESET_ALL}")
        print(f"{Fore.GREEN}  • Create histograms{Style.RESET_ALL}")
        print(f"\n{Fore.YELLOW}💡 Tip: Use --quiet flag to run without prompts.{Style.RESET_ALL}")
        wait_for_user(interactive, "Ready to start? Press Enter...")

    # Check for sample data
    sample_file = Path(__file__).parent.parent / "data" / "root_files" / "sample_events.root"

    if not sample_file.exists():
        warning("Sample data not found!")
        print(f"{Fore.YELLOW}Please run: python examples/create_sample_data.py{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Expected file: {sample_file}{Style.RESET_ALL}")
        return 1

    explain(
        "ROOT-MCP is a Model Context Protocol (MCP) server that lets LLMs interact with ROOT files.\n"
        "It has two modes: CORE (lightweight) and EXTENDED (full physics analysis).",
        interactive,
    )

    # Initialize server
    print_section("Step 1: Server Initialization", interactive)

    explain(
        "First, we need to initialize the ROOT-MCP server.\n"
        "The server loads configuration from config.yaml and sets up all components.",
        interactive,
    )

    print(f"\n{Fore.WHITE}Initializing server...{Style.RESET_ALL}")
    config = load_config("config.yaml")

    # Add sample data directory to allowed roots
    data_dir = str(sample_file.parent)
    if data_dir not in config.security.allowed_roots:
        config.security.allowed_roots.append(data_dir)

    server = ROOTMCPServer(config)

    success(f"Server mode: {Fore.MAGENTA}{server.config.server.mode}{Fore.GREEN}")
    success(
        f"Extended mode available: {Fore.MAGENTA}{server.histogram_ops is not None}{Fore.GREEN}"
    )

    explain(
        f"The server is running in '{server.config.server.mode}' mode.\n"
        "CORE mode: Basic file operations, statistics (no scipy/matplotlib)\n"
        "EXTENDED mode: Full physics analysis with histograms, fitting, plotting",
        interactive,
    )

    wait_for_user(interactive)

    # Inspect file
    print_section("Step 2: File Inspection", interactive)

    explain(
        "Let's inspect a ROOT file to see what's inside.\n"
        "This shows us the file size, compression, and available trees.",
        interactive,
    )

    print(f"\n{Fore.WHITE}Inspecting: {Fore.YELLOW}{sample_file.name}{Style.RESET_ALL}")
    file_info = server.discovery_tools.inspect_file(str(sample_file))

    if "error" in file_info:
        error(f"Error: {file_info['error']}")
        return 1

    success(
        f"File size: {Fore.YELLOW}{file_info['data']['size_bytes'] / 1024 / 1024:.2f} MB{Fore.GREEN}"
    )
    success(f"Trees: {Fore.YELLOW}{len(file_info['data']['trees'])}{Fore.GREEN}")

    for tree in file_info["data"]["trees"]:
        print(
            f"{Fore.WHITE}     - {Fore.CYAN}{tree['name']}{Fore.WHITE}: {Fore.YELLOW}{tree['entries']:,}{Fore.WHITE} entries{Style.RESET_ALL}"
        )

    explain(
        "ROOT files contain 'trees' which are like tables of data.\n"
        "Each tree has multiple 'branches' (columns) with physics variables.",
        interactive,
    )

    wait_for_user(interactive)

    # List branches
    print_section("Step 3: Listing Branches", interactive)

    explain(
        "Now let's see what variables (branches) are available in the 'events' tree.\n"
        "Branches can be simple types (float, int) or jagged arrays (variable length per event).",
        interactive,
    )

    print(
        f"\n{Fore.WHITE}Listing branches in '{Fore.CYAN}events{Fore.WHITE}' tree...{Style.RESET_ALL}"
    )
    branches = server.discovery_tools.list_branches(str(sample_file), "events")

    if "error" not in branches:
        success(f"Total branches: {Fore.YELLOW}{branches['data']['total_branches']}{Fore.GREEN}")
        success("Sample branches:")
        for branch in branches["data"]["branches"][:5]:
            jagged = f" {Fore.MAGENTA}(jagged){Fore.WHITE}" if branch["is_jagged"] else ""
            print(
                f"{Fore.WHITE}     - {Fore.CYAN}{branch['name']}{Fore.WHITE}: {Fore.YELLOW}{branch['type']}{jagged}{Style.RESET_ALL}"
            )

    # Read data
    print_section("Step 4: Reading Data", interactive)

    explain(
        "Let's read some actual data from the file.\n"
        "We'll read muon kinematics (pT, η, φ) for the first 100 events.",
        interactive,
    )

    print(f"\n{Fore.WHITE}Reading muon data (first 100 events)...{Style.RESET_ALL}")
    data = server.data_access_tools.read_branches(
        str(sample_file), "events", ["muon_pt", "muon_eta", "muon_phi"], limit=100
    )

    if "error" not in data:
        success(f"Entries read: {Fore.YELLOW}{data['data']['entries']}{Fore.GREEN}")
        success(f"Branches: {Fore.CYAN}{', '.join(data['data']['branches'])}{Fore.GREEN}")

        explain(
            "The data is returned as awkward arrays, which handle jagged structures efficiently.\n"
            "You can export this data to CSV, JSON, or Parquet for analysis in other tools.",
            interactive,
        )

    wait_for_user(interactive)

    # Compute statistics
    print_section("Step 5: Computing Statistics", interactive)

    explain(
        "ROOT-MCP can compute basic statistics on any branch.\n"
        "This works in both CORE and EXTENDED modes (no scipy required).",
        interactive,
    )

    print(f"\n{Fore.WHITE}Computing statistics for muon variables...{Style.RESET_ALL}")
    stats = server.basic_stats.compute_stats(str(sample_file), "events", ["muon_pt", "muon_eta"])

    print(f"\n{Fore.CYAN}   Muon pT:{Style.RESET_ALL}")
    print(
        f"{Fore.WHITE}     - Mean: {Fore.YELLOW}{stats['muon_pt']['mean']:.2f} GeV{Style.RESET_ALL}"
    )
    print(
        f"{Fore.WHITE}     - Std Dev: {Fore.YELLOW}{stats['muon_pt']['std']:.2f} GeV{Style.RESET_ALL}"
    )
    print(
        f"{Fore.WHITE}     - Median: {Fore.YELLOW}{stats['muon_pt']['median']:.2f} GeV{Style.RESET_ALL}"
    )
    print(
        f"{Fore.WHITE}     - Range: [{Fore.YELLOW}{stats['muon_pt']['min']:.2f}{Fore.WHITE}, {Fore.YELLOW}{stats['muon_pt']['max']:.2f}{Fore.WHITE}] GeV{Style.RESET_ALL}"
    )

    print(f"\n{Fore.CYAN}   Muon η:{Style.RESET_ALL}")
    print(f"{Fore.WHITE}     - Mean: {Fore.YELLOW}{stats['muon_eta']['mean']:.3f}{Style.RESET_ALL}")
    print(
        f"{Fore.WHITE}     - Std Dev: {Fore.YELLOW}{stats['muon_eta']['std']:.3f}{Style.RESET_ALL}"
    )

    # Create histogram (if in extended mode)
    print_section("Step 6: Creating Histograms", interactive)

    if server.histogram_ops is not None:
        explain(
            "In EXTENDED mode, we can create histograms for visualization and analysis.\n"
            "Histograms show the distribution of values and can be fitted with physics models.",
            interactive,
        )

        print(f"\n{Fore.WHITE}Creating histogram of muon pT...{Style.RESET_ALL}")
        hist = server.histogram_ops.compute_histogram_1d(
            str(sample_file), "events", "muon_pt", bins=50, range=(0, 200)
        )

        success(f"Bins: {Fore.YELLOW}{len(hist['data']['bin_counts'])}{Fore.GREEN}")
        success(f"Total entries: {Fore.YELLOW}{hist['data']['entries']}{Fore.GREEN}")
        success(
            f"Mean from histogram: {Fore.YELLOW}{sum(c * (hist['data']['bin_centers'][i]) for i, c in enumerate(hist['data']['bin_counts'])) / hist['data']['entries']:.2f} GeV{Fore.GREEN}"
        )

        explain(
            "Histograms can be fitted with various models (Gaussian, exponential, Crystal Ball, etc.).\n"
            "You can also generate publication-quality plots with matplotlib.",
            interactive,
        )
    else:
        info("Server is in CORE mode - histograms not available")
        print(f"{Fore.CYAN}   To enable: Set mode: 'extended' in config.yaml{Style.RESET_ALL}")

        explain(
            "Histogram creation requires scipy and matplotlib (EXTENDED mode).\n"
            "CORE mode is lighter and faster for basic operations.",
            interactive,
        )

    wait_for_user(interactive)

    # Validate file
    print_section("Step 7: File Validation", interactive)

    explain(
        "Finally, let's validate the file integrity.\n"
        "This checks if the file is readable, has valid trees, and reports any issues.",
        interactive,
    )

    print(f"\n{Fore.WHITE}Validating file...{Style.RESET_ALL}")
    validation = server.file_manager.validate_file(str(sample_file))

    success(f"Valid: {Fore.YELLOW}{validation['valid']}{Fore.GREEN}")
    success(f"Readable: {Fore.YELLOW}{validation['readable']}{Fore.GREEN}")
    success(f"Number of trees: {Fore.YELLOW}{validation['metadata']['num_trees']}{Fore.GREEN}")

    if validation["warnings"]:
        warning("Warnings:")
        for warn in validation["warnings"]:
            print(f"{Fore.YELLOW}     - {warn}{Style.RESET_ALL}")

    explain(
        "File validation is useful for checking data quality in automated pipelines.", interactive
    )

    wait_for_user(interactive)

    # Summary
    print_section("Summary: What You Learned", interactive)

    print(f"\n{Fore.GREEN}{Style.BRIGHT}✓ Example completed successfully!{Style.RESET_ALL}\n")
    print(f"{Fore.WHITE}{Style.BRIGHT}What you learned:{Style.RESET_ALL}")
    print(f"{Fore.GREEN}  ✓ How to initialize the ROOT-MCP server{Style.RESET_ALL}")
    print(f"{Fore.GREEN}  ✓ How to inspect ROOT files and list their contents{Style.RESET_ALL}")
    print(f"{Fore.GREEN}  ✓ How to read branch data with limits{Style.RESET_ALL}")
    print(f"{Fore.GREEN}  ✓ How to compute basic statistics{Style.RESET_ALL}")
    print(f"{Fore.GREEN}  ✓ How to create histograms (extended mode){Style.RESET_ALL}")
    print(f"{Fore.GREEN}  ✓ How to validate file integrity{Style.RESET_ALL}")

    print(f"\n{Fore.BLUE}📚 Next steps:{Style.RESET_ALL}")
    print(
        f"{Fore.CYAN}  • Explore the integration tests: tests/integration_test.py{Style.RESET_ALL}"
    )
    print(f"{Fore.CYAN}  • Read the documentation: docs/README.md{Style.RESET_ALL}")
    print(f"{Fore.CYAN}  • Try different modes: docs/guides/modes.md{Style.RESET_ALL}")
    print(f"{Fore.CYAN}  • Use ROOT-MCP with Claude Desktop or other MCP clients{Style.RESET_ALL}")

    if interactive:
        print(
            f"\n{Fore.YELLOW}💡 Tip: Run with --quiet flag for non-interactive execution.{Style.RESET_ALL}"
        )
        print(f"\n{Fore.MAGENTA}{Style.BRIGHT}👋 Thanks for trying ROOT-MCP!{Style.RESET_ALL}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
