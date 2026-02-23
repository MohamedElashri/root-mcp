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

Mode selection
--------------

ROOT-MCP starts in **extended mode** by default (full analysis capabilities).
To start in lightweight core mode:

.. code-block:: bash

   root-mcp --data-path /data --mode core

You can switch modes at runtime via the ``switch_mode`` tool without restarting.

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

ROOT-MCP speaks the standard `MCP stdio transport
<https://modelcontextprotocol.io/docs/concepts/transports>`_.
Any MCP-compatible client can use it with the same ``command`` + ``args`` pattern.
Check your client's documentation for the exact JSON key names.

----

First queries
-------------

Once Claude Desktop is running with ROOT-MCP connected, try these prompts:

**List files**

   *"List the ROOT files available to you."*

Claude calls ``list_files`` and returns a table of file names, sizes, and
modification times. No file access happens until you ask.

**Inspect a file structure**

   *"What's in analysis.root? Show me the TTree structure."*

Claude calls ``inspect_file`` and returns a tree of objects — TTrees,
branches, histograms — with their types and sizes.

**Read and summarise branch data**

   *"Read the muon_pt branch from the Events tree and give me basic statistics."*

Claude calls ``read_branches`` followed by ``get_branch_stats``, returning
min, max, mean, standard deviation, and median.

**Compute a histogram with fit**

   *"Compute a histogram of muon_pt with 50 bins between 0 and 200 GeV
   and fit a Gaussian to the peak."*

Claude calls ``compute_histogram`` (extended mode) followed by
``fit_histogram``, returning bin counts, a fitted mean and sigma, and a
summary plot.

**Kinematic calculation**

   *"Compute the invariant mass of the di-muon system using the four
   leading muons."*

Claude calls ``compute_invariant_mass`` with the relevant branch names and
returns a histogram of the invariant mass distribution — the Z peak should
appear around 91 GeV if the data contains Z→μμ events.

**Export for further analysis**

   *"Export the first 10,000 events from the Events tree to a CSV file."*

Claude calls ``export_data`` and writes a ``.csv`` to the server's export
path, then tells you where to find it.

----

Next steps
----------

- :doc:`modes` — understand core vs extended vs native ROOT capabilities
- :doc:`configuration` — full ``config.yaml`` reference
- :doc:`llm_integration` — prompting strategies and advanced LLM workflows
- :doc:`tools_reference` — complete catalogue of all 20 tools and their arguments
