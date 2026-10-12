Quick Start
===========

Overview
--------

The supplied ``user_input_NAMD_GOMC.json`` describes GEMC sampling of
water at 350 K. The example requests five cycles, each with 1,000 NAMD
steps in box 0 followed by 200 CPU GOMC steps. The engine paths must be
changed for the local installation.

The short example demonstrates execution; it is not an equilibrated
production protocol.

Prerequisites
-------------

Complete :doc:`installation` and activate the simulation environment.
Run the commands below from the repository root. Use a separate working
copy for the optional dry run so that its generated files do not mix
with production output.

Input Files
-----------

Review the supplied configuration and the files in ``required_data/input/``.

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Setting
     - Action before execution
   * - ``namd2_bin_directory``
     - Set the directory containing ``namd2``.
   * - ``gomc_bin_directory``
     - Set the directory containing ``GOMC_CPU_GEMC`` or fallback ``GOMC_CPU``.
   * - PSF, PDB, and force-field paths
     - Verify that every referenced file exists and describes the intended system.
   * - ``starting_at_cycle_namd_gomc_sims``
     - Use ``0`` for a new calculation.
   * - ``developer_mode``
     - The example uses ``false`` . Set ``true`` before production if restart or standalone
       analysis may be needed.
   * - ``process_on_the_fly``
     - The example uses ``true`` to write combined analysis after each completed cycle.

Execution
---------

Check input generation (optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In the dry-run working copy:

.. code-block:: bash

   python py_mcmd_refactored/cli/main.py \
       -f user_input_NAMD_GOMC.json \
       --dry_run

Inspect the generated inputs and
``logs/NAMD_GOMC_started_at_cycle_No_0.log``. Correct configuration or
template errors before proceeding.

.. note::

   A dry run creates files but does not execute NAMD or GOMC. It can
   continue when an engine directory does not exist, so it is not an
   executable-installation check.

Run production
~~~~~~~~~~~~~~

In the production working copy, with validated inputs and unused output
locations:

.. code-block:: bash

   python py_mcmd_refactored/cli/main.py -f user_input_NAMD_GOMC.json

The run log should contain ``All cycles completed.``. Inspect the
engine logs, continuity reports, and combined data before interpreting
results. Completion alone does not establish equilibration or convergence.

Output
------

With the supplied on-the-fly setting, selected results are written under
``combined_data/``. Raw disk copies are available only if
``developer_mode`` was enabled. See :doc:`simulation_analysis` for
filenames and :doc:`simulation_output` for restart requirements.
For this GEMC example, GOMC trajectories can be combined for both boxes;
the on-the-fly processor does not combine NAMD DCD segments for GEMC.

Troubleshooting
---------------

For missing packages, executable paths, or output files, use
:doc:`troubleshooting`. The complete JSON reference is in
:doc:`simulation_parameters_files`; command-line options are in
:doc:`running_the_simulation`.
