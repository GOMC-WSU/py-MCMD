Simulation Input and Templates
==============================

Input Files
-----------

The refactored CLI reads one simulation JSON file. Start from
``user_input_NAMD_GOMC.json`` and change its engine paths before execution.
All relative paths are resolved from the current working directory.

.. list-table::
   :header-rows: 1
   :widths: 18 47 35

   * - Input
     - Configuration field or default path
     - Requirement
   * - Run configuration
     - ``user_input_NAMD_GOMC.json``
     - Select another file with ``-f FILE``.
   * - Coordinates
     - ``starting_pdb_box_0_file``, ``starting_pdb_box_1_file``
     - PDB files consistent with the corresponding PSF.
   * - Topology
     - ``starting_psf_box_0_file``, ``starting_psf_box_1_file``
     - PSF files with matching atom order and residue definitions.
   * - Force fields
     - ``starting_ff_file_list_namd``, ``starting_ff_file_list_gomc``
     - Lists of engine-specific parameter files describing the same system.
   * - NAMD template
     - Selected from ``required_data/config_files/namd/``
     - Selected automatically by ensemble and, for GEMC, by box.
   * - GOMC template
     - Selected from ``required_data/config_files/gomc/``
     - Selected automatically by ensemble.

JSON conventions
----------------

* Field names are case-sensitive. Use the allowed values exactly as shown.
* Use unquoted ``true``, ``false``, and ``null`` for JSON literals.
* Unknown fields cause validation errors.
* A required field must be present even when its permitted value is
  ``null``.
* Defaults in the tables apply when a field is omitted; the supplied
  example may select a different value.

The supplied JSON groups settings into named sections. Existing flat JSON
files are also accepted; individual setting names and meanings are the same
in both formats.

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Section
     - Settings
   * - ``simulation``
     - Ensemble, temperature, and pressure.
   * - ``gcmc``
     - Chemical-potential or fugacity controls.
   * - ``run_control``
     - Cycle counts, segment lengths, and initial minimization.
   * - ``execution``
     - Engine device, NAMD box selection, core counts, and execution order.
   * - ``engines``
     - NAMD and GOMC executable directories.
   * - ``force_fields``
     - Parameter-file lists for both engines.
   * - ``box_0``, ``box_1``
     - Starting structures and box geometry.
   * - ``output``
     - Output destinations, retention, and trajectory processing.

Sections are organizational: the loader flattens them before validation.
Do not repeat a setting across sections or between a section and the top
level, even with the same value. Sections cannot be nested inside one
another. When editing the supplied file, update the existing section rather
than adding a second copy of a setting at the top level.

.. warning::

   The reader removes ``//`` and the remainder of each line before
   parsing. Do not put ``//`` inside strings. Standard JSON parsers do
   not accept these comments.

Ensemble requirements
---------------------

.. list-table::
   :header-rows: 1
   :widths: 12 30 20 38

   * - Ensemble
     - Starting structures
     - NAMD stage
     - Additional input
   * - ``NVT``
     - Box 0; box-1 path keys set to ``null``
     - Box 0
     - No ensemble-specific field.
   * - ``NPT``
     - Box 0; box-1 path keys set to ``null``
     - Box 0
     - ``simulation_pressure_bar``.
   * - ``GCMC``
     - Boxes 0 and 1
     - Box 0
     - Chemical-potential or fugacity settings by residue.
   * - ``GEMC``
     - Boxes 0 and 1
     - Box 0 or both boxes
     - ``only_use_box_0_for_namd_for_gemc`` selects the NAMD boxes.

GEMC denotes Gibbs ensemble Monte Carlo; GCMC denotes grand canonical
Monte Carlo. NAMD uses NVT dynamics for all four selections. GOMC
implements the selected ensemble.

Automatic template selection
----------------------------

Set ``simulation_type``; template-path fields can be omitted. The distributed
templates are selected as follows, relative to ``required_data/config_files/``:

.. list-table::
   :header-rows: 1
   :widths: 12 32 32 24

   * - Ensemble
     - NAMD box 0
     - NAMD box 1
     - GOMC
   * - ``GEMC``
     - ``namd/gemc_liquid.conf``
     - ``namd/gemc_gas.conf`` when enabled
     - ``gomc/gemc.conf``
   * - ``GCMC``
     - ``namd/gcmc.conf``
     - Not run
     - ``gomc/gcmc.conf``
   * - ``NPT``
     - ``namd/npt.conf``
     - Not run
     - ``gomc/npt.conf``
   * - ``NVT``
     - ``namd/nvt.conf``
     - Not run
     - ``gomc/nvt.conf``

