import sys
sys.path.insert(0, "/home/arsalan/wsu-gomc/py-MCMD-hm/py_mcmd_refactored")

import pytest
from pathlib import Path

from orchestrator.manager import SimulationOrchestrator
from config.models import SimulationConfig


def make_cfg_for_orch(tmp_path: Path, **overrides) -> SimulationConfig:
    base = dict(
        total_cycles_namd_gomc_sims=2,
        starting_at_cycle_namd_gomc_sims=1,
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


def test_orchestrator_consumes_config_derived_sims(tmp_path: Path, monkeypatch):
    cfg = make_cfg_for_orch(
        tmp_path,
        total_cycles_namd_gomc_sims=3,
        starting_at_cycle_namd_gomc_sims=2,
    )

    # Sanity on derived fields (from SimulationConfig, not recomputed)
    assert cfg.total_sims_namd_gomc == 6
    assert cfg.starting_sims_namd_gomc == 4

    orch = SimulationOrchestrator(cfg, dry_run=True)

    # IMPORTANT: orchestrator now calls run_segment(), not run_steps()
    monkeypatch.setattr(orch.namd, "run_segment", lambda **kwargs: None, raising=True)
    monkeypatch.setattr(orch.gomc, "run_segment", lambda **kwargs: None, raising=True)

    summary = orch.run()

    assert summary["total_sims_namd_gomc"] == 6
    assert summary["starting_sims_namd_gomc"] == 4

    assert orch.total_sims_namd_gomc == cfg.total_sims_namd_gomc
    assert orch.starting_sims_namd_gomc == cfg.starting_sims_namd_gomc

    # Smoke: init should have created these
    assert (tmp_path / "logs").exists()
    assert (tmp_path / "NAMD").exists()
    assert (tmp_path / "GOMC").exists()


def test_orchestrator_propagates_namd_simulation_order(tmp_path: Path):
    cfg = make_cfg_for_orch(tmp_path, namd_simulation_order="parallel")
    orch = SimulationOrchestrator(cfg, dry_run=True)
    assert orch.namd_simulation_order == "parallel"


def test_orchestrator_defaults_namd_simulation_order_to_series(tmp_path: Path):
    cfg = make_cfg_for_orch(tmp_path)
    orch = SimulationOrchestrator(cfg, dry_run=True)
    assert orch.namd_simulation_order == "series"


def test_orchestrator_initializes_run_state(tmp_path: Path, monkeypatch):
    # Set start_cycle=0 so run() does not apply restart current_step bump.
    cfg = make_cfg_for_orch(tmp_path, starting_at_cycle_namd_gomc_sims=0, total_cycles_namd_gomc_sims=1)
    orch = SimulationOrchestrator(cfg, dry_run=True)

    assert hasattr(orch, "state")
    assert orch.state.current_step == 0

    # Prevent engine file/template access
    monkeypatch.setattr(orch.namd, "run_segment", lambda **kwargs: None, raising=True)
    monkeypatch.setattr(orch.gomc, "run_segment", lambda **kwargs: None, raising=True)

    summary = orch.run()
    assert "state" in summary
    assert summary["state"]["current_step"] == 0