import sys

sys.path.insert(0, "/home/arsalan/wsu-gomc/py-MCMD-hm/py_mcmd_refactored")


import json

import pytest
from config.models import SimulationConfig, load_simulation_config
from pydantic import ValidationError


# Helper: minimal valid configuration as a Python dict
def minimal_config():
    return {
        "total_cycles_namd_gomc_sims": 2,
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
        "namd_minimize_mult_scalar": 2,
        "namd_run_steps": 100,
        "gomc_run_steps": 100,
        "set_dims_box_0_list": [10.0, 10.0, 10.0],
        "set_dims_box_1_list": [10.0, 10.0, 10.0],
        "set_angle_box_0_list": [90, 90, 90],
        "set_angle_box_1_list": [90, 90, 90],
        "starting_ff_file_list_gomc": ["ff1.dat"],
        "starting_ff_file_list_namd": ["ff2.dat"],
        "starting_pdb_box_0_file": "box0.pdb",
        "starting_psf_box_0_file": "box0.psf",
        "starting_pdb_box_1_file": None,
        "starting_psf_box_1_file": None,
        "namd2_bin_directory": "bin/namd",
        "gomc_bin_directory": "bin/gomc",
    }


def test_valid_minimal_config(tmp_path):
    # Write JSON to temporary file
    cfg_path = tmp_path / "cfg.json"
    cfg_path.write_text(json.dumps(minimal_config()))

    # Should load without errors
    cfg = load_simulation_config(str(cfg_path))
    assert isinstance(cfg, SimulationConfig)
    assert cfg.total_cycles_namd_gomc_sims == 2
    # Lists normalized
    assert cfg.set_dims_box_0_list == [10.0, 10.0, 10.0]
    assert cfg.set_angle_box_1_list == [90, 90, 90]


def test_negative_cycles_raises():
    data = minimal_config()
    data["total_cycles_namd_gomc_sims"] = -1
    with pytest.raises(ValidationError) as exc:
        SimulationConfig(**data)
    assert "total_cycles_namd_gomc_sims" in str(exc.value)


def test_invalid_gomc_device():
    data = minimal_config()
    data["gomc_use_CPU_or_GPU"] = "TPU"
    with pytest.raises(ValidationError):
        SimulationConfig(**data)


def test_invalid_simulation_type():
    data = minimal_config()
    data["simulation_type"] = "FOO"
    with pytest.raises(ValidationError):
        SimulationConfig(**data)


def test_dims_list_length():
    data = minimal_config()
    data["set_dims_box_0_list"] = [1.0, 2.0]  # wrong length
    with pytest.raises(ValidationError):
        SimulationConfig(**data)


def test_angle_list_invalid_value():
    data = minimal_config()
    data["set_angle_box_1_list"] = [90, 60, 90]
    with pytest.raises(ValidationError):
        SimulationConfig(**data)


def test_gemc_requires_two_box_cores():
    data = minimal_config()
    data["simulation_type"] = "GEMC"
    data["only_use_box_0_for_namd_for_gemc"] = False
    data["no_core_box_1"] = 0
    with pytest.raises(ValueError) as exc:
        SimulationConfig(**data)
    assert "no_core_box_1 must be > 0" in str(exc.value)


def test_npt_pressure_negative():
    data = minimal_config()
    data["simulation_type"] = "NPT"
    data["simulation_pressure_bar"] = -5.0
    with pytest.raises(ValueError):
        SimulationConfig(**data)


def test_gcmc_missing_fields():
    data = minimal_config()
    data["simulation_type"] = "GCMC"
    # Remove chempot fields
    data["GCMC_ChemPot_or_Fugacity"] = None
    data["GCMC_ChemPot_or_Fugacity_dict"] = None
    with pytest.raises(ValueError):
        SimulationConfig(**data)


def test_gcmc_negative_fugacity_value():
    data = minimal_config()
    data["simulation_type"] = "GCMC"
    data["GCMC_ChemPot_or_Fugacity"] = "Fugacity"
    data["GCMC_ChemPot_or_Fugacity_dict"] = {"x": -1.0}
    with pytest.raises(ValueError):
        SimulationConfig(**data)


def test_namd_simulation_order_default_is_series():
    cfg = SimulationConfig(**minimal_config())
    assert cfg.namd_simulation_order == "series"


