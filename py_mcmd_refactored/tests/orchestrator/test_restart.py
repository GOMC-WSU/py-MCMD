from __future__ import annotations

from pathlib import Path

from config.models import SimulationConfig
from orchestrator.restart import compute_start_context


def _base_cfg(tmp_path: Path, **overrides) -> SimulationConfig:
    base = dict(
        total_cycles_namd_gomc_sims=2,
        starting_at_cycle_namd_gomc_sims=0,
        gomc_use_CPU_or_GPU="CPU",
        simulation_type="NPT",
        only_use_box_0_for_namd_for_gemc=True,
        no_core_box_0=1,
        no_core_box_1=0,
        simulation_temp_k=250,
        simulation_pressure_bar=1.0,
        GCMC_ChemPot_or_Fugacity="ChemPot",
        GCMC_ChemPot_or_Fugacity_dict={"WAT": -2000},
        namd_minimize_mult_scalar=1,
        namd_run_steps=10,
        gomc_run_steps=5,
        set_dims_box_0_list=[25.0, 25.0, 25.0],
        set_dims_box_1_list=[25, 25, 25],
        set_angle_box_0_list=[90, 90, 90],
        set_angle_box_1_list=[90, 90, 90],
        starting_ff_file_list_gomc=["required_data/input/OPC_FF_GOMC.inp"],
        starting_ff_file_list_namd=["required_data/input/OPC_FF_NAMD.inp"],
        starting_pdb_box_0_file="required_data/input/OPC_equil_BOX_0_restart.pdb",
        starting_psf_box_0_file="required_data/input/OPC_equil_BOX_0_restart.psf",
        starting_pdb_box_1_file="required_data/equilb_box_298K/TIPS3P_reservoir_box_1.pdb",
        starting_psf_box_1_file="required_data/equilb_box_298K/TIPS3P_reservoir_box_1.psf",
        namd2_bin_directory=str(tmp_path / "bin_namd"),
        gomc_bin_directory=str(tmp_path / "bin_gomc"),
        path_namd_runs=str(tmp_path / "NAMD"),
        path_gomc_runs=str(tmp_path / "GOMC"),
        log_dir=str(tmp_path / "logs"),
    )
    base.update(overrides)
    return SimulationConfig(**base)


def test_compute_start_context_new_start(tmp_path: Path):
    cfg = _base_cfg(tmp_path, starting_at_cycle_namd_gomc_sims=0)
    ctx = compute_start_context(cfg, id_width=8)

    assert ctx.current_step == 0
    assert ctx.previous_namd_box0_dir is None
    assert ctx.previous_gomc_dir is None
    assert ctx.previous_namd_box1_dir is None


def test_compute_start_context_restart_cycle1(tmp_path: Path):
    cfg = _base_cfg(tmp_path, starting_at_cycle_namd_gomc_sims=1)
    # namd_minimize_steps = namd_run_steps * mult = 10
    # current_step = (10+5)*1 + 10 = 25
    ctx = compute_start_context(cfg, id_width=8)

    assert ctx.current_step == 25
    assert ctx.previous_namd_box0_dir == (tmp_path / "NAMD" / "00000000_a")
    assert ctx.previous_gomc_dir == (tmp_path / "GOMC" / "00000001")
    assert ctx.previous_namd_box1_dir is None


def test_compute_start_context_restart_cycle1_two_box_gemc(tmp_path: Path):
    cfg = _base_cfg(
        tmp_path,
        starting_at_cycle_namd_gomc_sims=1,
        simulation_type="GEMC",
        only_use_box_0_for_namd_for_gemc=False,
        no_core_box_1=1,
    )
    ctx = compute_start_context(cfg, id_width=8)

    assert ctx.previous_namd_box0_dir == (tmp_path / "NAMD" / "00000000_a")
    assert ctx.previous_namd_box1_dir == (tmp_path / "NAMD" / "00000000_b")
    assert ctx.previous_gomc_dir == (tmp_path / "GOMC" / "00000001")