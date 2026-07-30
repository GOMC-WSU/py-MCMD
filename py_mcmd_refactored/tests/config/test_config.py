import sys
sys.path.insert(0, "/home/arsalan/wsu-gomc/py-MCMD-hm/py_mcmd_refactored")

import pytest
from pathlib import Path
import json
from pydantic import ValidationError


from config.models import load_simulation_config, SimulationConfig
# ---- helpers ----
def repo_root() -> Path:
    # test file is at: <repo>/py_mcmd_refactored/tests/test_config.py
    # parents[0]=.../tests, [1]=.../py_mcmd_refactored, [2]=<repo>
    return Path(__file__).resolve().parents[3]

def make_cfg(**overrides) -> SimulationConfig:
    base = dict(
        total_cycles_namd_gomc_sims=3,
        starting_at_cycle_namd_gomc_sims=0,
        gomc_use_CPU_or_GPU="CPU",
        simulation_type="NPT",
        only_use_box_0_for_namd_for_gemc=True,
        no_core_box_0=4,
        no_core_box_1=0,
        simulation_temp_k=250,
        simulation_pressure_bar=1.0,
        GCMC_ChemPot_or_Fugacity="ChemPot",
        GCMC_ChemPot_or_Fugacity_dict={"TIP3": -1000, "WAT": -2000},
        namd_minimize_mult_scalar=1,
        namd_run_steps=200,
        gomc_run_steps=20,
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
        namd2_bin_directory="../NAMD_2.14_Linux-x86_64-multicore",
        gomc_bin_directory="../GOMC/bin",
    )
    base.update(overrides)
    return SimulationConfig(**base)

def with_two_box(cfg_kwargs):
    cfg_kwargs.setdefault("no_core_box_1", 1)
    return cfg_kwargs

def test_load_config():
    # Resolve the JSON file path *relative* to the project root
    project_root = Path(__file__).parent.parent.parent
    # config_path = project_root / "user_input_NAMD_GOMC.json"
    config_path = repo_root() / "user_input_NAMD_GOMC.json"
    # sanity check
    assert config_path.exists(), f"Config not found at {config_path}"
    cfg = load_simulation_config(config_path)
    assert isinstance(cfg, SimulationConfig)
    # spot‐check a value you know exists
    assert cfg.total_cycles_namd_gomc_sims > 0


# ---- tolerances defaults & overrides ----
def test_tolerances_defaults():
    cfg = make_cfg()
    assert cfg.allowable_error_fraction_vdw_plus_elec == pytest.approx(5e-3)
    assert cfg.allowable_error_fraction_potential == pytest.approx(5e-3)
    assert cfg.max_absolute_allowable_kcal_fraction_vdw_plus_elec == pytest.approx(0.5)


def test_tolerances_overrides():
    cfg = make_cfg(
        allowable_error_fraction_vdw_plus_elec=1e-2,
        allowable_error_fraction_potential=2e-2,
        max_absolute_allowable_kcal_fraction_vdw_plus_elec=0.75,
    )
    assert cfg.allowable_error_fraction_vdw_plus_elec == pytest.approx(1e-2)
    assert cfg.allowable_error_fraction_potential == pytest.approx(2e-2)
    assert cfg.max_absolute_allowable_kcal_fraction_vdw_plus_elec == pytest.approx(0.75)


# ---- derived per-engine params ----
def test_derived_params_basic():
    cfg = make_cfg()  # namd_run_steps=200, gomc_run_steps=20
    # GOMC
    assert cfg.gomc_console_blkavg_hist_steps == 20
    assert cfg.gomc_rst_coor_ckpoint_steps == 20
    assert cfg.gomc_hist_sample_steps == 2  # 20/10 = 2 < 500
    # NAMD
    assert cfg.namd_rst_dcd_xst_steps == 200
    assert cfg.namd_console_blkavg_e_and_p_steps == 200


