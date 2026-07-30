# tests/test_cli.py

import sys
sys.path.insert(0, "/home/arsalan/wsu-gomc/py-MCMD-hm/py_mcmd_refactored")

import pytest

import os
import logging

from cli.main import parse_args

def test_main_overrides_config_namd_simulation_order(tmp_path, monkeypatch):
    """Ensure cli.main.main() applies CLI override to SimulationConfig."""
    import json
    import cli.main as cli_main

    # Valid config JSON WITHOUT namd_simulation_order (so default would be "series")
    cfg_dict = {
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
    config_file = tmp_path / "cfg.json"
    config_file.write_text(json.dumps(cfg_dict))

    captured = {}

    class DummyOrchestrator:
        def __init__(self, cfg, *args, **kwargs):
            captured["cfg"] = cfg

        def run(self):
            return None

    monkeypatch.setattr(cli_main, "SimulationOrchestrator", DummyOrchestrator)

    monkeypatch.setattr(
        cli_main.sys,
        "argv",
        ["py-mcmd", "--file", str(config_file), "--namd_simulation_order", "parallel"],
    )

    cli_main.main()

    assert "cfg" in captured
    assert captured["cfg"].namd_simulation_order == "parallel"


def test_parse_args_valid_file_and_order(tmp_path, caplog):
    # Arrange: create a dummy JSON config file
    config_file = tmp_path / "user.json"
    config_file.write_text("{}")

    # Act: parse args with existing file and valid order
    caplog.set_level(logging.INFO)
    args = parse_args(["--file", str(config_file), "--namd_simulation_order", "parallel"])

    # Assert: args values and INFO logs
    assert args.file == str(config_file)
    assert args.namd_simulation_order == "parallel"
    assert f"Reading data from <{config_file}> file." in caplog.text
    assert "shall be run in <parallel>." in caplog.text


def test_parse_args_default_order_on_invalid(tmp_path, caplog):
    # Arrange: create a dummy JSON config file
    config_file = tmp_path / "user.json"
    config_file.write_text("{}")

    # Act: parse args with invalid order
    caplog.set_level(logging.WARNING)
    args = parse_args(["--file", str(config_file), "--namd_simulation_order", "invalid_order"])

    # Assert: default to 'series' and emit WARNING
    assert args.namd_simulation_order == "series"
    assert "defaulting to <series>" in caplog.text or "defaulting to <series>." in caplog.text


def test_parse_args_exit_on_missing_file(tmp_path):
    # Arrange: define a non-existent file
    nonexist = tmp_path / "nope.json"

    # Act & Assert: SystemExit with code 1
    with pytest.raises(SystemExit) as exc_info:
        parse_args(["--file", str(nonexist)])
    assert exc_info.value.code == 1