def test_namd_simulation_order_accepts_parallel():
    data = minimal_config()
    data["namd_simulation_order"] = "parallel"
    cfg = SimulationConfig(**data)
    assert cfg.namd_simulation_order == "parallel"


def test_namd_simulation_order_rejects_invalid_value():
    data = minimal_config()
    data["namd_simulation_order"] = "not-a-real-mode"
    with pytest.raises(ValidationError):
        SimulationConfig(**data)


def test_developer_mode_defaults_to_false_when_absent():
    cfg = SimulationConfig(**minimal_config())
    assert cfg.developer_mode is False


def test_developer_mode_accepts_true_bool():
    data = minimal_config()
    data["developer_mode"] = True
    cfg = SimulationConfig(**data)
    assert cfg.developer_mode is True


def test_developer_mode_rejects_non_bool_values():
    data = minimal_config()
    data["developer_mode"] = "true"
    with pytest.raises(ValidationError):
        SimulationConfig(**data)


def test_runtime_cleanup_and_otf_fields_default_values():
    cfg = SimulationConfig(**minimal_config())

    assert cfg.disk_cleanup_mode == "compact"
    assert cfg.process_on_the_fly is False
    assert cfg.combined_data_dir == "combined_data"
    assert (
        cfg.rel_path_to_combine_binary_catdcd
        == "required_data/bin/catdcd-4.0b/LINUXAMD64/bin/catdcd4.0/catdcd"
    )
    assert cfg.combine_namd_dcd_file is True
    assert cfg.combine_gomc_dcd_file is True
    assert cfg.otf_keep_raw_cycles == 2


@pytest.mark.parametrize(
    ("input_mode", "expected_mode"),
    [
        ("compact", "compact"),
        (" Minimal ", "minimal"),
        ("OFF", "off"),
    ],
)
def test_disk_cleanup_mode_accepts_and_normalizes_valid_modes(
    input_mode, expected_mode
):
    data = minimal_config()
    data["disk_cleanup_mode"] = input_mode

    cfg = SimulationConfig(**data)

    assert cfg.disk_cleanup_mode == expected_mode


def test_disk_cleanup_mode_rejects_invalid_mode():
    data = minimal_config()
    data["disk_cleanup_mode"] = "delete_everything"

    with pytest.raises(ValidationError) as exc:
        SimulationConfig(**data)

    assert "disk_cleanup_mode" in str(exc.value)
    assert "compact, minimal, off" in str(exc.value)


def test_otf_keep_raw_cycles_must_be_at_least_one():
    data = minimal_config()
    data["otf_keep_raw_cycles"] = 0

    with pytest.raises(ValidationError) as exc:
        SimulationConfig(**data)

    assert "otf_keep_raw_cycles" in str(exc.value)


@pytest.mark.parametrize(
    "field_name",
    [
        "process_on_the_fly",
        "combine_namd_dcd_file",
        "combine_gomc_dcd_file",
    ],
)
def test_otf_boolean_fields_are_strict_bools(field_name):
    data = minimal_config()
    data[field_name] = "true"

    with pytest.raises(ValidationError) as exc:
        SimulationConfig(**data)

    assert field_name in str(exc.value)


def test_gcmc_allows_zero_namd_box1_cores_when_gcmc_fields_are_valid():
    data = minimal_config()
    data["simulation_type"] = "GCMC"
    data["no_core_box_1"] = 0
    data["GCMC_ChemPot_or_Fugacity"] = "ChemPot"
    data["GCMC_ChemPot_or_Fugacity_dict"] = {"TIP3": -1000.0}

    cfg = SimulationConfig(**data)

    assert cfg.simulation_type == "GCMC"
    assert cfg.no_core_box_1 == 0


def test_one_box_gemc_allows_zero_namd_box1_cores():
    data = minimal_config()
    data["simulation_type"] = "GEMC"
    data["only_use_box_0_for_namd_for_gemc"] = True
    data["no_core_box_1"] = 0

    cfg = SimulationConfig(**data)

    assert cfg.simulation_type == "GEMC"
    assert cfg.only_use_box_0_for_namd_for_gemc is True
    assert cfg.no_core_box_1 == 0
