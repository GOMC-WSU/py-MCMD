from __future__ import annotations

from pathlib import Path

import pytest
from config.models import SimulationConfig
from engines.gomc_engine import GomcEngine
from engines.namd.plan import build_namd_execution_plan
from engines.namd_engine import NamdEngine
from utils.persisted_file_lists import (
    GOMC_PERSISTED_BASENAMES,
    NAMD_PERSISTED_BASENAMES,
    persisted_output_path,
    should_persist,
)


def make_cfg(tmp_path: Path, **kw) -> SimulationConfig:
    base = dict(
        total_cycles_namd_gomc_sims=1,
        starting_at_cycle_namd_gomc_sims=0,
        simulation_type="NPT",
        gomc_use_CPU_or_GPU="CPU",
        only_use_box_0_for_namd_for_gemc=True,
        no_core_box_0=4,
        no_core_box_1=0,
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
        path_namd_template=str(tmp_path / "templates" / "NAMD.conf"),
        path_gomc_template=str(tmp_path / "templates" / "GOMC_NPT.conf"),
        log_dir=str(tmp_path / "logs"),
        namd_simulation_order="series",
    )
    base.update(kw)
    return SimulationConfig(**base)


# def test_default_allow_lists_are_out_dat_only():
#     assert NAMD_PERSISTED_BASENAMES == ["out.dat"]
#     assert GOMC_PERSISTED_BASENAMES == ["out.dat"]
def test_default_allow_lists_are_empty():
    assert NAMD_PERSISTED_BASENAMES == []
    assert GOMC_PERSISTED_BASENAMES == []


# def test_should_persist_uses_engine_allow_list():
#     assert should_persist("NAMD", "out.dat") is True
#     assert should_persist("GOMC", "out.dat") is True

#     assert should_persist("NAMD", "in.conf") is False
#     assert should_persist("GOMC", "Output_data_BOX_0_restart.coor") is False


#     assert should_persist("namd", "/tmp/any/out.dat") is True
#     assert should_persist("gomc", "/tmp/any/in.conf") is False
def test_should_persist_uses_engine_allow_list():
    assert should_persist("NAMD", "out.dat") is False
    assert should_persist("GOMC", "out.dat") is False

    assert should_persist("NAMD", "in.conf") is False
    assert (
        should_persist(
            "GOMC",
            "Output_data_BOX_0_restart.coor",
        )
        is False
    )

    assert should_persist("namd", "/tmp/any/out.dat") is False
    assert should_persist("gomc", "/tmp/any/in.conf") is False


# def test_persisted_output_path_returns_disk_path_only_for_allow_listed_file(tmp_path: Path):
#     run_dir = tmp_path / "NAMD" / "00000000_a"
#     assert persisted_output_path("NAMD", run_dir, "out.dat") == run_dir / "out.dat"


#     with pytest.raises(ValueError):
#         persisted_output_path("NAMD", run_dir, "in.conf")
def test_persisted_output_path_rejects_files_when_default_allow_list_is_empty(
    tmp_path: Path,
):
    run_dir = tmp_path / "NAMD" / "00000000_a"

    with pytest.raises(ValueError):
        persisted_output_path("NAMD", run_dir, "out.dat")

    with pytest.raises(ValueError):
        persisted_output_path("NAMD", run_dir, "in.conf")


# def test_build_namd_execution_plan_routes_stdout_through_allow_list_helper(
#     tmp_path: Path, monkeypatch: pytest.MonkeyPatch
# ):
#     cfg = make_cfg(tmp_path, simulation_type="NPT", only_use_box_0_for_namd_for_gemc=True)

#     calls: list[tuple[str, Path, str]] = []

#     def fake_persisted_output_path(engine: str, run_dir: Path, basename: str) -> Path:
#         calls.append((engine, Path(run_dir), basename))
#         return Path(run_dir) / f"persisted-{basename}"

#     monkeypatch.setattr("engines.namd.plan.persisted_output_path", fake_persisted_output_path)

#     box0_dir = tmp_path / "NAMD" / "00000000_a"
#     plan = build_namd_execution_plan(
#         cfg,
#         exec_path="namd2",
#         box0_dir=box0_dir,
#         box1_dir=None,
#     )


#     assert plan.box0.stdout_path == box0_dir / "persisted-out.dat"
#     assert calls == [("NAMD", box0_dir, "out.dat")]
def test_build_namd_execution_plan_routes_stdout_to_execution_directory(
    tmp_path: Path,
):
    cfg = make_cfg(
        tmp_path,
        simulation_type="NPT",
        only_use_box_0_for_namd_for_gemc=True,
    )
    box0_dir = tmp_path / "managed" / "NAMD" / "0000000000_a"

    plan = build_namd_execution_plan(
        cfg,
        exec_path="namd2",
        box0_dir=box0_dir,
        box1_dir=None,
    )

    assert plan.box0.stdout_path == box0_dir / "out.dat"


def test_namd_engine_run_steps_routes_stdout_through_allow_list_helper(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    cfg = make_cfg(tmp_path)
    engine = NamdEngine(cfg, dry_run=True)

    captured = {}

    def fake_run_and_wait(cmd):
        captured["cmd"] = cmd
        return 0

    monkeypatch.setattr(engine.runner, "run_and_wait", fake_run_and_wait)
    monkeypatch.setattr(
        "engines.namd_engine.persisted_output_path",
        lambda engine_name, run_dir, basename: Path(run_dir)
        / f"persisted-{basename}",
    )

    run_dir = tmp_path / "NAMD" / "00000000_a"
    rc = engine.run_steps(run_dir=run_dir, cores=4)

    assert rc == 0
    assert captured["cmd"].stdout_path == run_dir / "persisted-out.dat"


def test_gomc_engine_run_steps_routes_stdout_through_allow_list_helper(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    cfg = make_cfg(tmp_path)
    engine = GomcEngine(cfg, dry_run=True)

    captured = {}

    def fake_run_and_wait(cmd):
        captured["cmd"] = cmd
        return 0

    monkeypatch.setattr(engine.runner, "run_and_wait", fake_run_and_wait)
    monkeypatch.setattr(
        "engines.gomc_engine.persisted_output_path",
        lambda engine_name, run_dir, basename: Path(run_dir)
        / f"persisted-{basename}",
    )

    run_dir = tmp_path / "GOMC" / "00000001"
    rc = engine.run_steps(run_dir=run_dir, cores=4)

    assert rc == 0
    assert captured["cmd"].stdout_path == run_dir / "persisted-out.dat"