An NPT simulation therefore uses one NAMD template. It does not require
liquid and gas template paths. Set its pressure, box-0 structures, and
geometry; set the required box-1 structure keys to ``null`` and
``no_core_box_1`` to ``0``. NAMD still runs NVT dynamics; GOMC performs
the NPT sampling.

For GEMC, box 0 is assigned the liquid template and box 1 the gas template;
selection follows the box number rather than a density measurement. Edit
the appropriate template to change that phase's engine settings. For
example, ``PMEGridSpacing`` in ``namd/gemc_gas.conf`` controls the gas
template independently of the liquid template. Validate engine energies for
the same configuration after changing PME or interaction settings; a
coarser grid does not itself establish equivalent accuracy.

Custom templates are optional. A GEMC per-box override
(``path_namd_template_box_0`` or ``path_namd_template_box_1``) takes
precedence over a shared ``path_namd_template`` override. Without either
override, the corresponding automatic template is used. An explicit shared
NAMD override applies to both GEMC boxes unless a box-specific override is
provided. ``path_gomc_template`` overrides the automatic GOMC choice.
These fields can be placed in ``engines`` when using sectioned input.
Ordinary runs need none of these path fields, including ``null`` placeholders.

Older distributed templates are kept under ``archive/`` where applicable.
Recognized missing legacy paths, such as
``required_data/config_files/NAMD.conf``, resolve to their relocated files.
An existing file at an explicitly supplied path takes precedence. A legacy
shared override still selects one shared template; omit it to use separate
automatic GEMC templates.

Run control
-----------

.. list-table::
   :header-rows: 1
   :widths: 38 22 40

   * - Parameter
     - Type / default
     - Definition
   * - ``total_cycles_namd_gomc_sims``
     - Integer ≥ 1; required
     - Total target cycle count, including completed cycles on restart.
   * - ``starting_at_cycle_namd_gomc_sims``
     - Integer ≥ 0; required
     - First cycle to execute. Use ``0`` for a new calculation; must be less than the target to
       execute cycles.
   * - ``simulation_type``
     - String; required
     - ``GEMC``, ``GCMC``, ``NPT``, or ``NVT``.
   * - ``gomc_use_CPU_or_GPU``
     - String; required
     - ``CPU`` or ``GPU``; selects GOMC, not NAMD.
   * - ``only_use_box_0_for_namd_for_gemc``
     - Boolean; required
     - For GEMC, ``true`` runs NAMD in box 0 only; ``false`` runs NAMD in both boxes.
   * - ``namd_simulation_order``
     - String; ``series``
     - ``series`` or ``parallel`` for two-NAMD-box GEMC. An explicit CLI option overrides
       this field; omitting the option preserves the JSON value.
   * - ``namd_run_steps``
     - Integer ≥ 0; required
     - MD steps per NAMD segment.
   * - ``gomc_run_steps``
     - Integer ≥ 0; required
     - MC steps per GOMC segment.
   * - ``namd_minimize_mult_scalar``
     - Integer ≥ 0; required
     - Initial minimization steps equal ``namd_run_steps * namd_minimize_mult_scalar``.

Use positive segment lengths for production. Keep segment lengths,
ensemble, topology, force fields, and templates unchanged on restart.
A start cycle of ``2`` and target count of ``5`` executes cycles 2, 3,
and 4. See :doc:`simulation_output`.

Set ``namd_simulation_order`` to ``parallel`` in JSON for concurrent NAMD
execution, or pass ``-namd_sims_order parallel`` for an explicit CLI override.
If neither supplies an order, the default is ``series``.

Thermodynamic parameters
------------------------

.. list-table::
   :header-rows: 1
   :widths: 38 22 40

   * - Parameter
     - Type / default
     - Definition
   * - ``simulation_temp_k``
     - Number > 0; required
     - Temperature in K.
   * - ``simulation_pressure_bar``
     - Number or ``null``; ``null``
     - Required and non-negative for NPT, in bar. Other ensembles may omit it or use ``null`` ;
       the workflow then supplies 1.01325 where a numeric value is needed.
   * - ``GCMC_ChemPot_or_Fugacity``
     - String or ``null``; ``null``
     - Required for GCMC: ``ChemPot`` or ``Fugacity``.
   * - ``GCMC_ChemPot_or_Fugacity_dict``
     - Object or ``null``; ``null``
     - Required for GCMC: residue names mapped to chemical potential in GOMC K units or fugacity
       in bar. Fugacity must be non-negative.

