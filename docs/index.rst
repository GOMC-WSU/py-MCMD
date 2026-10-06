py-MCMD User Manual
===================

Overview
--------

py-MCMD alternates molecular dynamics (MD) in NAMD with Monte Carlo (MC)
in GOMC. Each cycle runs one NAMD stage followed by one GOMC stage and
transfers the simulation state between engines.

This manual documents the refactored command-line program,
``py_mcmd_refactored/cli/main.py``. Commands assume the repository root
as the working directory unless stated otherwise. Relative input paths
are resolved from the current working directory, not from the directory
containing the JSON configuration.

.. list-table::
   :header-rows: 1
   :widths: 15 55 30

   * - Ensemble
     - GOMC stage
     - NAMD stage
   * - ``NVT``
     - Constant particle count, volume, and temperature
     - Box 0
   * - ``NPT``
     - Constant particle count, pressure, and temperature
     - Box 0
   * - ``GCMC``
     - Grand canonical Monte Carlo; requires two starting boxes
     - Box 0
   * - ``GEMC``
     - Gibbs ensemble Monte Carlo; requires two starting boxes
     - Box 0 or both boxes

The NAMD stage uses NVT dynamics for every ensemble. The workflow supports
orthogonal boxes. Validate the prepared system in each engine before a
production calculation.

Prerequisites
-------------

Install the Python dependencies, NAMD, GOMC, and, for trajectory
concatenation, CatDCD. py-MCMD does not install the simulation engines.

.. toctree::
   :maxdepth: 1

   installation
   generating_systems

Input Files
-----------

The simulation JSON specifies the ensemble, starting PSF/PDB files,
force fields, templates, segment lengths, and output controls.
The supplied example contains machine-specific engine paths.

.. toctree::
   :maxdepth: 1

   simulation_parameters_files

CLI Parameters
--------------

The CLI accepts a simulation JSON file and options for a dry run and
NAMD execution order.

.. toctree::
   :maxdepth: 1

   running_the_simulation

Execution
---------

Start with :doc:`quick_start` for the supplied GEMC example. Select output
retention before execution: restarts and standalone analysis require
raw engine files.

.. toctree::
   :maxdepth: 1

   quick_start
   fifo_output_and_developer_mode
   simulation_output
   simulation_analysis
   running_analysis_code
   example_simulation

Troubleshooting
---------------

Inspect the py-MCMD run log and the failed engine segment before repeating
a calculation. A dry run does not execute or validate either engine.

.. toctree::
   :maxdepth: 1

   troubleshooting

Citation and licenses
---------------------

.. toctree::
   :maxdepth: 1

   citing_MDMC_PYTHON

py-MCMD and CatDCD have separate licenses. See the
:download:`combined license file <../LICENSE>`,
:download:`py-MCMD license <_images/NAMD_GOMC_license>`, and
:download:`CatDCD license <_images/CatDCD_license>`.
