Installation
============

Requirements
------------

- Python **3.10** or later; CI targets 3.10–3.14
- MCP Python SDK **2.3+** within the 2.x line (installed as a dependency)
- No C++ ROOT installation required for the uproot analysis tools

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

   XRootD is a native dependency. Installation can require a compiler toolchain
   when no compatible wheel is available. As an alternative, install XRootD
   through conda-forge and install ROOT-MCP without the extra.

**Documentation tools** (to build this site locally):

.. code-block:: bash

   pip install "root-mcp[docs]"

Optional native ROOT support
-----------------------------

The standard analysis tools work without a CERN ROOT installation. When ROOT *is* available,
three additional tools become available when explicitly enabled in extended mode (``run_root_code``, ``run_rdataframe``,
``run_root_macro``).

Install a compatible ROOT/PyROOT environment separately. The ``root-mcp[root]``
extra does not install PyROOT. Common environment setup options:

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
   root-cli --version

You should see the full argument list. Run a quick server check:

.. code-block:: bash

   root-mcp --data-path /tmp     # starts on stdio; Ctrl-C to exit

Upgrading
---------

.. code-block:: bash

   pip install --upgrade root-mcp
