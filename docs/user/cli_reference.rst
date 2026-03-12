ROOT CLI Reference
==================

.. module:: root_cli

**root-cli** is a token-efficient command-line interface for analyzing CERN ROOT files.
It provides significant token savings compared to the MCP JSON protocol by using human-readable
commands and output instead of verbose JSON structures.

Quick Start
-----------

Set your data path once:

.. code-block:: bash

   export ROOT_MCP_DATA_PATH=/path/to/your/data

Or specify per command:

.. code-block:: bash

   root-cli -d /path/to/data <command>

All commands support ``--json`` flag for machine-readable output.

Command Overview
----------------

File Operations
~~~~~~~~~~~~~~~

.. cmdoption:: ls [pattern]

   List ROOT files in the data directory.

   .. option:: -l, --limit

      Maximum files to list (default: 100)

   **Example:**

   .. code-block:: bash

      root-cli ls
      root-cli ls "run_*.root" --limit 10

.. cmdoption:: inspect <file.root>

   Inspect ROOT file structure (TTrees, branches, histograms).

   **Example:**

   .. code-block:: bash

      root-cli inspect /data/sample.root

.. cmdoption:: branches <file.root> <tree>

   List branches in a TTree with type information.

   .. option:: -p, --pattern

      Glob pattern for branch names

   .. option:: -l, --limit

      Maximum branches to list (default: 100)

   .. option:: -s, --stats

      Compute statistics (slower)

   **Example:**

   .. code-block:: bash

      root-cli branches /data/sample.root events
      root-cli branches /data/sample.root events --pattern "muon_*"

.. cmdoption:: validate <file.root>

   Validate ROOT file integrity and readability.

   **Example:**

   .. code-block:: bash

      root-cli validate /data/sample.root

Data Access
~~~~~~~~~~~

.. cmdoption:: read <file.root> <tree> <branches...>

   Read branch data from TTree with optional selection.

   .. option:: -s, --selection

      Cut expression (C++ syntax, e.g., ``"pt > 20 && abs(eta) < 2.4"``)

   .. option:: -l, --limit

      Maximum entries to read

   .. option:: -o, --offset

      Skip first N entries

   .. option:: --flatten

      Flatten jagged arrays

   .. option:: -d, --defines

      Derived variables (``name=expr``)

   **Example:**

   .. code-block:: bash

      root-cli read /data/sample.root events met muon_pt
      root-cli read /data/sample.root events met --selection "met > 50" --limit 1000

.. cmdoption:: stats <file.root> <tree> <branches...>

   Compute statistics (mean, std, min, max, median) for branches.

   .. option:: -s, --selection

      Cut expression

   **Example:**

   .. code-block:: bash

      root-cli stats /data/sample.root events met muon_pt jet1_pt

.. cmdoption:: sample <file.root> <tree>

   Get a sample from a TTree.

   .. option:: --size

      Sample size (default: 100)

   .. option:: --method

      Sampling method: ``first`` or ``random``

   .. option:: --seed

      Random seed (for random sampling)

   **Example:**

   .. code-block:: bash

      root-cli sample /data/sample.root events --size 50 --method random

.. cmdoption:: export <file.root> <tree> <branches...> -o <output>

   Export branch data to CSV, JSON, or Parquet.

   .. option:: --format

      Output format: ``csv``, ``json``, or ``parquet`` (default: csv)

   .. option:: -s, --selection

      Cut expression

   .. option:: -l, --limit

      Maximum entries to export

   **Example:**

   .. code-block:: bash

      root-cli export /data/sample.root events met pt -o data.csv
      root-cli export /data/sample.root events met -o data.parquet --format parquet

Histogram Analysis
~~~~~~~~~~~~~~~~~~

.. cmdoption:: histogram <file.root> <tree> <branch>

   Create 1D histogram with optional fit.

   .. option:: -b, --bins

      Number of bins (default: 100)

   .. option:: -r, --range MIN MAX

      Histogram range

   .. option:: -s, --selection

      Cut expression

   .. option:: -f, --fit

      Fit model: ``gaussian``, ``exponential``, ``polynomial``, ``crystal_ball``

   .. option:: --fit-range MIN MAX

      Fit range

   **Example:**

   .. code-block:: bash

      root-cli histogram /data/sample.root events met --bins 50
      root-cli histogram /data/sample.root events dimuon_mass --fit gaussian --fit-range 80 100

.. cmdoption:: histogram2d <file.root> <tree> <x_branch> <y_branch>

   Create 2D histogram for correlation studies.

   .. option:: --xbins

      Number of X bins (default: 50)

   .. option:: --ybins

      Number of Y bins (default: 50)

   .. option:: --xrange

      X axis range

   .. option:: --yrange

      Y axis range

   **Example:**

   .. code-block:: bash

      root-cli histogram2d /data/sample.root events met met_phi

