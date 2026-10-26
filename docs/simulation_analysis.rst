Analysis Files
==============

py-MCMD can combine selected output after each cycle. The standalone
program combines retained raw segments after execution. For standalone
processing of a hybrid run, set ``developer_mode`` to ``true`` before
starting the simulation.

.. list-table::
   :header-rows: 1
   :widths: 25 35 40

   * - Method
     - Required source
     - Coverage
   * - On-the-fly processing
     - Current engine segments; ``process_on_the_fly`` enabled
     - Selected energy, state, topology, and DCD output as cycles finish.
   * - Standalone combining
     - Raw disk copies; original hybrid run uses ``developer_mode`` enabled
     - Post-run processing, including GCMC histogram and distribution outputs.

On-the-fly files
----------------

Set ``process_on_the_fly`` to ``true``. Files are written under
``combined_data_dir``, which defaults to ``combined_data/``.
Relative destinations are resolved from the invocation's working directory.
Launching from the repository root therefore writes to its
``combined_data/`` directory; managed temporary storage does not change
that destination. Developer mode is not required for combined output.

.. list-table::
   :header-rows: 1
   :widths: 47 53

   * - File
     - Contents
   * - ``NAMD_data_box_0.txt``
     - NAMD energy records for box 0.
   * - ``NAMD_data_box_1.txt``
     - Gas-phase NAMD energy records when GEMC enables both NAMD boxes.
   * - ``NAMD_data_density_box_0.txt``
     - NAMD records with calculated density.
   * - ``NAMD_data_density_box_1.txt``
     - Gas-phase NAMD records with calculated density for two-NAMD-box GEMC.
   * - ``GOMC_data_box_0.txt``
     - GOMC energy and state records for box 0.
   * - ``GOMC_data_box_1.txt``
     - GOMC energy and state records for box 1 in GCMC/GEMC.
   * - ``GOMC_Energies_Stat_box_0.txt``
     - Merged box-0 GOMC energy and state columns.
   * - ``GOMC_Energies_Stat_kcal_per_mol_box_0.txt``
     - Box-0 GOMC summary with converted energy units.
   * - ``GOMC_Energies_Stat_box_1.txt``
     - Merged box-1 GOMC energy and state columns for two-NAMD-box GEMC.
   * - ``GOMC_Energies_Stat_kcal_per_mol_box_1.txt``
     - Box-1 GOMC summary with converted energy units for two-NAMD-box GEMC.
   * - ``combined_NAMD_GOMC_data_box_0.txt``
     - Alternating box-0 NAMD and GOMC records.
   * - ``combined_NAMD_GOMC_data_box_1.txt``
     - Box-1 NAMD and GOMC records for two-NAMD-box GEMC.
   * - ``Output_data_merged.psf``
     - Topology copied from GOMC for combined trajectories.
   * - ``combined_box_0_NAMD_dcd_files.dcd``
     - NAMD trajectory segments for NVT/NPT when enabled.
   * - ``combined_box_0_GOMC_dcd_files.dcd``
     - GOMC box-0 trajectory segments when enabled.
   * - ``combined_box_1_GOMC_dcd_files.dcd``
     - GOMC box-1 trajectory segments for GCMC/GEMC when enabled.

A listed file may be absent or empty when the corresponding engine record or
trajectory is unavailable. The NAMD DCD path applies only to NVT/NPT; the
GOMC DCD paths apply to all supported ensembles.

Box-1 NAMD summaries require ``simulation_type`` set to ``GEMC`` and
``only_use_box_0_for_namd_for_gemc`` set to ``false``. Liquid-only GEMC
still produces the box-1 GOMC output. When gas MD is temporarily skipped
because fewer than two molecules are present, no NAMD rows are invented
for that cycle; the GOMC records continue.

Record selection and units
--------------------------

Use the column headers in the generated text files to interpret each value.
NAMD reports energy in kcal/mol. Raw GOMC energy is in K; the
``kcal_per_mol`` summary converts energy for comparison. Check units before
joining files or plotting mixed-engine data.

The DCD selection interval counts complete cycle segments from the
configured start cycle. It does not resample individual frames. Keep the
engine output frequencies and selected cycle interval with the analysis
record.

.. warning::

   On-the-fly text files are opened for appending. Reusing a destination
   for an independent run or repeating completed cycles can duplicate
   records and headers. Preserve the old output and use a separate
   destination when needed.

Standalone combining
--------------------

``combine_data_NAMD_GOMC.py`` reads on-disk raw segment directories after a
run. Both processing methods can generate NAMD summaries for the two GEMC
boxes. The standalone program additionally produces GCMC histogram and
distribution files that the on-the-fly processor does not create. It
also supports NAMD-only and GOMC-only input sets. Run it using the separate
configuration described in :doc:`running_analysis_code`.

Combined output is an analysis product. Keep the source JSON, templates,
starting system, and raw developer-mode directories when reproducibility or
restart is required.
