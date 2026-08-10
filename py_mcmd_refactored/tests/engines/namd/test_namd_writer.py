# py-MCMD
# Author: Haydar Mehryar
# Copyright (c) 2025
# SPDX-License-Identifier: MIT
import sys

sys.path.insert(0, "/home/arsalan/wsu-gomc/py-MCMD-hm/py_mcmd_refactored")

from pathlib import Path

import pytest
from engines.namd.namd_writer import _validate_box_number


def test_validate_box_number_ok():
    _validate_box_number(0)
    _validate_box_number(1)


@pytest.mark.parametrize("bad", [-1, 2, 1.0, "0", None])
def test_validate_box_number_bad(bad):
    with pytest.raises(ValueError):
        _validate_box_number(bad)


from pathlib import Path

from engines.namd.namd_writer import _compute_namd_box_dir


def test_compute_namd_box_dir_default_width10():
    base = Path("/tmp/base")
    d0 = _compute_namd_box_dir(base, "NAMD", 7, 0)  # width=10 by default
    d1 = _compute_namd_box_dir(base, "NAMD", 7, 1)
    assert d0.as_posix().endswith("/NAMD/0000000007_a")
    assert d1.as_posix().endswith("/NAMD/0000000007_b")


def test_compute_namd_box_dir_width3():
    base = Path("/tmp/base")
    d = _compute_namd_box_dir(base, "NAMD", 7, 0, width=3)
    assert d.as_posix().endswith("/NAMD/007_a")


from pathlib import Path

import pytest

from py_mcmd_refactored.engines.namd.namd_writer import (
    _load_template_text,
    _resolve_under,
)


def test_resolve_under_relative(tmp_path):
    base = tmp_path
    rel = "templates/in.conf.tpl"
    p = _resolve_under(base, rel)
    assert p == base / rel


def test_resolve_under_absolute(tmp_path):
    abs_p = tmp_path / "abs.tpl"
    p = _resolve_under(tmp_path, abs_p)
    assert p == abs_p


def test_load_template_text_ok_relative(tmp_path):
    base = tmp_path
    tpl = base / "tpl.conf"
    tpl.write_text("hello {{world}}")
    out = _load_template_text(base, "tpl.conf")
    assert "hello" in out


def test_load_template_text_ok_absolute(tmp_path):
    tpl = tmp_path / "tpl2.conf"
    tpl.write_text("non-empty")
    out = _load_template_text("/does/not/matter", tpl)  # absolute wins
    assert out == "non-empty"


def test_load_template_text_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        _load_template_text(tmp_path, "nope.tpl")


def test_load_template_text_empty_raises(tmp_path):
    tpl = tmp_path / "empty.conf"
    tpl.write_text("   \n\t")
    with pytest.raises(ValueError):
        _load_template_text(tmp_path, tpl)


from pathlib import Path

from engines.namd.namd_writer import _build_parameter_files_block


def test_build_parameter_files_block_two_files(tmp_path):
    # Create dummy parameter files in different subdirs
    ff1 = tmp_path / "ff" / "par1.prm"
    ff2 = tmp_path / "data" / "charmm" / "par2.prm"
    ff1.parent.mkdir(parents=True)
    ff2.parent.mkdir(parents=True)
    ff1.write_text("* PRM 1")
    ff2.write_text("* PRM 2")

    rel_to = tmp_path / "run" / "0000000007_a"
    rel_to.mkdir(parents=True)

    block = _build_parameter_files_block([ff1, ff2], rel_to)
    # Should contain two lines with relative, POSIX-style paths
    assert "parameters" in block
    assert "ff/par1.prm" in block
    assert "data/charmm/par2.prm" in block
    # exactly two lines
    assert block.count("\n") == 2


def test_build_parameter_files_block_empty_list(tmp_path):
    rel_to = tmp_path
    assert _build_parameter_files_block([], rel_to) == ""
    assert _build_parameter_files_block(None, rel_to) == ""


from pathlib import Path

from engines.namd.namd_writer import _compute_run_paths_and_read_pdb_lines


def test_compute_run_paths_and_read_pdb_lines_fresh(tmp_path):
    base = tmp_path
    namd_dir = base / "NAMD" / "0000000007_a"
    namd_dir.mkdir(parents=True)
    pdb = base / "box0.pdb"
    pdb.write_text("CRYST1   10 20 30 90 90 90\n")
    psf = base / "box0.psf"
    psf.write_text("PSF\n")

    repl, lines = _compute_run_paths_and_read_pdb_lines(
        python_file_directory=base,
        gomc_newdir=base / "GOMC",
        namd_box_x_newdir=namd_dir,
        run_no=0,
        box_number=0,
        starting_pdb_box_x_file=pdb.name,
        starting_psf_box_x_file=psf.name,
    )

    assert repl["Bool_restart"] == "false"
    assert (
        repl["coor_file"] == "NA"
        and repl["xsc_file"] == "NA"
        and repl["vel_file"] == "NA"
    )
    assert repl["pdb_box_file"].endswith("box0.pdb")
    assert repl["psf_box_file"].endswith("box0.psf")
    assert any("CRYST1" in L for L in lines)


