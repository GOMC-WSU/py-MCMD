Installation
============

Prerequisites
-------------

The refactored py-MCMD workflow uses Linux runtime facilities and requires
Python, NAMD, GOMC, and prepared simulation inputs. NAMD and GOMC are separate
programs; py-MCMD does not install them. The default runtime store uses
``/dev/shm``, so ensure that location has enough space for the intermediate
files produced by the job. See :doc:`fifo_output_and_developer_mode`.

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Component
     - Requirement
   * - Python packages
     - Pydantic 2, NumPy, and Pandas for the refactored workflow; SciPy for standalone
       combining.
   * - NAMD
     - Executable named ``namd2``; installed separately.
   * - GOMC
     - Executable matching the selected ensemble and CPU/GPU setting; installed separately.
   * - CatDCD
     - Required for trajectory concatenation; must run on the compute node.
   * - Storage
     - Space for managed runtime files and any retained raw or combined output.
   * - Prepared system
     - Compatible PSF, PDB, force-field files, and NAMD/GOMC templates.

Obtain py-MCMD
--------------

Clone or download the repository:
https://github.com/GOMC-WSU/py-MCMD.

To clone a new working copy:

.. code-block:: bash

   git clone https://github.com/GOMC-WSU/py-MCMD.git
   cd py-MCMD

Run the remaining commands from the repository root. If a working copy
already exists, change to that directory instead of cloning again.

Python environment
------------------

Run these commands from the repository root. The supplied Conda file includes
NumPy, Pandas, and SciPy, but does not include Pydantic, which the refactored
program requires:

.. code-block:: bash

   conda env create -f namd_gomc-env.yml
   conda activate NAMD_GOMC-code
   conda install -c conda-forge "pydantic>=2,<3"
   python -c "import pydantic, numpy, pandas, scipy; print(pydantic.__version__)"

The version printed by the last command must start with ``2.``. The supplied
environment contains a broad set of dependencies for the older workflow.
If that environment cannot be solved on the local platform, a smaller
environment for the refactored program and the standalone combining script
can be created with:

.. code-block:: bash

   conda create -n py-mcmd -c conda-forge python=3.11 "pydantic>=2,<3" numpy pandas scipy tk
   conda activate py-mcmd

The program is run directly from this repository; no ``pip install`` step is
required for the commands in this manual. Check that the CLI can start:

.. code-block:: bash

   python py_mcmd_refactored/cli/main.py --version

Simulation engines
------------------

Set ``namd2_bin_directory`` to a directory containing an executable named
``namd2``. If the installed NAMD executable has a different name, place a
``namd2`` symlink in that directory.

Set ``gomc_bin_directory`` to a directory containing the executable for the
selected device and ensemble. For example, CPU GEMC uses ``GOMC_CPU_GEMC``.
If that file is absent, py-MCMD tries ``GOMC_CPU``; it makes the analogous
choice for GPU builds. The selected files must be executable on the compute
node where the job runs.

The distributed templates and earlier project work used NAMD 2.14 and GOMC
development builds. Test the selected versions with a short calculation
before production. A successful ``--dry_run`` does not establish engine
compatibility because it does not execute either engine.

Input files and CatDCD
----------------------

Each run needs PSF, PDB, and force-field files compatible with both engines,
plus the NAMD and ensemble-specific GOMC templates. The example files are in
``required_data/``. The workflow currently accepts orthogonal boxes only. See
:doc:`generating_systems` and :doc:`simulation_parameters_files`.

The bundled CatDCD binary is used when combined DCD trajectories are
requested. Check that the path selected by
``rel_path_to_combine_binary_catdcd`` points to a binary for the local system.
Energy and state summaries do not require trajectory concatenation.

Engine-specific references
--------------------------

Consult the `NAMD User's Guide <https://www.ks.uiuc.edu/Research/namd/2.14/ug/>`_
and `GOMC documentation <https://gomc.eng.wayne.edu/documentation/>`_ for
installation, simulation controls, and force-field syntax. NAMD runs in NVT
within this hybrid workflow; the GOMC stage controls the selected ensemble.
Check force-field term support in the installed engine versions and
compare energies for the same prepared configuration before production.
