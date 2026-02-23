Module Overview
===============

Annotated map of the ``root_mcp`` package tree.  Each sub-package is linked to
its auto-generated API reference page.

----

Package tree
------------

.. code-block:: text

   src/root_mcp/
   │
   ├── __init__.py           — public API: Config, load_config, __version__
   ├── config.py             — Pydantic configuration models + CLI/env helpers
   ├── server.py             — ROOTMCPServer class and main() entry point
   │
   ├── common/               — shared utilities (no analysis deps)
   │   ├── cache.py          — generic TTL/LRU caching helpers
   │   ├── errors.py         — custom exception hierarchy
   │   ├── root_availability.py  — subprocess-based ROOT probe + feature detection
   │   └── utils.py          — misc helpers (path normalisation, JSON serialisation)
   │
   ├── core/                 — pure-Python core (uproot, awkward, numpy, pandas only)
   │   ├── io/
   │   │   ├── file_manager.py   — LRU file-handle cache + uproot open/close
   │   │   ├── readers.py        — TreeReader, HistogramReader (TTree + TH*)
   │   │   ├── exporters.py      — DataExporter (JSON, CSV, Parquet)
   │   │   └── validators.py     — PathValidator (security, protocol checks)
   │   ├── operations/
   │   │   └── basic_stats.py    — min/max/mean/std/median for any numeric branch
   │   └── tools/
   │       ├── discovery.py      — DiscoveryTools (list_files, inspect_file, …)
   │       └── data_access.py    — DataAccessTools (read_branches, get_branch_stats, …)
   │
   └── extended/             — full analysis (scipy + matplotlib required)
       ├── analysis/
       │   ├── histograms.py     — HistogramOperations (1D/2D, weighted, arithmetic)
       │   ├── fitting.py        — HistogramFitter (Gaussian, CB, Voigt, …) + fit_histogram()
       │   ├── kinematics.py     — KinematicsOperations (invariant mass, ΔR, pT, …)
       │   ├── correlations.py   — CorrelationAnalysis (Pearson, Spearman, matrices)
       │   ├── plotting.py       — PlottingAnalysis (matplotlib 1D/2D plot generation)
       │   ├── operations.py     — AnalysisOperations (high-level coordinator)
       │   └── expression.py     — SafeExprEvaluator (restricted expression parser)
       ├── tools/
       │   ├── analysis.py       — AnalysisTools MCP tool layer (extended tools)
       │   ├── plotting.py       — PlottingTools MCP tool layer
       │   └── root_native.py    — RootNativeTools (run_root_code, run_rdataframe, …)
       └── root_native/
           ├── executor.py       — RootCodeExecutor (subprocess isolation, timeout)
           ├── sandbox.py        — CodeValidator (AST-based import blocking)
           └── templates.py      — RDataFrame and macro code templates

----

Sub-package details
-------------------

``root_mcp.common``
~~~~~~~~~~~~~~~~~~~

Shared infrastructure used by all tiers.  No physics or analysis dependencies.

- :mod:`root_mcp.common.root_availability` — the ROOT probe is subprocess-based
  to avoid contaminating the MCP server process with ROOT's global signal
  handlers.  Results are cached after the first call.
- :mod:`root_mcp.common.errors` — extends the error hierarchy used throughout;
  ``SecurityError`` is raised by :mod:`root_mcp.core.io.validators` on path
  traversal attempts.
- :mod:`root_mcp.common.cache` — generic helpers used by :class:`~root_mcp.core.io.file_manager.FileCache`.

``root_mcp.config``
~~~~~~~~~~~~~~~~~~~

All configuration is expressed as Pydantic v2 models in
:mod:`root_mcp.config`.  The key model is :class:`~root_mcp.config.Config`
which composes:

.. list-table::
   :header-rows: 1

   * - Sub-model
     - Governs
   * - :class:`~root_mcp.config.ServerConfig`
     - Name, version, mode (``core`` / ``extended``)
   * - :class:`~root_mcp.config.SecurityConfig`
     - Allowed roots, protocols, path depth
   * - :class:`~root_mcp.config.ResourceConfig`
     - Named data sources (URI + glob patterns)
   * - :class:`~root_mcp.config.LimitsConfig`
     - Row caps, export row limits
   * - :class:`~root_mcp.config.CacheConfig`
     - File-handle cache size
   * - :class:`~root_mcp.config.FeatureFlags`
     - ``enable_root`` toggle
   * - :class:`~root_mcp.config.RootNativeConfig`
     - Timeout, output formats, working directory for native ROOT

``root_mcp.core``
~~~~~~~~~~~~~~~~~

The **core tier** runs without scipy or matplotlib.  The IO sub-package is the
foundation everything else builds on:

- :class:`~root_mcp.core.io.file_manager.FileManager` owns the uproot file
  handles and the LRU cache.
- :class:`~root_mcp.core.io.validators.PathValidator` is the single enforcement
  point for the ``security.allowed_roots`` and protocol allow-lists.
- :class:`~root_mcp.core.io.readers.TreeReader` and
  :class:`~root_mcp.core.io.readers.HistogramReader` provide high-level branch
  and histogram reading with chunking and offset support.

``root_mcp.extended``
~~~~~~~~~~~~~~~~~~~~~

The **extended tier** loads lazily — only if ``config.server.mode == "extended"``
and the scipy/matplotlib imports succeed.  If they fail, the server falls back
to core mode automatically.

- :mod:`root_mcp.extended.analysis.fitting` is the most complex module.
  ``fit_histogram()`` supports composite models (e.g. Gaussian + exponential
  background), per-parameter bounds, and fixed parameters.
- :mod:`root_mcp.extended.root_native` is the native ROOT execution engine.
  ``RootCodeExecutor`` runs user code in a subprocess; ``CodeValidator``
  performs AST-level import blocking as a best-effort sandbox.

----

Adding a new analysis tool
---------------------------

The typical flow for adding an extended analysis capability:

1. Add the pure calculation to the appropriate module in
   ``src/root_mcp/extended/analysis/`` (e.g. ``kinematics.py``).
2. Add the corresponding MCP tool method to
   ``src/root_mcp/extended/tools/analysis.py`` (or ``plotting.py``).
3. Register the tool in ``src/root_mcp/server.py`` under
   ``_register_extended_tools()``.
4. Document the tool in ``docs/api/tools.md`` following the existing table format.
5. Add tests under ``tests/``.

Adding a core tool follows the same pattern but targets
``src/root_mcp/core/tools/`` and ``_register_core_tools()`` in the server.
