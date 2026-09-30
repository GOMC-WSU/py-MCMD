Output Files and Restarts
=========================

Output locations
----------------

py-MCMD separates the run log, raw engine files, and combined analysis.
Raw files and analysis files have different retention rules.

.. list-table::
   :header-rows: 1
   :widths: 20 43 37

   * - Artifact
     - Default location
     - Retention
   * - Run log
     - ``logs/NAMD_GOMC_started_at_cycle_No_<start>.log``
     - Written for the invocation; overwritten when the same starting cycle is reused.
   * - Managed engine files
     - Working-directory-specific root under ``/dev/shm``
     - Controlled by ``disk_cleanup_mode``.
   * - Raw NAMD disk copies
     - ``NAMD/``
     - Mirrored when ``developer_mode`` is ``true``.
   * - Raw GOMC disk copies
     - ``GOMC/``
     - Mirrored when ``developer_mode`` is ``true``.
   * - Combined analysis
     - ``combined_data/``
     - Written when ``process_on_the_fly`` is ``true``.

Set the on-disk destinations through ``log_dir``, ``path_namd_runs``,
``path_gomc_runs``, and ``combined_data_dir`` in the JSON configuration.
``PY_MCMD_MANAGED_OUTPUT_ROOT`` is an environment variable, not a JSON key.

.. important::

   Enable ``developer_mode`` before the original run if restart files
   or standalone analysis will be needed. Combined trajectories and
   summary tables cannot replace the raw restart state.

With developer mode disabled, the on-disk NAMD/GOMC roots are placeholders.
The raw files remain in managed storage until cleanup. See
:doc:`fifo_output_and_developer_mode` for retention after success or failure.

Segment numbering
-----------------

Cycle indices start at zero. For cycle ``c``, the NAMD index is ``2*c``
and the GOMC index is ``2*c + 1``. Directory indices are padded to ten
digits.

.. list-table::
   :header-rows: 1
   :widths: 10 45 45

   * - Cycle
     - NAMD box 0
     - GOMC
   * - 0
     - ``NAMD/0000000000_a/``
     - ``GOMC/0000000001/``
   * - 1
     - ``NAMD/0000000002_a/``
     - ``GOMC/0000000003/``
   * - 2
     - ``NAMD/0000000004_a/``
     - ``GOMC/0000000005/``

When GEMC uses NAMD for both boxes, each NAMD index also has a ``_b``
directory for box 1. A GOMC directory contains the corresponding GOMC
stage's output, including both boxes when applicable.

These directories contain engine inputs, logs, trajectories, and restart
files produced by that segment. A directory can exist without a completed
engine run; inspect its log and restart files.

Run log and completion
----------------------

The run log records engine selection, cycle progress, errors, and timing
records. ``All cycles completed.`` marks successful orchestration.
Check the engine logs and energy continuity reports as well.

.. warning::

   The log is opened in write mode. Before repeating a starting cycle,
   preserve the existing log and any failed-segment files required for
   diagnosis.

Combined analysis
-----------------

On-the-fly output includes energy and state records, an available merged
PSF, and selected DCD trajectory segments. Filenames and ensemble coverage are
listed in :doc:`simulation_analysis`.

Text output is appended to existing files. Repeating cycles can produce
duplicate records or repeated headers. For independent calculations, use
separate working directories and output destinations.

Restart procedure
-----------------

A restart resumes at a completed coupled-cycle boundary. It requires the
previous completed NAMD/GOMC pair in the configured on-disk roots; it does
not resume an arbitrary frame within a failed segment.

1. Preserve the original JSON, structures, force fields, and templates.
   Keep the complete raw NAMD and GOMC directories. Retain the initial
   NAMD logs as well: the workflow reads run-0 PME-grid information.
2. Identify the last fully completed coupled cycle from both engine logs.
   Do not count a cycle whose NAMD stage finished but whose GOMC stage
   failed.
3. Set ``starting_at_cycle_namd_gomc_sims`` to the next cycle.
   Set ``total_cycles_namd_gomc_sims`` to the final target count, not the
   number of additional cycles.
4. Keep the ensemble, topology, force fields, templates, and segment
   lengths unchanged.
5. Preserve existing combined output before resuming. If using a new
   ``combined_data_dir``, its output will cover the resumed portion only.
6. Run the CLI with the updated complete configuration.

Example: resume at cycle 2
~~~~~~~~~~~~~~~~~~~~~~~~~~

Suppose cycles 0 and 1 completed and the target is five cycles. The previous
completed pair is ``NAMD/0000000002_a/`` and ``GOMC/0000000003/``.
For NAMD in both GEMC boxes, retain ``NAMD/0000000002_b/`` as well.

Change the following fields in the existing configuration:

.. code-block:: json

   {
     "total_cycles_namd_gomc_sims": 5,
     "starting_at_cycle_namd_gomc_sims": 2,
     "developer_mode": true
   }

This is a configuration fragment, not a complete input file. It executes
cycles 2, 3, and 4: three additional cycles, not five.

.. code-block:: bash

   python py_mcmd_refactored/cli/main.py -f user_input_NAMD_GOMC.json

For parallel two-NAMD-box GEMC, also pass
``-namd_sims_order parallel``. Changing ``developer_mode`` after raw
files have been removed does not recover those files.

Analysis after completion
-------------------------

The standalone combining program reads retained on-disk engine segments.
It uses a separate JSON configuration and expects roots named ``NAMD``
and ``GOMC`` in its working directory. See :doc:`running_analysis_code`.