# def test_compute_run_paths_and_read_pdb_lines_restart(tmp_path):
#     base = tmp_path
#     namd_dir = base / "NAMD" / "0000000008_b"
#     namd_dir.mkdir(parents=True)
#     gomc = base / "GOMC"; gomc.mkdir()
#     (gomc / "Output_data_BOX_1_restart.pdb").write_text("CRYST1   10 20 30 90 90 90\n")
#     (gomc / "Output_data_BOX_1_restart.psf").write_text("PSF\n")
#     (gomc / "Output_data_BOX_1_restart.coor").write_text("COOR\n")
#     (gomc / "Output_data_BOX_1_restart.xsc").write_text("XSC\n")
#     (gomc / "Output_data_BOX_1_restart.vel").write_text("VEL\n")

#     repl, lines = _compute_run_paths_and_read_pdb_lines(
#         python_file_directory=base,
#         gomc_newdir=gomc,
#         namd_box_x_newdir=namd_dir,
#         run_no=1,
#         box_number=1,
#         starting_pdb_box_x_file="unused",
#         starting_psf_box_x_file="unused",
#     )


#     assert repl["Bool_restart"] == "true"
#     assert repl["pdb_box_file"].endswith("Output_data_BOX_1_restart.pdb")
#     assert repl["psf_box_file"].endswith("Output_data_BOX_1_restart.psf")
#     assert repl["coor_file"].endswith("Output_data_BOX_1_restart.coor")
#     assert repl["xsc_file"].endswith("Output_data_BOX_1_restart.xsc")
#     assert repl["vel_file"].endswith("Output_data_BOX_1_restart.vel")
#     assert any("CRYST1" in L for L in lines)
def test_compute_run_paths_and_read_pdb_lines_restart_with_vel_uses_binary_restart(
    tmp_path,
):
    base = tmp_path
    namd_dir = base / "NAMD" / "0000000008_b"
    namd_dir.mkdir(parents=True)

    gomc = base / "GOMC"
    gomc.mkdir()

    import struct

    (gomc / "Output_data_BOX_1_restart.pdb").write_text(
        "CRYST1   10 20 30 90 90 90\n"
    )
    (gomc / "Output_data_BOX_1_restart.psf").write_text("1 !NATOM\n")
    (gomc / "Output_data_BOX_1_restart.coor").write_text("COOR\n")
    (gomc / "Output_data_BOX_1_restart.xsc").write_text("XSC\n")
    (gomc / "Output_data_BOX_1_restart.vel").write_bytes(
        struct.pack("<i", 1) + b"\x00" * 24
    )

    repl, lines = _compute_run_paths_and_read_pdb_lines(
        python_file_directory=base,
        gomc_newdir=gomc,
        namd_box_x_newdir=namd_dir,
        run_no=1,
        box_number=1,
        starting_pdb_box_x_file="unused",
        starting_psf_box_x_file="unused",
    )

    assert repl["Bool_restart"] == "true"
    assert repl["pdb_box_file"].endswith("Output_data_BOX_1_restart.pdb")
    assert repl["psf_box_file"].endswith("Output_data_BOX_1_restart.psf")
    assert repl["coor_file"].endswith("Output_data_BOX_1_restart.coor")
    assert repl["xsc_file"].endswith("Output_data_BOX_1_restart.xsc")
    assert repl["vel_file"].endswith("Output_data_BOX_1_restart.vel")
    assert any("CRYST1" in line for line in lines)


