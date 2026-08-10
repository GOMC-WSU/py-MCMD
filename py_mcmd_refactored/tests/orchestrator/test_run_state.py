from __future__ import annotations

from pathlib import Path

from config.models import SimulationConfig
from orchestrator.state import PmeDims, RunState


def _minimal_cfg_dict() -> dict:
    """A minimal, valid config dict for constructing SimulationConfig."""
    return {
        "total_cycles_namd_gomc_sims": 1,
        "starting_at_cycle_namd_gomc_sims": 0,
        "gomc_use_CPU_or_GPU": "CPU",
        "simulation_type": "NVT",
        "only_use_box_0_for_namd_for_gemc": True,
        "no_core_box_0": 1,
        "no_core_box_1": 0,
        "simulation_temp_k": 300.0,
        "simulation_pressure_bar": 1.0,
        "GCMC_ChemPot_or_Fugacity": None,
        "GCMC_ChemPot_or_Fugacity_dict": None,
        "namd_minimize_mult_scalar": 1,
        "namd_run_steps": 10,
        "gomc_run_steps": 5,
        "set_dims_box_0_list": [10.0, 10.0, 10.0],
        "set_dims_box_1_list": [10.0, 10.0, 10.0],
        "set_angle_box_0_list": [90, 90, 90],
        "set_angle_box_1_list": [90, 90, 90],
        "starting_ff_file_list_gomc": ["ff_gomc.inp"],
        "starting_ff_file_list_namd": ["ff_namd.inp"],
        "starting_pdb_box_0_file": "box0.pdb",
        "starting_psf_box_0_file": "box0.psf",
        "starting_pdb_box_1_file": None,
        "starting_psf_box_1_file": None,
        "namd2_bin_directory": "bin/namd",
        "gomc_bin_directory": "bin/gomc",
    }


def test_run_state_defaults_from_config():
    cfg = SimulationConfig(**_minimal_cfg_dict())
    state = RunState.from_config(cfg)

    assert state.current_step == 0
    assert state.namd_box0_dir is None
    assert state.namd_box1_dir is None
    assert state.gomc_dir is None

    # PME dimensions are constructed but unset
    assert isinstance(state.pme_box0, PmeDims)
    assert state.pme_box0.as_tuple() == (None, None, None)
    assert isinstance(state.pme_box1, PmeDims)
    assert state.pme_box1.as_tuple() == (None, None, None)

    # Run0 FFT metadata unset
    assert state.run0_fft_name_box0 is None
    assert state.run0_fft_name_box1 is None
    assert state.run0_dir_box0 is None
    assert state.run0_dir_box1 is None

    # Snapshot is JSON-serializable (strings/tuples/None)
    snap = state.snapshot()
    assert snap["current_step"] == 0
    assert snap["namd_box0_dir"] is None
    assert snap["pme_box0"] == (None, None, None)


def test_run_state_allows_mutation_of_expected_fields(tmp_path: Path):
    cfg = SimulationConfig(**_minimal_cfg_dict())
    state = RunState.from_config(cfg)

    state.current_step = 123
    state.namd_box0_dir = tmp_path / "NAMD" / "00000000_a"
    state.gomc_dir = tmp_path / "GOMC" / "00000001"
    state.pme_box0 = PmeDims(x=64, y=64, z=64)
    state.run0_fft_name_box0 = "grid.txt"
    state.run0_dir_box0 = tmp_path / "NAMD" / "00000000_a"

    assert state.current_step == 123
    assert state.namd_box0_dir.name == "00000000_a"
    assert state.gomc_dir.name == "00000001"
    assert state.pme_box0.as_tuple() == (64, 64, 64)
    assert state.run0_fft_name_box0 == "grid.txt"
    assert state.run0_dir_box0.name == "00000000_a"
