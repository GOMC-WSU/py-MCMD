from __future__ import annotations

from pathlib import Path
import orchestrator.manager as mgr
from config.models import SimulationConfig


def _cfg(tmp_path: Path, **overrides) -> SimulationConfig:
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
        set_dims_box_1_list=[25.0, 25.0, 25.0],
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


def test_time_stats_header_once_and_data_per_cycle(tmp_path: Path, monkeypatch):
    # perf_counter ticks:
    # cycle0 start=0 end=20  -> total=20
    # cycle1 start=100 end=130 -> total=30
    ticks = iter([0.0, 20.0, 100.0, 130.0])
    monkeypatch.setattr(mgr.time, "perf_counter", lambda: next(ticks))

    class DummyNamd:
        def __init__(self, cfg, engine_type="NAMD", dry_run=False):
            self.cfg = cfg
            self.exec_path = "namd2"  # <-- required by orchestrator init/logging

        def run_segment(self, *, run_no: int, state):
            state.timings.max_namd_cycle_time_s = 10.0

    class DummyGomc:
        def __init__(self, cfg, engine_type="GOMC", dry_run=False):
            self.cfg = cfg
            self.exec_path = "gomc"  # <-- keep symmetrical; may also be logged

        def run_segment(self, *, run_no: int, state):
            state.timings.gomc_cycle_time_s = 5.0

    monkeypatch.setattr(mgr, "NamdEngine", DummyNamd)
    monkeypatch.setattr(mgr, "GomcEngine", DummyGomc)

    cfg = _cfg(tmp_path)
    orch = mgr.SimulationOrchestrator(cfg, dry_run=True)
    summary = orch.run()

    lines = summary["time_stats_lines"]
    assert len(lines) == 3  # header + 2 data lines
    assert "TIME_STATS_TITLE" in lines[0]
    assert "TIME_STATS_DATA" in lines[1]
    assert "TIME_STATS_DATA" in lines[2]

    # Cycle 0: total=20, namd=10, gomc=5 => python_only=5
    assert "\t0\t\t10.0\t\t5.0\t\t5.0\t\t20.0" in lines[1]
    # Cycle 1: total=30, namd=10, gomc=5 => python_only=15
    assert "\t1\t\t10.0\t\t5.0\t\t15.0\t\t30.0" in lines[2]