@pytest.mark.parametrize(
    "gomc_steps, expected_hist_sample",
    [
        (10, 1),          # 10/10 = 1
        (100, 10),        # 100/10 = 10
        (5000, 500),      # 5000/10 = 500 → boundary
        (6000, 500),      # 6000/10 = 600 → capped at 500
        (0, 0),           # guard for zero
        (1, 0),           # int(1/10) = 0
        (9, 0),           # int(9/10) = 0
    ],
)
def test_gomc_hist_sample_rule(gomc_steps, expected_hist_sample):
    cfg = make_cfg(gomc_run_steps=gomc_steps)
    assert cfg.gomc_hist_sample_steps == expected_hist_sample


def test_zero_steps_edge_cases():
    cfg = make_cfg(namd_run_steps=0, gomc_run_steps=0)
    assert cfg.namd_rst_dcd_xst_steps == 0
    assert cfg.namd_console_blkavg_e_and_p_steps == 0
    assert cfg.gomc_console_blkavg_hist_steps == 0
    assert cfg.gomc_rst_coor_ckpoint_steps == 0
    assert cfg.gomc_hist_sample_steps == 0


def test_load_from_json_constructor_logic(tmp_path: Path):
    # Ensure load_simulation_config applies constructor-derived values
    data = make_cfg().model_dump()  # Pydantic v2
    data["gomc_run_steps"] = 6000  # should cap hist_sample at 500
    json_path = tmp_path / "user_input.json"
    json_path.write_text(json.dumps(data, indent=2))

    cfg = load_simulation_config(str(json_path))
    assert cfg.gomc_run_steps == 6000
    assert cfg.gomc_hist_sample_steps == 500

def test_run_dir_defaults_and_override(tmp_path):
    from py_mcmd_refactored.config.models import load_simulation_config

    # defaults
    cfg1 = make_cfg()
    assert cfg1.path_namd_runs == "NAMD"
    assert cfg1.path_gomc_runs == "GOMC"

    # json override
    data = make_cfg().model_dump()
    data["path_namd_runs"] = "NAMD_TEST"
    data["path_gomc_runs"] = "GOMC_TEST"
    p = tmp_path / "user_input.json"
    p.write_text(json.dumps(data))
    cfg2 = load_simulation_config(str(p))
    assert cfg2.path_namd_runs == "NAMD_TEST"
    assert cfg2.path_gomc_runs == "GOMC_TEST"

def test_template_paths_derived_and_overridable(tmp_path):
    # default derivation from simulation_type
    cfg = make_cfg(simulation_type="NPT")
    assert cfg.path_namd_template == "required_data/config_files/NAMD.conf"
    assert cfg.path_gomc_template == "required_data/config_files/GOMC_NPT.conf"

    # JSON override still respected
    data = make_cfg(simulation_type="NVT").model_dump()
    data["path_namd_template"] = "custom/NAMD_custom.conf"
    data["path_gomc_template"] = "custom/GOMC_custom.conf"
    p = tmp_path / "user_input.json"
    p.write_text(json.dumps(data))
    cfg2 = load_simulation_config(str(p))
    assert cfg2.path_namd_template == "custom/NAMD_custom.conf"
    assert cfg2.path_gomc_template == "custom/GOMC_custom.conf"

def test_template_paths_only_derived_when_missing():
    data = make_cfg(simulation_type="NVT").model_dump()
    data["path_namd_template"] = None
    data["path_gomc_template"] = None
    cfg = SimulationConfig(**data)
    assert cfg.path_namd_template == "required_data/config_files/NAMD.conf"
    assert cfg.path_gomc_template == "required_data/config_files/GOMC_NVT.conf"

def test_ff_lists_accept_valid_strings():
    cfg = make_cfg(
        starting_ff_file_list_gomc=["a.inp", "b.inp"],
        starting_ff_file_list_namd=["c.inp"]
    )
    assert cfg.starting_ff_file_list_gomc == ["a.inp", "b.inp"]
    assert cfg.starting_ff_file_list_namd == ["c.inp"]

def test_ff_lists_reject_non_list():
    with pytest.raises((ValidationError, TypeError)):
        make_cfg(starting_ff_file_list_gomc="not-a-list")

def test_ff_lists_reject_non_string_items():
    with pytest.raises((ValidationError, TypeError)):
        make_cfg(starting_ff_file_list_namd=["ok.inp", 123])

