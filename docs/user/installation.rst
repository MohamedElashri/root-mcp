Installation
============

Requirements
------------

- Python **3.10** or later (3.11–3.14 fully supported)
- No C++ ROOT installation required — the core server runs on pure Python

Install from PyPI
-----------------

.. code-block:: bash

   pip install root-mcp

Optional extras
---------------

**XRootD remote access** (``root://`` URLs, CERN EOS, Open Data Portal):

.. code-block:: bash

   pip install "root-mcp[xrootd]"

.. note::

   XRootD requires a platform-compatible binary wheel. Linux x86_64 and
   macOS are supported. If no wheel is available for your platform,
   install `XRootD <https://xrootd.slac.stanford.edu/>`_ from conda-forge
   and then ``pip install root-mcp`` without the extra.

**Documentation tools** (to build this site locally):

.. code-block:: bash

   pip install "root-mcp[docs]"

Optional native ROOT support
-----------------------------

ROOT-MCP works fully without a CERN ROOT installation. When ROOT *is* available,
three additional tools unlock automatically (``run_root_code``, ``run_rdataframe``,
``run_root_macro``).

ROOT is **not** pip-installable. Supported installation paths:

.. list-table::
   :header-rows: 1

   * - Method
     - Command
     - Notes
   * - conda-forge
     - ``conda install -c conda-forge root``
     - Recommended; Linux & macOS
   * - System package
     - ``apt install root-system`` / ``brew install root``
     - OS-managed version
   * - Binary tarball
     - `root.cern/install <https://root.cern/install/>`_
     - Full manual control
   * - CVMFS / LCG
     - ``source /cvmfs/sft.cern.ch/…``
     - CERN/HEP cluster environments

After installing ROOT, enable it in ``config.yaml``:

.. code-block:: yaml

   features:
     enable_root: true

Verifying the installation
--------------------------

.. code-block:: bash

   root-mcp --help

You should see the full argument list. Run a quick server check:

.. code-block:: bash

   root-mcp --data-path /tmp     # starts on stdio; Ctrl-C to exit

Upgrading
---------

.. code-block:: bash

   pip install --upgrade root-mcp
