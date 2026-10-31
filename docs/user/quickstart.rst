Quick Start
===========

ROOT-MCP is designed to work in under two minutes with **no configuration file**.
This page walks through the three setup paths and your first analysis query.

----

Zero-config setup
-----------------

Option 1 — ``--data-path`` flag
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Pass the directory containing your ROOT files directly on the command line:

.. code-block:: bash

   root-mcp --data-path /path/to/your/data

Multiple directories are supported:

.. code-block:: bash

   root-mcp --data-path /data/run2024 --data-path /data/simulation

Option 2 — environment variable
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Set once, start anywhere:

.. code-block:: bash

   export ROOT_MCP_DATA_PATH=/path/to/your/data
   root-mcp

On Linux/macOS, colon-separate multiple directories:

.. code-block:: bash

   export ROOT_MCP_DATA_PATH=/data/run2024:/data/simulation

Option 3 — generate a config file
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you want a persistent config with advanced settings:

.. code-block:: bash

   root-mcp init --permissive   # creates config.yaml pre-filled with $PWD
   # edit config.yaml if needed, then:
   root-mcp --config config.yaml

.. warning::

   The permissive local setup is intended for trusted single-user stdio
   sessions. Do not expose it as a shared HTTP service with
   ``security.allowed_roots: []``; central deployments need authentication and
   explicit resource restrictions.

Mode selection
--------------

ROOT-MCP starts in **extended mode** by default (full analysis capabilities).
To start in lightweight core mode:

.. code-block:: bash

   root-mcp --data-path /data --mode core

In local deployments, ``switch_mode`` changes the server-wide tier; refresh
the tool list afterward. Central deployments keep the configured tier fixed.

See :doc:`modes` for full details on what each mode provides.

----

Connecting to Claude Desktop
-----------------------------

Open (or create) your Claude Desktop configuration:

- **macOS**: ``~/Library/Application Support/Claude/claude_desktop_config.json``
- **Windows**: ``%APPDATA%\Claude\claude_desktop_config.json``

Add a ``root-mcp`` entry under ``mcpServers``:

.. code-block:: json

   {
     "mcpServers": {
       "root-mcp": {
         "command": "root-mcp",
         "args": ["--data-path", "/absolute/path/to/your/data"]
       }
     }
   }

.. important::

   Use an **absolute path** in the JSON config. Relative paths are resolved
   against the directory Claude Desktop was launched from, which is often not
   your home directory.

With a persistent config file instead:

.. code-block:: json

   {
     "mcpServers": {
       "root-mcp": {
         "command": "root-mcp",
         "env": {
           "ROOT_MCP_CONFIG": "/absolute/path/to/config.yaml"
         }
       }
     }
   }

Restart Claude Desktop after editing the JSON file.

Connecting to other MCP clients
---------------------------------

ROOT-MCP supports local stdio and authenticated Streamable HTTP. For Codex,
Claude Code, Antigravity, Qwen Code, Pi/OMP, VS Code, Cursor, Zed and other
harnesses, use the client-specific configuration in :doc:`llm_integration`.
Server discovery and client approval behavior vary by client.

----

First queries
-------------

Once your client is connected to ROOT-MCP, try these prompts:

**List files**

   *"List the ROOT files available to you."*

The agent calls ``list_files`` and returns a table of file names, sizes, and
modification times. It uses a configured resource name from ``get_server_info``.

**Inspect a file structure**

   *"What's in analysis.root? Show me the TTree structure."*

The agent calls ``inspect_file`` and returns a tree of objects, TTrees and RNTuples,
branches, histograms — with their types and sizes.

**Read and summarise branch data**

   *"Read the muon_pt branch from the Events tree and give me basic statistics."*

The agent calls ``read_branches`` followed by ``get_branch_stats``, returning
min, max, mean, standard deviation, and median.

**Compute a histogram with fit**

   *"Compute a histogram of muon_pt with 50 bins between 0 and 200 GeV
   and fit a Gaussian to the peak."*

The agent calls ``compute_histogram`` (extended mode) followed by
``fit_histogram``, returning bin counts and fit parameters. A separate
``plot_histogram_1d`` call creates a plot file when requested.

**Kinematic calculation**

   *"Compute the invariant mass of the two muon candidates using their
   momentum and mass branches."*

The agent calls ``compute_invariant_mass`` with the relevant branch names and
returns invariant mass values and summary statistics. Confirm that all input
branches use consistent units before interpreting the result.

**Export for further analysis**

   *"Export muon_pt and muon_eta from the Events tree to selected_muons.csv."*

The agent calls ``export_data`` with explicit branches, ``format: csv`` and
``output_path``. The file is written under the permitted export location;
existing files can be overwritten.

----

Next steps
----------

- :doc:`modes` — understand core vs extended vs native ROOT capabilities
- :doc:`configuration` — full ``config.yaml`` reference
- :doc:`llm_integration` — prompting strategies and advanced LLM workflows
- :doc:`tools_reference` — catalogue of the 17 standard and 3 optional native tools