GCMC residue names must match the prepared system. Set the two GCMC
fields to ``null`` or omit them for other ensembles.

Box geometry and CPU allocation
-------------------------------

.. list-table::
   :header-rows: 1
   :widths: 38 22 40

   * - Parameter
     - Type / default
     - Definition
   * - ``no_core_box_0``
     - Integer ≥ 1; required
     - NAMD CPU cores for box 0.
   * - ``no_core_box_1``
     - Integer ≥ 0; required
     - NAMD CPU cores for box 1. Must be positive for GEMC with NAMD in both boxes; use ``0``
       for box-0-only execution.
   * - ``set_dims_box_0_list``, ``set_dims_box_1_list``
     - List or ``null``; both keys required
     - Three positive box lengths in Å, or ``null`` entries read from the corresponding PDB
       CRYST1 record. ``null`` for the whole list leaves all lengths to the PDB.
   * - ``set_angle_box_0_list``, ``set_angle_box_1_list``
     - List or ``null``; both keys required
     - Three entries, each ``90`` or ``null``. Only orthogonal boxes are supported.

For example, ``[40.0, null, null]`` sets the x length to 40 Å and reads
the remaining lengths from the PDB. Include all four geometry keys even
when a second NAMD box is not used.

Structures, force fields, and engine paths
------------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 38 22 40

   * - Parameter
     - Type / default
     - Definition
   * - ``starting_pdb_box_0_file``, ``starting_psf_box_0_file``
     - String; required
     - Paths to the initial box-0 coordinates and topology.
   * - ``starting_pdb_box_1_file``, ``starting_psf_box_1_file``
     - String or ``null``; required
     - Paths for GEMC/GCMC. Both keys must be present with value ``null`` for NVT/NPT.
   * - ``starting_ff_file_list_namd``
     - List of strings; required
     - NAMD force-field paths. Supply at least one valid parameter file.
   * - ``starting_ff_file_list_gomc``
     - List of strings; required
     - GOMC force-field paths.
   * - ``namd2_bin_directory``
     - String; required
     - Directory containing the ``namd2`` executable.
   * - ``gomc_bin_directory``
     - String; required
     - Directory containing ``GOMC_<CPU/GPU>_<ENSEMBLE>`` ; ``GOMC_CPU`` or ``GOMC_GPU`` is
       accepted as a fallback.
   * - ``path_namd_template``
     - String or ``null``; omitted by default
     - Optional shared NAMD override; otherwise selected by ensemble.
   * - ``path_namd_template_box_0``, ``path_namd_template_box_1``
     - String or ``null``; omitted by default
     - Optional GEMC per-box overrides, taking precedence over the shared override.
   * - ``path_gomc_template``
     - String or ``null``; omitted by default
     - Optional GOMC override; otherwise selected by ensemble.

Preserve the placeholders used by the distributed templates. Changes to
engine settings, time steps, and move frequencies require independent
validation of the resulting NAMD and GOMC inputs.

The NAMD and GOMC force fields must represent the same molecular model.
Verify that both installed engine versions support its interaction terms.
See :doc:`generating_systems` for consistency checks.

Output and retention
--------------------

.. list-table::
   :header-rows: 1
   :widths: 38 22 40

   * - Parameter
     - Type / default
     - Definition
   * - ``developer_mode``
     - Boolean; ``false``
     - Mirror raw engine files to the on-disk output roots. Enable before execution for the
       documented restart and standalone-analysis procedures.
   * - ``path_namd_runs``
     - String; ``NAMD``
     - On-disk NAMD output root.
   * - ``path_gomc_runs``
     - String; ``GOMC``
     - On-disk GOMC output root.
   * - ``log_dir``
     - String; ``logs``
     - Run-log directory.
   * - ``process_on_the_fly``
     - Boolean; ``false``
     - Combine selected output after each completed cycle.
   * - ``combined_data_dir``
     - String; ``combined_data``
     - Destination for on-the-fly analysis files.
   * - ``disk_cleanup_mode``
     - String; ``compact``
     - ``compact`` , ``minimal`` , or ``off`` . Controls managed storage, not developer-mode
       disk copies.
   * - ``otf_keep_raw_cycles``
     - Integer ≥ 1; ``2``
     - Recent cycle pairs retained during rolling cleanup in ``compact`` and ``minimal`` modes.