def test_compute_run_paths_and_read_pdb_lines_restart_without_vel_uses_pdb_psf_fallback(
    tmp_path,
):
    base = tmp_path
    namd_dir = base / "NAMD" / "0000000008_a"
    namd_dir.mkdir(parents=True)

    gomc = base / "GOMC"
    gomc.mkdir()

    restart_pdb = gomc / "Output_data_BOX_0_restart.pdb"
    restart_psf = gomc / "Output_data_BOX_0_restart.psf"

    restart_pdb.write_text("CRYST1   11 22 33 90 90 90\n")
    restart_psf.write_text("PSF\n")

    (gomc / "Output_data_BOX_0_restart.coor").write_text("COOR\n")
    (gomc / "Output_data_BOX_0_restart.xsc").write_text("XSC\n")

    repl, lines = _compute_run_paths_and_read_pdb_lines(
        python_file_directory=base,
        gomc_newdir=gomc,
        namd_box_x_newdir=namd_dir,
        run_no=1,
        box_number=0,
        starting_pdb_box_x_file="unused",
        starting_psf_box_x_file="unused",
    )

    assert repl["Bool_restart"] == "false"
    assert repl["pdb_box_file"].endswith("Output_data_BOX_0_restart.pdb")
    assert repl["psf_box_file"].endswith("Output_data_BOX_0_restart.psf")
    assert repl["coor_file"] == "NA"
    assert repl["xsc_file"] == "NA"
    assert repl["vel_file"] == "NA"
    assert any("CRYST1   11 22 33" in line for line in lines)


from engines.namd.namd_writer import _parse_cryst1


def test_parse_cryst1_parses_fixed_width():
    # Fixed-width PDB line with proper columns
    line = "CRYST1   10.000   20.000   30.000   90.00   90.00   90.00 P 1           1\n"
    a, b, c, alpha, beta, gamma = _parse_cryst1([line])
    assert (a, b, c) == (10.0, 20.0, 30.0)
    assert (alpha, beta, gamma) == (90.0, 90.0, 90.0)


def test_parse_cryst1_parses_whitespace_split():
    # Whitespace-separated variant
    line = "CRYST1 10 20 30 90 90 90\n"
    a, b, c, alpha, beta, gamma = _parse_cryst1([line])
    assert (a, b, c) == (10.0, 20.0, 30.0)
    assert (alpha, beta, gamma) == (90.0, 90.0, 90.0)


def test_parse_cryst1_returns_none_when_missing():
    a, b, c, alpha, beta, gamma = _parse_cryst1(["ATOM  ...\n", "HEADER X\n"])
    assert all(v is None for v in (a, b, c, alpha, beta, gamma))


import pytest
from engines.namd.namd_writer import _override_dim


class _DummyChecker:
    def __call__(self, axis, run_no, read_dim, *, set_dim, only_on_run_no):
        # mimic legacy: prefer set_dim, else read_dim
        return set_dim if set_dim is not None else read_dim


def test_override_dim_uses_checker_preferring_set():
    assert _override_dim(_DummyChecker(), "x", 0, 10.0, 11.0) == 11.0


def test_override_dim_uses_checker_fallback_to_read():
    assert _override_dim(_DummyChecker(), "y", 0, 22.5, None) == 22.5


def test_override_dim_without_checker_prefers_set_then_read():
    assert _override_dim(None, "z", 0, 30.0, 31.0) == 31.0
    assert _override_dim(None, "z", 0, 30.0, None) == 30.0


def test_override_dim_raises_when_missing_all():
    with pytest.raises(ValueError):
        _override_dim(None, "x", 0, None, None)


import pytest
from engines.namd.namd_writer import _validate_angles


def test_validate_angles_run0_all_ninety_ok():
    _validate_angles(0, 90.0, 90.0, 90.0, 90.0, 90.0, 90.0)


def test_validate_angles_run0_nonorthogonal_from_pdb_raises():
    with pytest.raises(ValueError):
        _validate_angles(0, 89.0, 90.0, 90.0, 90.0, 90.0, 90.0)


def test_validate_angles_run0_nonorthogonal_from_set_raises():
    with pytest.raises(ValueError):
        _validate_angles(0, 90.0, 90.0, 90.0, None, 100.0, None)


def test_validate_angles_restart_run_allows_any_angles():
    _validate_angles(
        1, 95.0, 80.0, 120.0, 70.0, 110.0, 60.0
    )  # should not raise


from engines.namd.namd_writer import _compute_pme_grid_dims


def test_compute_pme_grid_dims_restart_returns_given():
    assert _compute_pme_grid_dims(
        run_no=1,
        used_x=10.0,
        used_y=20.0,
        used_z=30.0,
        given_x=32,
        given_y=40,
        given_z=48,
        fft_add_namd_ang_to_box_dim=0,
        simulation_type="NVT",
    ) == (32, 40, 48)


def test_compute_pme_grid_dims_run0_scales_nvt():
    # mult = 1.0; add fft_add and +1
    x, y, z = _compute_pme_grid_dims(
        run_no=0,
        used_x=10.0,
        used_y=20.0,
        used_z=30.0,
        given_x=0,
        given_y=0,
        given_z=0,
        fft_add_namd_ang_to_box_dim=2,
        simulation_type="NVT",
    )
    assert (x, y, z) == (int(12.0 + 1), int(22.0 + 1), int(32.0 + 1))


