from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from config.models import SimulationConfig
from engines.namd_engine import NamdEngine
from engines.namd.plan import build_namd_execution_plan


@dataclass
class DummyHandle:
    pid: int


class DummyRunner:
    def __init__(self):
        self.calls = []
        self._pid = 100

    def start(self, cmd):
        self.calls.append(("start", cmd.argv, str(cmd.cwd)))
        self._pid += 1
        return DummyHandle(pid=self._pid)

    def wait(self, handle):
        self.calls.append(("wait", handle.pid))
        return 0


def make_cfg(tmp_path: Path, **kw) -> SimulationConfig:
    base = dict(
        total_cycles_namd_gomc_sims=1,
        starting_at_cycle_namd_gomc_sims=0,
        simulation_type="GEMC",
        gomc_use_CPU_or_GPU="CPU",
        only_use_box_0_for_namd_for_gemc=False,
        no_core_box_0=2,
        no_core_box_1=3,
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


def test_execute_plan_series_runs_sequentially(tmp_path: Path):
    cfg = make_cfg(tmp_path, namd_simulation_order="series")
    eng = NamdEngine(cfg, dry_run=True)
    eng.exec_path = Path("namd2")  # make deterministic
    eng.runner = DummyRunner()

    plan = build_namd_execution_plan(
        cfg,
        exec_path="namd2",
        box0_dir=tmp_path / "NAMD" / "00000000_a",
        box1_dir=tmp_path / "NAMD" / "00000000_b",
    )
    eng.execute_plan(plan)

    # series: start0 wait0 start1 wait1
    assert [c[0] for c in eng.runner.calls] == ["start", "wait", "start", "wait"]


def test_execute_plan_parallel_starts_both_then_waits(tmp_path: Path):
    cfg = make_cfg(tmp_path, namd_simulation_order="parallel")
    eng = NamdEngine(cfg, dry_run=True)
    eng.exec_path = Path("namd2")
    eng.runner = DummyRunner()

    plan = build_namd_execution_plan(
        cfg,
        exec_path="namd2",
        box0_dir=tmp_path / "NAMD" / "00000000_a",
        box1_dir=tmp_path / "NAMD" / "00000000_b",
    )
    eng.execute_plan(plan)

    # parallel: start0 start1 wait0 wait1
    assert [c[0] for c in eng.runner.calls] == ["start", "start", "wait", "wait"]