Quick Start
===========

Overview
--------

The supplied ``user_input_NAMD_GOMC.json`` describes GEMC sampling of
water at 350 K. It requests 10,000 cycles with 1,000 NAMD steps in each
box, running concurrently with eight cores per box, followed by 200 CPU
GOMC steps. The engine paths must be changed for the local installation.

The procedure below creates a separate 10-cycle check with three cores
per NAMD box. This short run checks execution; it does not establish
equilibration or sampling convergence.

Prerequisites
-------------

Complete :doc:`installation` and activate the simulation environment.
Run the commands below from the repository root. Use a separate working
copy for the optional dry run so that its generated files do not mix
with production output.

Input Files
-----------

Review the supplied configuration and the files in ``required_data/input/``.
The JSON is organized into named sections; edit settings in their existing
sections. Template paths can be omitted: GEMC selects separate liquid and
gas NAMD templates and the GEMC GOMC template automatically.

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

Prepare a short two-box check
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create a separate input from the supplied JSON:

.. code-block:: bash

   python - <<'PY'
   import json
   from pathlib import Path

   config = json.loads(Path("user_input_NAMD_GOMC.json").read_text())
   config["run_control"].update({
       "total_cycles_namd_gomc_sims": 10,
       "starting_at_cycle_namd_gomc_sims": 0,
   })
   config["execution"].update({
       "only_use_box_0_for_namd_for_gemc": False,
       "no_core_box_0": 3,
       "no_core_box_1": 3,
       "namd_simulation_order": "parallel",
   })
   Path("gemc_10cycles.json").write_text(json.dumps(config, indent=2) + "\n")
   PY

In ``gemc_10cycles.json``, replace the machine-specific executable
directories in ``engines`` and check the starting structures and force
fields. Allocate at least six CPU cores for the two concurrent NAMD
segments. This input keeps the supplied 1,000 MD and 200 MC steps per
cycle and enables combined output. Enable ``developer_mode`` under
``output`` if raw files or a restart are needed.

Check input generation (optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In the dry-run working copy:

.. code-block:: bash

   python py_mcmd_refactored/cli/main.py \
       -f gemc_10cycles.json \
       --dry_run

Inspect the generated inputs and
``logs/NAMD_GOMC_started_at_cycle_No_0.log``. Correct configuration or
template errors before proceeding.

.. note::

   A dry run creates files but does not execute NAMD or GOMC. It can
   continue when an engine directory does not exist, so it is not an
   executable-installation check.

Run the short check
~~~~~~~~~~~~~~~~~~~

In the simulation working copy, with validated inputs and unused output
locations:

.. code-block:: bash

   python py_mcmd_refactored/cli/main.py -f gemc_10cycles.json

The JSON execution order is honored without an additional CLI flag.
NAMD uses ``required_data/config_files/namd/gemc_liquid.conf`` for box 0
and ``required_data/config_files/namd/gemc_gas.conf`` for box 1.
GOMC then updates both boxes using
``required_data/config_files/gomc/gemc.conf``.

The run log should contain ``All cycles completed.``. Inspect the
engine logs, continuity reports, and combined data before interpreting
results. Completion alone does not establish equilibration or convergence.

For production, choose the cycle count, core counts, and output destinations
in a separate configuration. See :doc:`running_the_simulation` for
liquid-only GEMC and single-box NPT/NVT settings.

Output
------

With the supplied on-the-fly setting, selected results are written under
``combined_data/``. Raw disk copies are available only if
``developer_mode`` was enabled. See :doc:`simulation_analysis` for
filenames and :doc:`simulation_output` for restart requirements.
When launched from the repository root, the default destination is
``<repository>/combined_data/``, not managed temporary storage. Launching
from another working directory changes the base for this relative path.

For two-NAMD-box GEMC, check for ``NAMD_data_box_0.txt``,
``NAMD_data_box_1.txt``, ``GOMC_data_box_0.txt``, and
``GOMC_data_box_1.txt``. Gas NAMD rows are absent for cycles when the
gas population is too small for MD; see :doc:`running_the_simulation`.
For this GEMC example, GOMC trajectories can be combined for both boxes;
the on-the-fly processor does not combine NAMD DCD segments for GEMC.

Troubleshooting
---------------

For missing packages, executable paths, or output files, use
:doc:`troubleshooting`. The complete JSON reference is in
:doc:`simulation_parameters_files`; command-line options are in
:doc:`running_the_simulation`.