def test_compute_pme_grid_dims_run0_scales_npt_and_gemc():
    # mult = 1.3 for NPT and GEMC
    for sim in ("NPT", "GEMC"):
        x, y, z = _compute_pme_grid_dims(
            run_no=0,
            used_x=10.0,
            used_y=20.0,
            used_z=30.0,
            given_x=0,
            given_y=0,
            given_z=0,
            fft_add_namd_ang_to_box_dim=0,
            simulation_type=sim,
        )
        assert (x, y, z) == (
            int(10.0 * 1.3 + 1),
            int(20.0 * 1.3 + 1),
            int(30.0 * 1.3 + 1),
        )


import pytest
from engines.namd.namd_writer import _apply_replacements


def test_apply_replacements_basic():
    tpl = "x_dim_box y_dim_box z_dim_box"
    out = _apply_replacements(
        tpl, {"x_dim_box": 10.0, "y_dim_box": 20, "z_dim_box": "30"}
    )
    assert out == "10.0 20 30"


def test_apply_replacements_multiple_occurrences():
    tpl = "PMEGridSizeX X_PME_GRID_DIM ; X_PME_GRID_DIM end"
    out = _apply_replacements(tpl, {"X_PME_GRID_DIM": 64})
    assert out == "PMEGridSizeX 64 ; 64 end"


def test_apply_replacements_strict_raises_on_leftover():
    tpl = "A X_PME_GRID_DIM B Y_PME_GRID_DIM"
    with pytest.raises(ValueError):
        _apply_replacements(
            tpl,
            {"X_PME_GRID_DIM": 32},
            strict=True,
            must_replace=["X_PME_GRID_DIM", "Y_PME_GRID_DIM"],
        )


def test_apply_replacements_non_strict_allows_leftover():
    tpl = "A X_PME_GRID_DIM B Y_PME_GRID_DIM"
    out = _apply_replacements(tpl, {"X_PME_GRID_DIM": 32})
    assert out == "A 32 B Y_PME_GRID_DIM"


from pathlib import Path

import pytest
from engines.namd.namd_writer import write_namd_conf_file


def test_write_namd_conf_file_fresh(tmp_path, monkeypatch):
    # Globals expected by legacy code
    from engines.namd import namd_writer as mod

    # parameter files
    prm = tmp_path / "params" / "par.prm"
    prm.parent.mkdir()
    prm.write_text("* test prm")
    monkeypatch.setattr(mod, "starting_ff_file_list_namd", [prm])

    # checker
    class Checker:
        def __call__(self, axis, run_no, read_dim, *, set_dim, only_on_run_no):
            return float(set_dim if set_dim is not None else read_dim)

    monkeypatch.setattr(mod, "check_for_pdb_dims_and_override", Checker())

    # sim type
    monkeypatch.setattr(mod, "simulation_type", "NVT")

    # template (include all placeholders we fill)
    tpl = tmp_path / "tpl.conf"
    tpl.write_text(
        "parameters all_parameter_files\n"
        "structure psf_box_file\ncoordinates pdb_box_file\n"
        "set coor coor_file\nset xsc xsc_file\nset vel vel_file\n"
        "cellBasisVector1 x_dim_box 0 0\n"
        "cellBasisVector2 0 y_dim_box 0\n"
        "cellBasisVector3 0 0 z_dim_box\n"
        "cellOrigin x_origin_box y_origin_box z_origin_box\n"
        "PMEGridSizeX X_PME_GRID_DIM\nPMEGridSizeY Y_PME_GRID_DIM\nPMEGridSizeZ Z_PME_GRID_DIM\n"
        "set t System_temp_set\nset p System_press_set\n"
        "DCDfreq NAMD_RST_DCD_XST_Steps\noutputEnergies NAMD_console_BLKavg_E_and_P_Steps\n"
        "minimize NAMD_Minimize\nrun NAMD_Run_Steps\nset r Bool_restart\n"
        "cur current_step\n"
    )

    # inputs
    pdb = tmp_path / "box0.pdb"
    pdb.write_text(
        "CRYST1   10.000   20.000   30.000   90.00   90.00   90.00\n"
    )
    psf = tmp_path / "box0.psf"
    psf.write_text("PSF\n")
    (tmp_path / "NAMD").mkdir()

    out_dir = write_namd_conf_file(
        python_file_directory=tmp_path,
        path_namd_template=tpl.name,
        path_namd_runs="NAMD",
        gomc_newdir=tmp_path / "GOMC",
        run_no=0,
        box_number=0,
        namd_run_steps=1000,
        namd_minimize_steps=100,
        namd_rst_dcd_xst_steps=50,
        namd_console_blkavg_e_and_p_steps=10,
        simulation_temp_k=300.0,
        simulation_pressure_bar=1.0,
        starting_pdb_box_x_file=pdb.name,
        starting_psf_box_x_file=psf.name,
        namd_x_pme_grid_dim=32,
        namd_y_pme_grid_dim=32,
        namd_z_pme_grid_dim=32,
        set_x_dim=None,
        set_y_dim=None,
        set_z_dim=None,
        set_angle_alpha=90,
        set_angle_beta=90,
        set_angle_gamma=90,
        fft_add_namd_ang_to_box_dim=2,
    )
    out_path = Path(out_dir) / "in.conf"
    txt = out_path.read_text()
    assert "set r false" in txt
    assert "parameters" in txt and "par.prm" in txt
    assert (
        "PMEGridSizeX" in txt
        and "PMEGridSizeY" in txt
        and "PMEGridSizeZ" in txt
    )
    # ensure no placeholders remain
    leftovers = [
        "all_parameter_files",
        "pdb_box_file",
        "psf_box_file",
        "coor_file",
        "xsc_file",
        "vel_file",
        "x_dim_box",
        "y_dim_box",
        "z_dim_box",
        "x_origin_box",
        "y_origin_box",
        "z_origin_box",
        "X_PME_GRID_DIM",
        "Y_PME_GRID_DIM",
        "Z_PME_GRID_DIM",
        "System_temp_set",
        "System_press_set",
        "NAMD_RST_DCD_XST_Steps",
        "NAMD_console_BLKavg_E_and_P_Steps",
        "NAMD_Minimize",
        "NAMD_Run_Steps",
        "Bool_restart",
        "current_step",
    ]
    assert not any(tok in txt for tok in leftovers)


