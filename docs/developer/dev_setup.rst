Development Setup
=================

This page guides you through setting up a local development environment for
ROOT-MCP from scratch.

----

Prerequisites
-------------

- Python **3.10** or later
- Git
- `uv <https://docs.astral.sh/uv/>`_ (recommended) or pip + venv

Clone the repository
---------------------

.. code-block:: bash

   git clone https://github.com/MohamedElashri/root-mcp.git
   cd root-mcp

Create a virtual environment and install dev dependencies
---------------------------------------------------------

**With uv (recommended):**

.. code-block:: bash

   uv sync --all-extras          # creates .venv and installs all deps including dev

**With pip:**

.. code-block:: bash

   python -m venv .venv
   source .venv/bin/activate     # Windows: .venv\Scripts\activate
   pip install -e ".[dev]"

Verify the install:

.. code-block:: bash

   root-mcp --help               # server entry point
   python -m pytest --version    # pytest is available

----

Running the test suite
-----------------------

.. code-block:: bash

   pytest                        # run all tests
   pytest -x                     # stop at first failure
   pytest tests/test_smoke.py    # single file
   pytest -k "test_config"       # filter by name pattern
   pytest --cov=src/root_mcp --cov-report=term-missing   # with coverage

Tests that require a ROOT installation are automatically skipped when ROOT is
not present. No test fixtures need ROOT files — the ``data/root_files/`` sample
files cover all file-level tests.

Running type checks
--------------------

ROOT-MCP uses `ty <https://github.com/astral-sh/ty>`_ for type checking:

.. code-block:: bash

   uv run ty check src/root_mcp

Linting and formatting
-----------------------

.. code-block:: bash

   uv run ruff check src/         # lint
   uv run ruff check --fix src/   # auto-fix safe violations
   uv run black src/              # format

Pre-commit hooks (run all checks on every commit):

.. code-block:: bash

   pre-commit install             # install hooks once
   pre-commit run --all-files     # run manually on all files

----

Building the documentation
---------------------------

Install doc dependencies:

.. code-block:: bash

   uv pip install -r docs/requirements.txt
   # or: pip install "root-mcp[docs]"

**Standard build:**

.. code-block:: bash

   cd docs
   make html
   # output → docs/_build/html/index.html

**Live-reload server** (auto-rebuilds on every file save):

.. code-block:: bash

   cd docs
   make livehtml
   # opens http://localhost:8000 in your browser

**Regenerate API stubs** (needed after adding/removing modules):

.. code-block:: bash

   cd root-mcp           # project root
   uv run sphinx-apidoc \
     --output-dir docs/apidoc/root_mcp \
     --module-first --separate --force \
     src/root_mcp

Or run the full pipeline script (Phases 5):

.. code-block:: bash

   ./scripts/build_docs.sh

**Strict build** (treats all warnings as errors — use before opening a PR):

.. code-block:: bash

   cd docs && make strict

----

Using the sample data
----------------------

The repository ships with a small set of ROOT files under ``data/root_files/``
that are used by the integration tests and examples:

.. code-block:: text

   data/root_files/
       analysis.root        — TTree with physics branches
       histograms.root      — TH1/TH2 histograms
       large_sample.root    — larger TTree for performance tests
       sample_events.root   — event-level data

Start the server against these files:

.. code-block:: bash

   root-mcp --data-path data/root_files

----

Project layout quick reference
--------------------------------

.. code-block:: text

   src/root_mcp/        — main package (see Module Overview)
   tests/               — pytest test suite
   docs/                — Sphinx documentation source
   data/root_files/     — sample ROOT files for development
   examples/            — standalone usage examples
   scripts/             — build and maintenance scripts
   config.yaml          — default configuration file
   pyproject.toml       — project metadata and dependencies
