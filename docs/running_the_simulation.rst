Running a Simulation
====================

Overview
--------

Run the CLI from the working directory used to resolve the input paths.
Commands below assume the repository root. A coupled cycle executes NAMD
first, then GOMC. For two-box GEMC, the two NAMD segments can run concurrently;
NAMD and GOMC stages remain sequential.

CLI Parameters
--------------

.. code-block:: text

   python py_mcmd_refactored/cli/main.py [-h] [--version] [-f FILE]
       [-namd_sims_order {series,parallel}] [-v] [--dry_run]

Square brackets mark optional arguments; do not type the brackets.

.. list-table::
   :header-rows: 1
   :widths: 35 25 40

   * - Option
     - Default
     - Behavior
   * - ``-h``, ``--help``
     - Not set
     - Print command help and exit.
   * - ``--version``
     - Not set
     - Print the py-MCMD version and exit.
   * - ``-f FILE``, ``--file FILE``
     - ``user_input_NAMD_GOMC.json``
     - Read the simulation configuration.
   * - ``-namd_sims_order ORDER``, ``--namd_simulation_order ORDER``
     - ``series``
     - Select ``series`` or ``parallel`` for two-box GEMC NAMD stages.
   * - ``--dry_run``
     - Not set
     - Generate inputs and run orchestration without launching NAMD or GOMC.
   * - ``-v``, ``--verbose``
     - Not set
     - Accepted, but the current CLI retains INFO logging; DEBUG output is not enabled.

.. important::

   The CLI overrides JSON ``namd_simulation_order`` even when the option
   is omitted. Pass ``-namd_sims_order parallel`` explicitly for parallel
   execution. An invalid order falls back to ``series``.

Execution
---------

Pre-run checks
~~~~~~~~~~~~~~

1. Activate the environment described in :doc:`installation`.
2. Verify engine paths, starting structures, force fields, and templates.
3. Confirm the ensemble and simulation-box geometry.
4. Set the starting cycle to ``0`` for a new run.
5. Select raw-output retention and on-the-fly processing.
6. Use a separate working directory for each independent calculation.
   Adjust relative input paths when using a directory other than the
   repository root.

Input-generation check (optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   python py_mcmd_refactored/cli/main.py \
       -f user_input_NAMD_GOMC.json \
       --dry_run

A dry run exercises configuration loading and input generation. It does
not test executable compatibility, engine input acceptance, force-field
consistency, or the physical validity of the calculation.

.. warning::

   A dry run writes files and logs, including placeholder engine artifacts.
   Use a separate working copy for this check. Do not use dry-run artifacts
   as production restart data.

A dry run can continue if an engine directory is absent. An existing GOMC
directory without the expected executable can still cause failure.
Check executable names and permissions independently.

Production run
~~~~~~~~~~~~~~

.. code-block:: bash

   python py_mcmd_refactored/cli/main.py -f user_input_NAMD_GOMC.json

For GEMC with NAMD in both boxes, set
``only_use_box_0_for_namd_for_gemc`` to ``false`` and allocate positive
core counts to both boxes. To execute the NAMD segments concurrently:

.. code-block:: bash

   python py_mcmd_refactored/cli/main.py \
       -f user_input_NAMD_GOMC.json \
       -namd_sims_order parallel

The parallel option has no effect when NAMD runs only box 0. Allocate
enough resources for both segments when they run concurrently.

Completion checks
~~~~~~~~~~~~~~~~~

The default log for a new calculation is
``logs/NAMD_GOMC_started_at_cycle_No_0.log``. Successful execution records
``All cycles completed.``. See :doc:`simulation_output` for log naming,
output locations, and restart files.

Completion does not establish equilibration or sampling convergence.
Inspect engine logs, energy continuity reports, and the analysis files
before interpreting results.

.. warning::

   Another invocation with the same starting cycle overwrites its run log.
   Existing combined text files are opened for appending. Preserve the
   previous results before reusing output locations.

Troubleshooting
---------------

Use :doc:`troubleshooting` for configuration, engine-startup, storage, and
analysis errors. The workflow does not support a box containing no atoms
or no mobile atoms.

Restart only from a completed coupled-cycle boundary; follow
:doc:`simulation_output`. Test GPU NAMD/GEMC combinations on a short
calculation before production.
