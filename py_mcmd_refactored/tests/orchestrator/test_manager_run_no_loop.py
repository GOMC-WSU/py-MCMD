
from __future__ import annotations

from pathlib import Path

import pytest

from config.models import SimulationConfig
import orchestrator.manager as mgr


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


def test_orchestrator_run_no_loop_call_order_and_cycles_completed(tmp_path: Path, monkeypatch):
    calls = []

    class DummyNamd:
        def __init__(self, cfg, engine_type="NAMD", dry_run=False):
            self.cfg = cfg
            self.exec_path = "namd2"

        def run_segment(self, *, run_no: int, state):
            calls.append(("NAMD", int(run_no)))
            # mimic legacy step updates
            if int(run_no) == 0:
                state.current_step += int(self.cfg.namd_run_steps) + int(self.cfg.namd_minimize_steps)
            else:
                state.current_step += int(self.cfg.namd_run_steps)
            return {"run_no": int(run_no)}

    class DummyGomc:
        def __init__(self, cfg, engine_type="GOMC", dry_run=False):
            self.cfg = cfg
            self.exec_path = "gomc"

        def run_segment(self, *, run_no: int, state):
            calls.append(("GOMC", int(run_no)))
            state.current_step += int(self.cfg.gomc_run_steps)
            return {"run_no": int(run_no)}

    monkeypatch.setattr(mgr, "NamdEngine", DummyNamd)
    monkeypatch.setattr(mgr, "GomcEngine", DummyGomc)

    cfg = _cfg(tmp_path, starting_at_cycle_namd_gomc_sims=0, total_cycles_namd_gomc_sims=2)
    orch = mgr.SimulationOrchestrator(cfg, dry_run=True)

    summary = orch.run()

    assert calls == [("NAMD", 0), ("GOMC", 1), ("NAMD", 2), ("GOMC", 3)]
    assert summary["cycles_completed"] == 2

    expected_step = (
        (cfg.namd_run_steps + cfg.namd_minimize_steps)
        + cfg.gomc_run_steps
        + cfg.namd_run_steps
        + cfg.gomc_run_steps
    )
    assert orch.state.current_step == expected_step


def test_orchestrator_run_no_loop_applies_restart_current_step(tmp_path: Path, monkeypatch):
    calls = []

    class DummyNamd:
        def __init__(self, cfg, engine_type="NAMD", dry_run=False):
            self.cfg = cfg
            self.exec_path = "namd2"

        def run_segment(self, *, run_no: int, state):
            calls.append(("NAMD", int(run_no)))
            state.current_step += int(self.cfg.namd_run_steps)
            return {"run_no": int(run_no)}

    class DummyGomc:
        def __init__(self, cfg, engine_type="GOMC", dry_run=False):
            self.cfg = cfg
            self.exec_path = "gomc"

        def run_segment(self, *, run_no: int, state):
            calls.append(("GOMC", int(run_no)))
            state.current_step += int(self.cfg.gomc_run_steps)
            return {"run_no": int(run_no)}

    monkeypatch.setattr(mgr, "NamdEngine", DummyNamd)
    monkeypatch.setattr(mgr, "GomcEngine", DummyGomc)

    # start at cycle 1 -> starting_sims=2, total_sims=4 -> run_no: 2,3
    cfg = _cfg(tmp_path, starting_at_cycle_namd_gomc_sims=1, total_cycles_namd_gomc_sims=2)
    orch = mgr.SimulationOrchestrator(cfg, dry_run=True)

    summary = orch.run()

    assert calls == [("NAMD", 2), ("GOMC", 3)]
    assert summary["cycles_completed"] == 1

    restart_base = (cfg.namd_run_steps + cfg.gomc_run_steps) * cfg.starting_at_cycle_namd_gomc_sims + cfg.namd_minimize_steps
    expected = restart_base + cfg.namd_run_steps + cfg.gomc_run_steps
    assert orch.state.current_step == expected