# def test_write_namd_conf_file_restart(tmp_path, monkeypatch):
def test_write_namd_conf_file_restart_with_vel_uses_binary_restart(
    tmp_path,
    monkeypatch,
):
    from py_mcmd_refactored.engines.namd import namd_writer as mod

    monkeypatch.setattr(mod, "starting_ff_file_list_namd", [])
    monkeypatch.setattr(mod, "check_for_pdb_dims_and_override", None)
    monkeypatch.setattr(mod, "simulation_type", "NPT")

    tpl = tmp_path / "tpl.conf"
    tpl.write_text("set r Bool_restart\nPMEGridSizeX X_PME_GRID_DIM\n")

    # gomc = tmp_path / "GOMC"; gomc.mkdir()
    # (gomc / "Output_data_BOX_1_restart.pdb").write_text("CRYST1 10 20 30 90 90 90\n")
    # (tmp_path / "NAMD").mkdir()
    import struct

    gomc = tmp_path / "GOMC"
    gomc.mkdir()

    (gomc / "Output_data_BOX_1_restart.pdb").write_text(
        "CRYST1 10 20 30 90 90 90\n"
    )
    (gomc / "Output_data_BOX_1_restart.psf").write_text("1 !NATOM\n")
    (gomc / "Output_data_BOX_1_restart.vel").write_bytes(
        struct.pack("<i", 1) + b"\x00" * 24
    )

    (tmp_path / "NAMD").mkdir()

    out_dir = write_namd_conf_file(
        python_file_directory=tmp_path,
        path_namd_template=tpl.name,
        path_namd_runs="NAMD",
        gomc_newdir=gomc,
        run_no=1,
        box_number=1,
        namd_run_steps=1000,
        namd_minimize_steps=100,
        namd_rst_dcd_xst_steps=50,
        namd_console_blkavg_e_and_p_steps=10,
        simulation_temp_k=300.0,
        simulation_pressure_bar=1.0,
        starting_pdb_box_x_file="unused",
        starting_psf_box_x_file="unused",
        namd_x_pme_grid_dim=40,
        namd_y_pme_grid_dim=41,
        namd_z_pme_grid_dim=42,
        set_x_dim=None,
        set_y_dim=None,
        set_z_dim=None,
        set_angle_alpha=90,
        set_angle_beta=90,
        set_angle_gamma=90,
        fft_add_namd_ang_to_box_dim=0,
    )
    out_path = Path(out_dir) / "in.conf"
    txt = out_path.read_text()
    # restart: Bool_restart true and PME sizes match the given ones
    assert "set r true" in txt
    assert "PMEGridSizeX 40" in txt
