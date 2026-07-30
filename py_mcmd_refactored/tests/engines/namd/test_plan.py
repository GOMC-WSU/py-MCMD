from __future__ import annotations

from pathlib import Path

from config.models import SimulationConfig
from engines.namd.plan import build_namd_execution_plan
from utils.subprocess_runner import Command


def make_cfg(tmp_path: Path, **kw) -> SimulationConfig:
    base = dict(
        total_cycles_namd_gomc_sims=1,
        starting_at_cycle_namd_gomc_sims=0,
        simulation_type="NPT",
        gomc_use_CPU_or_GPU="CPU",
        only_use_box_0_for_namd_for_gemc=True,
        no_core_box_0=4,
        no_core_box_1=2,
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
        namd_simulation_order="series",
    )
    base.update(kw)
    return SimulationConfig(**base)


def test_plan_single_box_uses_total_no_cores(tmp_path: Path):
    cfg = make_cfg(tmp_path, simulation_type="NPT", only_use_box_0_for_namd_for_gemc=True, no_core_box_0=5)
    plan = build_namd_execution_plan(
        cfg,
        exec_path="namd2",
        box0_dir=tmp_path / "NAMD" / "00000000_a",
        box1_dir=None,
    )
    assert plan.mode == "series"
    assert plan.box1 is None
    assert plan.box0.argv == ["namd2", f"+p{cfg.total_no_cores}", "in.conf"]


def test_plan_two_box_series_uses_total_no_cores_for_both(tmp_path: Path):
    cfg = make_cfg(
        tmp_path,
        simulation_type="GEMC",
        only_use_box_0_for_namd_for_gemc=False,
        no_core_box_0=4,
        no_core_box_1=6,
        namd_simulation_order="series",
    )
    plan = build_namd_execution_plan(
        cfg,
        exec_path="namd2",
        box0_dir=tmp_path / "NAMD" / "00000000_a",
        box1_dir=tmp_path / "NAMD" / "00000000_b",
    )
    assert plan.mode == "series"
    assert plan.box1 is not None
    assert plan.box0.argv == ["namd2", f"+p{cfg.total_no_cores}", "in.conf"]
    assert plan.box1.argv == ["namd2", f"+p{cfg.total_no_cores}", "in.conf"]


def test_plan_two_box_parallel_uses_per_box_cores(tmp_path: Path):
    cfg = make_cfg(
        tmp_path,
        simulation_type="GEMC",
        only_use_box_0_for_namd_for_gemc=False,
        no_core_box_0=4,
        no_core_box_1=6,
        namd_simulation_order="parallel",
    )
    plan = build_namd_execution_plan(
        cfg,
        exec_path="namd2",
        box0_dir=tmp_path / "NAMD" / "00000000_a",
        box1_dir=tmp_path / "NAMD" / "00000000_b",
    )
    assert plan.mode == "parallel"
    assert plan.box1 is not None
    assert plan.box0.argv == ["namd2", "+p4", "in.conf"]
    assert plan.box1.argv == ["namd2", "+p6", "in.conf"]