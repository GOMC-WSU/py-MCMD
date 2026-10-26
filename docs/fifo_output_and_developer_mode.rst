Runtime Storage and Developer Mode
==================================

The refactored workflow uses managed runtime storage for files exchanged by
NAMD, GOMC, and the on-the-fly processor. On Linux, the default managed root is
a directory under ``/dev/shm`` whose name combines the working-directory
identity with a unique suffix for each invocation. If that location is
unavailable, the program uses a unique subdirectory of ``.managed_outputs``
in the working directory. Set ``PY_MCMD_MANAGED_OUTPUT_ROOT`` before starting
py-MCMD to choose an explicit location. The run log records the managed root.

Output controls
---------------

``developer_mode`` set to ``false``
   Default. Raw per-cycle engine files stay in managed runtime storage. The
   configured ``NAMD/`` and ``GOMC/`` directories are created but do not retain
   the files needed for a later restart or standalone analysis.

``developer_mode`` set to ``true``
   Keep the managed workflow and mirror each completed engine segment to the
   configured on-disk NAMD and GOMC directories. Use this mode when raw files
   must be inspected, a run may be restarted, or the legacy combining program
   will be used. Rendered ``in.conf`` inputs are archived to disk before
   engine execution; completed output is mirrored afterward. Failed step
   files are mirrored for diagnosis as well.

Setting ``process_on_the_fly`` to ``true`` is independent of developer mode. It writes
combined analysis output as the calculation proceeds; it does not make a
default-mode run restartable.
The default ``combined_data/`` destination is relative to the launch
directory and remains on disk independently of managed runtime cleanup.

Retained output
---------------

With ``disk_cleanup_mode`` set to its default, ``compact``, the two output switches
have the following effect:

.. list-table::
   :header-rows: 1
   :widths: 26 26 48

   * - ``developer_mode``
     - ``process_on_the_fly``
     - Retained output
   * - ``false``
     - ``false``
     - Run log only; no raw or combined data files
   * - ``false``
     - ``true``
     - Run log and combined analysis files
   * - ``true``
     - ``false``
     - Run log and raw NAMD/GOMC directories
   * - ``true``
     - ``true``
     - Run log, raw directories, and combined files

Choose these settings before starting a production calculation. Combined
files cannot replace raw restart files.

Managed-storage cleanup
-----------------------

.. list-table::
   :header-rows: 1
   :widths: 20 40 40

   * - Mode
     - During execution
     - After successful completion
   * - ``compact`` (default)
     - Retain the latest ``otf_keep_raw_cycles`` cycle pairs.
     - Remove managed segment directories and engine caches.
   * - ``minimal``
     - Retain the latest ``otf_keep_raw_cycles`` cycle pairs.
     - Keep recent managed segment directories; remove engine caches.
   * - ``off``
     - Retain all managed segment directories.
     - Keep managed segment directories; remove engine caches.

Cleanup applies to managed runtime storage, not to raw files mirrored by
developer mode. On failure, the remaining managed files are preserved for
diagnosis; earlier files removed by rolling cleanup are not recovered.
Failed segments remain registered in the artifact store and are excluded from
step release and bulk cleanup, including when ``developer_mode`` is ``false``.
Their files remain under the managed root recorded in the run log.
Engine caches needed by failed segments are also retained, so links to cached
NAMD FFT plans remain readable.

Default managed roots are unique to each invocation. An explicit
``PY_MCMD_MANAGED_OUTPUT_ROOT`` is used as supplied, so choose a different
value for each concurrent calculation. Independent calculations also need
separate working directories or distinct disk output and log destinations:
unique managed roots do not prevent collisions in shared ``NAMD/``,
``GOMC/``, ``logs/``, or ``combined_data/`` directories.

Restart requirement
-------------------

The restart logic reads the preceding cycle from ``path_namd_runs`` and
``path_gomc_runs`` on disk. Therefore, start the original calculation with
``developer_mode`` set to ``true`` if it may need to be restarted. Preserve
the complete raw output and follow :doc:`simulation_output`.

See :doc:`simulation_output` for the disk layout and :doc:`simulation_analysis`
for the distinction between on-the-fly and standalone combined output.