def test_gcmc_requires_fields_and_types():
    # Missing dict
    with pytest.raises((ValidationError, TypeError)):
        make_cfg(simulation_type="GCMC", GCMC_ChemPot_or_Fugacity="ChemPot",
                 GCMC_ChemPot_or_Fugacity_dict=None)

    # Bad dict types
    with pytest.raises((ValidationError, TypeError)):
        make_cfg(simulation_type="GCMC", GCMC_ChemPot_or_Fugacity="ChemPot",
                 GCMC_ChemPot_or_Fugacity_dict={"TIP3": "not-a-number"})

    # Bad key type
    with pytest.raises((ValidationError, TypeError)):
        make_cfg(simulation_type="GCMC", GCMC_ChemPot_or_Fugacity="ChemPot",
                 GCMC_ChemPot_or_Fugacity_dict={1: -1000})

def test_gcmc_fugacity_requires_non_negative():
    with pytest.raises((ValidationError, ValueError)):
        make_cfg(simulation_type="GCMC", GCMC_ChemPot_or_Fugacity="Fugacity",
                 GCMC_ChemPot_or_Fugacity_dict={"WAT": -0.1})

    # OK: Fugacity with non-negative values
    cfg = make_cfg(simulation_type="GCMC",
                no_core_box_1=1,  # GCMC requires box1 >= 1
                GCMC_ChemPot_or_Fugacity="Fugacity",
                GCMC_ChemPot_or_Fugacity_dict={"WAT": 0.0})
    
    assert cfg.GCMC_ChemPot_or_Fugacity_dict["WAT"] == 0.0

def test_npt_pressure_required_and_non_negative():
    with pytest.raises((ValidationError, TypeError)):
        make_cfg(simulation_type="NPT", simulation_pressure_bar=None)
    with pytest.raises((ValidationError, ValueError)):
        make_cfg(simulation_type="NPT", simulation_pressure_bar=-1.0)

    cfg = make_cfg(simulation_type="NPT", simulation_pressure_bar=0.0)
    assert cfg.simulation_pressure_bar == 0.0

def test_non_npt_pressure_defaults_to_atmospheric():
    cfg = make_cfg(simulation_type="NVT", simulation_pressure_bar=None)
    assert cfg.simulation_pressure_bar == 1.01325

    cfg2 = make_cfg(simulation_type="GEMC", 
                    no_core_box_1=1,           # GEMC requires box1 >= 1
                    simulation_pressure_bar=None)
    assert cfg2.simulation_pressure_bar == 1.01325

def test_minimize_steps_derivation():
    cfg = make_cfg(namd_run_steps=200, namd_minimize_mult_scalar=3)
    assert cfg.namd_minimize_steps == 600

def test_log_dir_default(tmp_path, monkeypatch):
    # ensure orchestrator creates logs/<file>
    from py_mcmd_refactored.orchestrator.manager import SimulationOrchestrator
    cfg = make_cfg()
    cfg.log_dir = str(tmp_path / "logs_test")
    orch = SimulationOrchestrator(cfg, dry_run=True)
    assert (tmp_path / "logs_test" / f"NAMD_GOMC_started_at_cycle_No_{cfg.starting_at_cycle_namd_gomc_sims}.log").exists()

def test_core_derivation_gemc_both_boxes():
    cfg = make_cfg(simulation_type="GEMC", only_use_box_0_for_namd_for_gemc=False,
                   no_core_box_0=4, no_core_box_1=2)
    assert cfg.effective_no_core_box_1 == 2
    assert cfg.total_no_cores == 6

def test_core_derivation_gemc_only_box0():
    cfg = make_cfg(simulation_type="GEMC", only_use_box_0_for_namd_for_gemc=True,
                   no_core_box_0=4, no_core_box_1=2)
    assert cfg.effective_no_core_box_1 == 0
    assert cfg.total_no_cores == 4

def test_core_derivation_non_gemc_ignores_box1():
    cfg = make_cfg(simulation_type="NPT", no_core_box_0=8, no_core_box_1=4)
    assert cfg.effective_no_core_box_1 == 0
    assert cfg.total_no_cores == 8

