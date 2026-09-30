Standalone Combining Program
============================

Overview
--------

``combine_data_NAMD_GOMC.py`` combines retained raw segments after a
simulation. It can produce two-box NAMD summaries and GCMC histogram
and distribution files that are absent from the on-the-fly output.

Prerequisites
-------------

The program requires NumPy, Pandas, and SciPy. DCD concatenation also
requires CatDCD. For hybrid simulations, enable ``developer_mode``
before the source calculation so that raw engine output is retained.

The program reads directories named ``NAMD/`` and ``GOMC/`` in its
current working directory. It does not read the runner's
``path_namd_runs`` or ``path_gomc_runs`` settings.

Input Files
-----------

Use ``user_input_combine_data_NAMD_GOMC.json``, not the simulation
configuration. Set its ensemble and box settings to match the source
calculation.

.. important::

   The supplied analysis JSON specifies GCMC, whereas the supplied
   simulation JSON specifies GEMC. Change the analysis settings before
   processing the supplied simulation.

All fields below are required.

.. list-table::
   :header-rows: 1
   :widths: 40 25 35

   * - Parameter
     - Accepted value
     - Meaning
   * - ``simulation_type``
     - ``GEMC``, ``GCMC``, ``NPT``, ``NVT``
     - Source ensemble.
   * - ``only_use_box_0_for_namd_for_gemc``
     - Boolean
     - Whether the source GEMC calculation used NAMD for box 0 only.
   * - ``simulation_engine_options``
     - ``Hybrid``, ``NAMD-only``, ``GOMC-only``
     - Source engine configuration.
   * - ``gomc_or_namd_only_log_filename``
     - String
     - Log filename for engine-only input; supplied value: ``out.dat``.
   * - ``combine_namd_dcd_file``
     - Boolean
     - Combine NAMD trajectory segments.
   * - ``combine_gomc_dcd_file``
     - Boolean
     - Combine GOMC trajectory segments.
   * - ``combine_dcd_files_cycle_freq``
     - Integer ≥ 1
     - Select every Nth segment for trajectory combination.
   * - ``get_initial_gomc_dcd``
     - Boolean
     - Control inclusion of the initial GOMC trajectory frame.
   * - ``rel_path_to_combine_binary_catdcd``
     - String
     - CatDCD path, resolved from the working directory.

.. literalinclude:: ../user_input_combine_data_NAMD_GOMC.json
   :language: json
   :linenos:

CLI Parameters
--------------

.. list-table::
   :header-rows: 1
   :widths: 42 18 40

   * - Option
     - Default
     - Behavior
   * - ``-f FILE``, ``--file FILE``
     - Required
     - Read the standalone analysis JSON.
   * - ``-w DIRECTORY``, ``--write_folder_name DIRECTORY``
     - Required
     - Write combined output to a relative destination directory.
   * - ``-o VALUE``, ``--overwrite VALUE``
     - ``false``
     - ``false`` refuses an existing destination; ``true`` allows generated files to be
       replaced.

Accepted Boolean spellings for ``-o`` are ``True``, ``true``,
``T``, ``t``, ``False``, ``false``, ``F``, and ``f``.
The overwrite option does not clear unrelated files. Use JSON Boolean
literals (``true`` or ``false``) for Boolean fields inside the input file.

Execution
---------

From the repository root containing the raw engine directories, choose a
new relative destination, separate from any on-the-fly output:

.. code-block:: bash

   python combine_data_NAMD_GOMC.py \
       -f user_input_combine_data_NAMD_GOMC.json \
       -w combined_legacy \
       -o false

If the source used custom raw-output roots, create copies or links named
``NAMD`` and ``GOMC`` in a separate analysis directory. Launch the
script by its path and ensure that the JSON and CatDCD paths are valid
from that directory. Keep the original raw output intact.

Troubleshooting
---------------

If raw segments are not found, check the working directory and directory
names before changing the input files. If trajectory combination fails,
inspect the source DCD files and CatDCD executable. File coverage and
energy units are described in :doc:`simulation_analysis`.
