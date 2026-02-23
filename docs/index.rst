ROOT-MCP Documentation
======================

**ROOT-MCP** empowers Large Language Models to natively understand and analyse
`CERN ROOT <https://root.cern/>`_ files via the
`Model Context Protocol <https://modelcontextprotocol.io/>`_.

Connect Claude (or any MCP-capable agent) to your ROOT files and ask it to:

- **Inspect** file structures — Trees, Branches, Histograms
- **Analyse** distributions — statistics, histograms, fits
- **Compute** kinematic quantities — invariant mass, 4-vector algebra
- **Visualise** results — 1D/2D plots returned directly to the chat

.. code-block:: bash

   pip install root-mcp

   # Zero-config start — no YAML required
   root-mcp --data-path /path/to/your/data

----

.. toctree::
   :maxdepth: 1
   :caption: User Guide

   user/installation
   user/quickstart
   user/modes
   user/configuration
   user/llm_integration
   user/tools_reference

.. toctree::
   :maxdepth: 1
   :caption: Developer Guide

   developer/dev_setup
   developer/module_overview
   developer/architecture
   developer/contributing

.. toctree::
   :maxdepth: 1
   :caption: API Reference

   apidoc/index

----

.. admonition:: Quick links

   **Users**

   * :doc:`user/installation` — get up and running in minutes
   * :doc:`user/quickstart` — zero-config walkthrough and first queries
   * :doc:`user/tools_reference` — complete tool catalogue (20 tools)
   * :doc:`user/llm_integration` — prompting strategies for Claude and others

   **Contributors**

   * :doc:`developer/dev_setup` — clone, install dev deps, run tests
   * :doc:`developer/module_overview` — annotated package tree
   * :doc:`developer/architecture` — three-tier design overview
   * :doc:`developer/contributing` — PR workflow and code style