def test_no_core_box0_must_be_int_and_nonzero():
    with pytest.raises((ValidationError, TypeError)):
        make_cfg(no_core_box_0="4")  # not int
    with pytest.raises((ValidationError, ValueError)):
        make_cfg(no_core_box_0=0)    # zero not allowed
    cfg = make_cfg(no_core_box_0=2)  # ok
    assert cfg.no_core_box_0 == 2

def test_no_core_box1_must_be_int_ge0():
    with pytest.raises((ValidationError, TypeError)):
        make_cfg(no_core_box_1="2")  # not int
    cfg = make_cfg(no_core_box_1=0)  # ok
    assert cfg.no_core_box_1 == 0

# @pytest.mark.parametrize("ensemble", ["GEMC", "GCMC"])
# def test_box1_required_for_two_box_ensembles(ensemble):
#     with pytest.raises((ValidationError, ValueError)):
#         make_cfg(simulation_type=ensemble, no_core_box_1=0)  # must be >=1
#     cfg = make_cfg(simulation_type=ensemble, no_core_box_1=2)
#     assert cfg.no_core_box_1 == 2


# GCMC
#     no_core_box_1 = 0
#     VALID

# GEMC + only_use_box_0_for_namd_for_gemc=True
#     no_core_box_1 = 0
#     VALID

# GEMC + only_use_box_0_for_namd_for_gemc=False
#     no_core_box_1 = 0
#     INVALID"
def test_box1_required_for_two_box_gemc():
    with pytest.raises((ValidationError, ValueError)):
        make_cfg(
            simulation_type="GEMC",
            only_use_box_0_for_namd_for_gemc=False,
            no_core_box_1=0,
        )

    cfg = make_cfg(
        simulation_type="GEMC",
        only_use_box_0_for_namd_for_gemc=False,
        no_core_box_1=2,
    )
    assert cfg.no_core_box_1 == 2


def test_box1_may_be_zero_for_gcmc_and_one_box_gemc():
    gcmc_cfg = make_cfg(
        simulation_type="GCMC",
        no_core_box_1=0,
    )
    assert gcmc_cfg.no_core_box_1 == 0

    gemc_cfg = make_cfg(
        simulation_type="GEMC",
        only_use_box_0_for_namd_for_gemc=True,
        no_core_box_1=0,
    )
    assert gemc_cfg.no_core_box_1 == 0

@pytest.mark.parametrize("ensemble", ["NVT", "NPT"])
def test_box1_may_be_zero_for_single_box_ensembles(ensemble):
    cfg = make_cfg(simulation_type=ensemble, no_core_box_1=0)
    assert cfg.no_core_box_1 == 0

def test_total_and_starting_sims_are_derived():
    # 2 segments per cycle (NAMD+GOMC) → 5 cycles -> 10 sims, start at 2 -> 4
    cfg = make_cfg(
        total_cycles_namd_gomc_sims=5,
        starting_at_cycle_namd_gomc_sims=2,
    )
    assert cfg.total_sims_namd_gomc == 10
    assert cfg.starting_sims_namd_gomc == 4


def test_total_and_starting_sims_dump():
    cfg = make_cfg(
        total_cycles_namd_gomc_sims=3,
        starting_at_cycle_namd_gomc_sims=1,
    )
    dumped = cfg.model_dump()
    assert dumped["total_sims_namd_gomc"] == 6
    assert dumped["starting_sims_namd_gomc"] == 2

def test_load_config_defaults_developer_mode_to_false(tmp_path: Path):
    data = make_cfg().model_dump()
    data.pop("developer_mode", None)
    json_path = tmp_path / "user_input.json"
    json_path.write_text(json.dumps(data, indent=2))

    cfg = load_simulation_config(str(json_path))
    assert cfg.developer_mode is False


def test_load_config_reads_explicit_developer_mode_true(tmp_path: Path):
    data = make_cfg().model_dump()
    data["developer_mode"] = True
    json_path = tmp_path / "user_input.json"
    json_path.write_text(json.dumps(data, indent=2))

    cfg = load_simulation_config(str(json_path))
    assert cfg.developer_mode is True