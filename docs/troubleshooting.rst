Troubleshooting
===============

Diagnostic procedure
--------------------

1. Preserve the run log before repeating the invocation. A run with the
   same starting cycle overwrites that log.
2. Locate the first error in
   ``logs/NAMD_GOMC_started_at_cycle_No_<start>.log``, or the configured
   ``log_dir``.
3. Identify the failing cycle, engine, and box. Inspect that engine's
   input and log in retained raw output or managed storage.
4. Correct the input or environment, then follow the documented restart
   procedure. Do not treat a partially completed pair as a completed cycle.

Configuration and Python
------------------------

.. list-table::
   :header-rows: 1
   :widths: 25 30 45

   * - Symptom
     - Check
     - Corrective action
   * - Missing ``pydantic``, ``numpy``, or ``pandas``
     - Active Python environment.
     - Activate the simulation environment; install Pydantic 2, NumPy, and Pandas. Standalone
       combining also needs SciPy.
   * - Missing ``tkinter`` or ``_tkinter``
     - Tk support in the active Python environment.
     - The current NAMD integration imports Python's turtle module, which requires Tk. For
       Conda, install ``tk`` in the simulation environment.
   * - Pydantic validator/import error
     - Installed Pydantic major version.
     - Use ``pydantic>=2,<3`` as described in :doc:`installation`.
   * - Unknown or missing JSON key
     - Field names, required keys, and nullable fields.
     - Use :doc:`simulation_parameters_files` . Keep required geometry and box-1 path keys even
       when their value is ``null`` .
   * - JSON parsing error
     - Quoting, commas, Boolean literals, and ``//`` inside strings.
     - Use unquoted ``true`` /``false``; avoid ``//`` inside strings because the reader strips
       the remainder of that line.
   * - Input file or template not found
     - Working directory and configured path.
     - Resolve relative paths from the directory where the command is launched, not from the
       JSON directory.

Engine startup and execution
----------------------------

.. list-table::
   :header-rows: 1
   :widths: 25 30 45

   * - Symptom
     - Check
     - Corrective action
   * - NAMD executable not found
     - ``namd2_bin_directory``.
     - Provide an executable named ``namd2``.
   * - GOMC executable not found
     - Device, ensemble, and ``gomc_bin_directory``.
     - For CPU GEMC, provide ``GOMC_CPU_GEMC`` or fallback ``GOMC_CPU`` ; use the corresponding
       names for other selections.
   * - Dry run succeeds; production fails
     - Engine log, executable permissions, libraries, and input syntax.
     - Test the prepared system independently in each engine. A dry run does not launch either
       engine.
   * - Two NAMD boxes run serially
     - CLI option and GEMC box settings.
     - Set ``only_use_box_0_for_namd_for_gemc`` to ``false`` and pass
       ``-namd_sims_order parallel`` ; the CLI default overrides JSON order.
   * - ``--verbose`` does not enable DEBUG logs
     - Current CLI implementation.
     - Use the INFO run log and engine logs; the flag currently does not change the logging
       level.
   * - Shared-memory or disk exhaustion
     - Capacity of the managed root and output destinations.
     - Select suitable storage with ``PY_MCMD_MANAGED_OUTPUT_ROOT`` before execution; review
       retention settings.

Output and restart
------------------

.. list-table::
   :header-rows: 1
   :widths: 25 30 45

   * - Symptom
     - Check
     - Corrective action
   * - Raw ``NAMD/`` and ``GOMC/`` roots are empty
     - Original ``developer_mode`` setting.
     - Enable it before a new run when raw files are needed. Enabling it later does not recover
       cleaned files.
   * - Restart cannot find the previous cycle
     - Last completed NAMD/GOMC pair and configured raw roots.
     - Retain the complete raw directories, including initial NAMD logs. Follow
       :doc:`simulation_output` .
   * - No combined text output
     - ``process_on_the_fly`` and engine records.
     - Enable on-the-fly processing before execution, or use standalone combining on retained
       raw output.
   * - Combined DCD missing
     - Processing flag, engine-specific DCD flag, CatDCD path, and source trajectory.
     - Check the processor warnings. NAMD combined DCD output is supported for NVT/NPT only.
   * - Repeated analysis rows or headers
     - Existing combined destination and repeated cycle indices.
     - Preserve the existing output. Use a separate destination for an independent calculation
       or explicitly reconcile restarted data.
   * - Standalone program cannot find segments
     - Working-directory roots named ``NAMD`` and ``GOMC``.
     - The standalone program ignores custom runner roots; follow :doc:`running_analysis_code`.
   * - Standalone destination already exists
     - ``-w`` destination and ``-o`` value.
     - Choose a new relative directory. Use ``-o true`` only when replacing generated files
       there is intended.

