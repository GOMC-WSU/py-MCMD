from __future__ import annotations

from pathlib import Path

from config.models import SimulationConfig
from orchestrator.manager import SimulationOrchestrator


def make_cfg(tmp_path: Path, **kw) -> SimulationConfig:
    base = dict(
        total_cycles_namd_gomc_sims=1,
        starting_at_cycle_namd_gomc_sims=0,
        simulation_type="NPT",
        gomc_use_CPU_or_GPU="CPU",
        only_use_box_0_for_namd_for_gemc=True,
        no_core_box_0=1,
        no_core_box_1=0,
        simulation_temp_k=298.15,
        simulation_pressure_bar=1.0,
        namd_minimize_mult_scalar=1,
        namd_run_steps=10,
        gomc_run_steps=10,
        set_dims_box_0_list=[25, 25, 25],
        set_angle_box_0_list=[90, 90, 90],
        set_dims_box_1_list=[25, 25, 25],
        set_angle_box_1_list=[90, 90, 90],
        starting_ff_file_list_gomc=["a.inp"],
        starting_ff_file_list_namd=["b.inp"],
        starting_pdb_box_0_file="box0.pdb",
        starting_psf_box_0_file="box0.psf",
        starting_pdb_box_1_file="box1.pdb",
        starting_psf_box_1_file="box1.psf",
        namd2_bin_directory=str(tmp_path / "bin_namd"),
        gomc_bin_directory=str(tmp_path / "bin_gomc"),
        path_namd_runs=str(tmp_path / "NAMD"),
        path_gomc_runs=str(tmp_path / "GOMC"),
        log_dir=str(tmp_path / "logs"),
    )
    base.update(kw)
    return SimulationConfig(**base)


def test_refresh_pme_dims_from_run0_sets_box0_when_present(tmp_path: Path):
    cfg = make_cfg(tmp_path)

    run0_dir = tmp_path / "NAMD" / "0000000000_a"
    run0_dir.mkdir(parents=True, exist_ok=True)
    (run0_dir / "out.dat").write_text("Info: PME GRID DIMENSIONS 48 50 52\n")

    orch = SimulationOrchestrator(cfg, dry_run=True)
    orch.refresh_pme_dims_from_run0()

    assert orch.state.pme_box0.as_tuple() == (48, 50, 52)


def test_refresh_pme_dims_from_run0_leaves_none_when_missing(tmp_path: Path):
    cfg = make_cfg(tmp_path)
    orch = SimulationOrchestrator(cfg, dry_run=True)

    orch.refresh_pme_dims_from_run0()

    assert orch.state.pme_box0.as_tuple() == (None, None, None)
    assert orch.state.pme_box1.as_tuple() == (None, None, None)


def test_refresh_pme_dims_from_run0_sets_box1_for_two_box_gemc(tmp_path: Path):
    cfg = make_cfg(
        tmp_path,
        simulation_type="GEMC",
        only_use_box_0_for_namd_for_gemc=False,
        no_core_box_1=1,
    )

    run0_a = tmp_path / "NAMD" / "0000000000_a"
    run0_b = tmp_path / "NAMD" / "0000000000_b"
    run0_a.mkdir(parents=True, exist_ok=True)
    run0_b.mkdir(parents=True, exist_ok=True)
    (run0_a / "out.dat").write_text("Info: PME GRID DIMENSIONS 64 64 64\n")
    (run0_b / "out.dat").write_text("Info: PME GRID DIMENSIONS 32 40 48\n")

    orch = SimulationOrchestrator(cfg, dry_run=True)
    orch.refresh_pme_dims_from_run0()

    assert orch.state.pme_box0.as_tuple() == (64, 64, 64)
    assert orch.state.pme_box1.as_tuple() == (32, 40, 48)