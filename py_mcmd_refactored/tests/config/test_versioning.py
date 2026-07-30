from __future__ import annotations

from pathlib import Path

import pytest

from py_mcmd_refactored import __version__ as package_version
from py_mcmd_refactored import get_version as package_get_version
from py_mcmd_refactored.version import __version__ as source_version
from py_mcmd_refactored.version import get_version as source_get_version
from cli.main import parse_args
from config.models import SimulationConfig
from orchestrator.manager import SimulationOrchestrator


def make_cfg_for_orch(tmp_path: Path, **overrides) -> SimulationConfig:
    base = dict(
        total_cycles_namd_gomc_sims=1,
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


def test_package_version_exports_match_single_source_of_truth() -> None:
    assert source_version == package_version
    assert source_get_version() == package_get_version() == source_version


def test_cli_version_output_matches_authoritative_version(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as excinfo:
        parse_args(["--version"])

    assert excinfo.value.code == 0
    assert capsys.readouterr().out.strip() == f"py-mcmd {source_get_version()}"


def test_cli_version_output_uses_cli_version_source(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import cli.main as cli_main

    sentinel = "9.9.9-test"
    monkeypatch.setattr(cli_main, "get_version", lambda: sentinel)

    with pytest.raises(SystemExit) as excinfo:
        cli_main.parse_args(["--version"])

    assert excinfo.value.code == 0
    assert capsys.readouterr().out.strip() == f"py-mcmd {sentinel}"


def test_startup_logging_includes_authoritative_version(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    cfg = make_cfg_for_orch(tmp_path)
    caplog.set_level("INFO")

    orch = SimulationOrchestrator(cfg, dry_run=True)

    expected = f"py-MCMD framework version = {source_get_version()}"
    assert expected in caplog.text
    assert expected in orch._log_path.read_text()


def test_startup_logging_uses_manager_version_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    import orchestrator.manager as manager

    sentinel = "9.9.9-test"
    monkeypatch.setattr(manager, "get_version", lambda: sentinel)

    cfg = make_cfg_for_orch(tmp_path)
    caplog.set_level("INFO")
    orch = SimulationOrchestrator(cfg, dry_run=True)

    expected = f"py-MCMD framework version = {sentinel}"
    assert expected in caplog.text
    assert expected in orch._log_path.read_text()


def test_no_other_package_module_hardcodes_the_current_version_string() -> None:
    project_root = Path(__file__).resolve().parents[1]
    current_version = source_get_version()
    offenders: list[str] = []

    for path in project_root.rglob("*.py"):
        if "__pycache__" in path.parts or "tests" in path.parts:
            continue
        if path.name == "version.py":
            continue
        if current_version in path.read_text(encoding="utf-8"):
            offenders.append(str(path.relative_to(project_root)))

    assert offenders == []