.. cmdoption:: fit <histogram.json> <model>

   Fit a mathematical model to histogram data.

   .. option:: --fit-range MIN MAX

      Fit range

   .. option:: -i, --initial-params

      Initial parameters (``name=value``)

   **Example:**

   .. code-block:: bash

      root-cli fit /tmp/root_mcp/met_hist.json gaussian

.. cmdoption:: hist-arithmetic <operation> <hist1.json> <hist2.json>

   Perform bin-by-bin histogram arithmetic.

   **Operations:** ``add``, ``subtract``, ``multiply``, ``divide``, ``asymmetry``

   **Example:**

   .. code-block:: bash

      root-cli hist-arithmetic divide /tmp/data.json /tmp/mc.json

Statistical Analysis
~~~~~~~~~~~~~~~~~~~~

.. cmdoption:: correlation <file.root> <tree> <branches...>

   Compute correlation matrix between branches.

   .. option:: --method

      Correlation method: ``pearson`` or ``spearman`` (default: pearson)

   **Example:**

   .. code-block:: bash

      root-cli correlation /data/sample.root events met jet1_pt jet2_pt

Kinematics
~~~~~~~~~~

.. cmdoption:: invariant-mass <file.root> <tree>

   Compute invariant mass from particle 4-vectors.

   .. option:: --pt

      PT branches (can specify multiple: ``--pt mu1_pt --pt mu2_pt``)

   .. option:: --eta

      Eta branches

   .. option:: --phi

      Phi branches

   .. option:: --mass

      Mass branches (optional)

   .. option:: -s, --selection

      Cut expression

   .. option:: -l, --limit

      Maximum entries

   **Example:**

   .. code-block:: bash

      root-cli invariant-mass /data/sample.root events \
        --pt mu1_pt mu2_pt \
        --eta mu1_eta mu2_eta \
        --phi mu1_phi mu2_phi

Visualization
~~~~~~~~~~~~~

.. cmdoption:: plot1d <histogram.json> -o <output.png>

   Create a 1D histogram plot.

   .. option:: -t, --title

      Plot title

   .. option:: -x, --xlabel

      X-axis label

   .. option:: -y, --ylabel

      Y-axis label (default: Events)

   .. option:: --log-y

      Logarithmic Y axis

   .. option:: --style

      Plot style: ``default``, ``publication``, ``presentation``

   **Example:**

   .. code-block:: bash

      root-cli plot1d /tmp/root_mcp/met_hist.json -o met.png \
        --title "MET Distribution" --xlabel "MET (GeV)"

.. cmdoption:: plot2d <histogram2d.json> -o <output.png>

   Create a 2D histogram plot.

   .. option:: -t, --title

      Plot title

   .. option:: --colormap

      Matplotlib colormap (default: viridis)

   .. option:: --log-z

      Logarithmic color scale

   **Example:**

   .. code-block:: bash

      root-cli plot2d /tmp/root_mcp/corr_hist2d.json -o corr.png \
        --colormap inferno

Utility
~~~~~~~

.. cmdoption:: info

   Show CLI information and available commands.

   .. option:: --json

      Output in JSON format

   **Example:**

   .. code-block:: bash

      root-cli info
      root-cli info --json

Common Workflows
----------------

Exploratory Analysis
~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # 1. List available files
   root-cli ls

   # 2. Inspect file structure
   root-cli inspect /data/sample.root

   # 3. Check available branches
   root-cli branches /data/sample.root events --pattern "muon_*"

   # 4. Get basic statistics
   root-cli stats /data/sample.root events met muon_pt

Histogram with Fit
~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # 1. Create histogram with fit
   root-cli histogram /data/sample.root events dimuon_mass \
     --bins 100 --range 80 100 --fit gaussian --fit-range 85 95

   # 2. Create publication plot
   root-cli plot1d /tmp/root_mcp/dimuon_mass_hist.json \
     -o dimuon_mass.png --title "Dimuon Mass" --style publication

Data Export
~~~~~~~~~~~

.. code-block:: bash

   # 1. Read data with selection
   root-cli read /data/sample.root events met muon_pt \
     --selection "met > 50 && muon_pt > 20"

   # 2. Export to Parquet
   root-cli export /data/sample.root events met muon_pt \
     -o selected.parquet --format parquet --selection "met > 50"

Token Efficiency
----------------

The CLI provides significant token savings compared to MCP JSON protocol by using
human-readable commands and output instead of verbose JSON structures.

For a typical analysis session, this translates to **thousands of tokens saved**.

See Also
--------

* :doc:`tools_reference` — MCP server tool reference
* `Skill File <https://github.com/MohamedElashri/root-mcp/tree/main/docs/skills/root-cli.md>`_ — Complete CLI documentation