.. warning::

   With ``developer_mode`` and ``process_on_the_fly`` both set to
   ``false``, default compact cleanup leaves no raw or combined simulation data
   after successful completion. Select retention before execution.

See :doc:`fifo_output_and_developer_mode` for cleanup and failure behavior.

Trajectory processing and CPU affinity
--------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 38 22 40

   * - Parameter
     - Type / default
     - Definition
   * - ``combine_namd_dcd_file``
     - Boolean; ``true``
     - Combine NAMD DCD segments for NVT/NPT only.
   * - ``combine_gomc_dcd_file``
     - Boolean; ``true``
     - Combine GOMC DCD segments for any supported ensemble.
   * - ``combine_dcd_files_cycle_freq``
     - Integer ≥ 1; ``1``
     - Select every Nth cycle's DCD segment, counted from the start cycle. Does not select
       individual frames within a segment.
   * - ``rel_path_to_combine_binary_catdcd``
     - String; bundled binary
     - CatDCD path; see the default below.
   * - ``catdcd_core``
     - Integer or ``null``; ``null``
     - Explicit CPU core for CatDCD via ``taskset`` . Applies even when ``enable_cpu_affinity``
       is false.
   * - ``enable_cpu_affinity``
     - Boolean; ``false``
     - Without an explicit CatDCD core, select the first core following the configured NAMD core
       range.
   * - ``otf_reserved_cores``
     - Integer or ``null``; ``null``
     - Accepted but not used to reserve or select cores. Use ``catdcd_core`` for explicit
       placement.

The default CatDCD path is
``required_data/bin/catdcd-4.0b/LINUXAMD64/bin/catdcd4.0/catdcd``.
Select an executable compatible with the compute node. Any pinned CPU
must belong to the job's allocation and should lie outside NAMD's core
range.

Derived engine output intervals
-------------------------------

The configuration loader calculates the following intervals from segment
lengths. They are not independent user controls: values supplied under
these names are overwritten during configuration initialization.

.. list-table::
   :header-rows: 1
   :widths: 55 45

   * - Derived field
     - Calculated value
   * - ``namd_rst_dcd_xst_steps``
     - ``namd_run_steps``
   * - ``namd_console_blkavg_e_and_p_steps``
     - ``namd_run_steps``
   * - ``gomc_console_blkavg_hist_steps``
     - ``gomc_run_steps``
   * - ``gomc_rst_coor_ckpoint_steps``
     - ``gomc_run_steps``
   * - ``gomc_hist_sample_steps``
     - ``min(500, int(gomc_run_steps / 10))``

For ``gomc_run_steps`` below 10, the derived histogram sampling interval
is zero. Inspect the generated GOMC input and confirm that the selected
engine accepts the interval before using such a short segment. These
engine intervals are distinct from ``combine_dcd_files_cycle_freq``, which
selects complete cycles for trajectory concatenation.

Continuity checks
-----------------

.. list-table::
   :header-rows: 1
   :widths: 42 16 42

   * - Parameter
     - Default
     - Definition
   * - ``allowable_error_fraction_potential``
     - ``0.005``
     - Non-negative fractional threshold for logged potential-energy continuity checks between
       NAMD segments.
   * - ``allowable_error_fraction_vdw_plus_elec``
     - ``0.005``
     - Non-negative fractional threshold for logged VDW-plus-electrostatic continuity checks.
   * - ``max_absolute_allowable_kcal_fraction_vdw_plus_elec``
     - ``0.5``
     - Non-negative threshold in kcal/mol. Skip the fractional VDW-plus-electrostatic check
       below this magnitude to avoid a ratio near zero.

These checks report status; they do not stop a calculation. When available,
the parser uses native full-precision ``MCMD_ENERGY:`` boundary records for
the corresponding NAMD timesteps. Older logs fall back to the ordinary
``ENERGY:`` records. This avoids console-rounding errors without changing
the acceptance thresholds.

Supplied configuration
----------------------

The following file is the repository's GEMC example. It uses NAMD in
both boxes concurrently, with eight cores per NAMD box; GOMC handles both
boxes in the following stage. It requests 10,000 cycles. Replace the
machine-specific engine paths and review the cycle count before execution.
See :doc:`quick_start` for a 10-cycle check with three cores per box.

.. literalinclude:: ../user_input_NAMD_GOMC.json
   :language: json
   :linenos:
