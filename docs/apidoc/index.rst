Package Reference
=================

Auto-generated reference documentation for all public modules in ``root_mcp``.

ROOT-MCP follows a three-tier package layout:

.. list-table::
   :header-rows: 1

   * - Package
     - Purpose
   * - :mod:`root_mcp.common`
     - Shared utilities — caching, error types, ROOT availability probe
   * - :mod:`root_mcp.core`
     - Pure-Python core: file I/O, TTree readers, basic statistics, core MCP tools
   * - :mod:`root_mcp.extended`
     - Full analysis: histograms, fitting, kinematics, correlations, plotting, native ROOT execution
   * - :mod:`root_mcp.config`
     - Configuration models (Pydantic) and ``load_config`` helpers
   * - :mod:`root_mcp.server`
     - ``ROOTMCPServer`` and ``main()`` entry point

.. toctree::
   :maxdepth: 1

   root_mcp/modules
