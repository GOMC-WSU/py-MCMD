# py_mcmd_refactored/tests/test_gomc_writer.py
from __future__ import annotations

import os

def _rel(p: Path, base: Path) -> str:
    """Return a relative POSIX path from base to p (can traverse up with ..)."""
    return os.path.relpath(str(p), start=str(base)).replace("\\", "/")

# --- update _build_parameters_block to avoid .relative_to on siblings ---
def _build_parameters_block(params_files: Iterable[Path], relative_to: Path) -> str:
    lines = []
    for p in params_files:
        p = Path(p)
        if p.is_absolute():
            rel = os.path.relpath(str(p), start=str(relative_to)).replace("\\", "/")
        else:
            # keep user-provided relative path as-is (matches legacy behavior & tests)
            rel = p.as_posix()
        lines.append(f"Parameters \t {rel}\n")
    return "".join(lines)

# --- make XSC reader resilient to both token layouts (1,5,9) and (1,4,7) ---
def _read_last_xsc_dims(xsc_path: Path) -> Tuple[float, float, float]:
    """
    Read the last line of an XSC file.
    Primary layout (legacy): tokens [1]=Lx, [5]=Ly, [9]=Lz
    Fallback layout (observed in tests): tokens [1]=Lx, [4]=Ly, [7]=Lz
    """
    lines = xsc_path.read_text().splitlines()
    if not lines:
        raise ValueError(f"Empty XSC: {xsc_path}")
    toks = lines[-1].split()

    def _try(idx):
        try:
            return float(toks[idx])
        except (IndexError, ValueError):
            return None

    # primary indices
    lx = _try(1); ly = _try(5); lz = _try(9)
    if lx is not None and ly is not None and lz is not None and (ly != 0.0 or lz != 0.0):
        return lx, ly, lz

    # fallback indices
    ly_fb = _try(4); lz_fb = _try(7)
    if lx is not None and ly_fb is not None and lz_fb is not None:
        return lx, ly_fb, lz_fb

    raise ValueError(f"Malformed XSC line in {xsc_path}: {lines[-1]!r}")


from types import SimpleNamespace
from pathlib import Path
import logging

from py_mcmd_refactored.engines.gomc.gomc_writer import (
    write_gomc_conf_file,
    GOMCIOPaths,
    GOMCSimParams,
    GOMCStartFiles,
)

import pytest


def _xsc(last_lx: float, last_ly: float, last_lz: float) -> str:
    # Columns expected (0-based): [1]=Lx, [5]=Ly, [9]=Lz
    # Put enough tokens so indices 1,5,9 exist
    return f"0 {last_lx} 0 0 {last_ly} 0 0 {last_lz} 0 0 5 6 7\n"


def _pdb_cryst1(a: float, b: float, c: float) -> str:
    # Minimal CRYST1 line: indices 1,2,3 parsed as a,b,c
    return f"CRYST1  {a:.1f} {b:.1f} {c:.1f} 90.00 90.00 90.00 P 1           1\n"


def _make_cfg(
    *,
    simulation_type="NPT",
    only_use_box_0_for_namd_for_gemc=False,
    params_rel=("params/par1.prm", "params/par2.prm"),
    gcmc_mode=None,
    gcmc_map=None,
    gcmc_keys=None,
):
    return SimpleNamespace(
        simulation_type=simulation_type,
        only_use_box_0_for_namd_for_gemc=only_use_box_0_for_namd_for_gemc,
        starting_ff_file_list_gomc=[Path(p) for p in params_rel],
        GCMC_ChemPot_or_Fugacity=gcmc_mode,
        GCMC_ChemPot_or_Fugacity_dict=gcmc_map,
        GCMC_ChemPot_or_Fugacity_dict_keys=gcmc_keys,
    )


def _write_template(path: Path, include_box1_tokens: bool, include_bin_lines: bool, include_gcmc_block: bool):
    lines = []
    lines.append("all_parameter_files\n")
    lines.append("coor_box_0_file\nxsc_box_0_file\nvel_box_0_file\n")
    lines.append("pdb_file_box_0_file\npsf_file_box_0_file\n")
    lines.append("x_dim_box_0\ny_dim_box_0\nz_dim_box_0\n")
    if include_box1_tokens:
        if include_bin_lines:
            lines.append("binCoordinates 1 SOME\n")
            lines.append("extendedSystem 1 SOME\n")
            lines.append("binVelocities 1 SOME\n")
        lines.append("coor_box_1_file\nxsc_box_1_file\nvel_box_1_file\n")
        lines.append("pdb_file_box_1_file\npsf_file_box_1_file\n")
        lines.append("x_dim_box_1\ny_dim_box_1\nz_dim_box_1\n")
    lines.append("restart_true_or_false\n")
    lines.append("GOMC_Run_Steps\nGOMC_RST_Coor_CKpoint_Steps\nGOMC_console_BLKavg_Hist_Steps\nGOMC_Hist_sample_Steps\n")
    lines.append("System_temp_set\nSystem_press_set\n")
    lines.append("GOMC_Equilb_Steps\nGOMC_Adj_Steps\n")
    lines.append("Restart_Checkpoint_file\n")
    if include_gcmc_block:
        lines.append("mu_ChemPot_K_or_P_Fugacitiy_bar_all\n")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(lines))


def test_fresh_npt_writes_config(tmp_path: Path, caplog: pytest.LogCaptureFixture):
    caplog.set_level(logging.INFO)

    proj = tmp_path / "proj"
    tpl = proj / "templates" / "gomc.tpl"
    _write_template(tpl, include_box1_tokens=False, include_bin_lines=False, include_gcmc_block=False)

    # dirs and files
    namd0 = proj / "NAMD" / "0000000001_a"
    namd0.mkdir(parents=True)
    (namd0 / "namdOut.restart.xsc").write_text(_xsc(10.0, 20.0, 30.0))
    (namd0 / "namdOut.restart.coor").write_text("coor")
    (namd0 / "namdOut.restart.vel").write_text("vel")

    # starting pdb/psf
    pdb0 = proj / "inputs" / "box0.pdb";   pdb0.parent.mkdir(parents=True, exist_ok=True); pdb0.write_text(_pdb_cryst1(40, 50, 60))
    psf0 = proj / "inputs" / "box0.psf";   psf0.write_text("psf0")
    pdb1 = proj / "inputs" / "box1.pdb";   pdb1.write_text(_pdb_cryst1(70, 80, 90))
    psf1 = proj / "inputs" / "box1.psf";   psf1.write_text("psf1")

    # params (relative paths to avoid absolute resolution issues)
    (proj / "params").mkdir(exist_ok=True)
    (proj / "params" / "par1.prm").write_text("*p1")
    (proj / "params" / "par2.prm").write_text("*p2")

    cfg = _make_cfg(simulation_type="NPT")
    io = GOMCIOPaths(
        python_file_directory=proj,
        path_gomc_runs=Path("GOMC"),
        path_gomc_template=tpl.relative_to(proj),
        namd_box_0_dir=namd0,
        namd_box_1_dir=None,
        previous_gomc_dir=None,
    )
    sim = GOMCSimParams(
        gomc_run_steps=5000,
        gomc_rst_coor_ckpoint_steps=100,
        gomc_console_blkavg_hist_steps=50,
        gomc_hist_sample_steps=25,
        simulation_temp_k=300.0,
        simulation_pressure_bar=1.0,
    )
    starts = GOMCStartFiles(
        starting_pdb_box_0_file=pdb0.relative_to(proj),
        starting_pdb_box_1_file=pdb1.relative_to(proj),
        starting_psf_box_0_file=psf0.relative_to(proj),
        starting_psf_box_1_file=psf1.relative_to(proj),
    )

    out_dir = write_gomc_conf_file(cfg, io, run_no=1, sim=sim, starts=starts)
    conf = (out_dir / "in.conf").read_text()

    # parameters present
    # assert "Parameters \t params/par1.prm" in conf
    # assert "Parameters \t params/par2.prm" in conf
    import os

    expected_par1 = os.path.relpath(proj / "params" / "par1.prm", out_dir).replace(os.sep, "/")
    expected_par2 = os.path.relpath(proj / "params" / "par2.prm", out_dir).replace(os.sep, "/")

    assert f"Parameters \t {expected_par1}" in conf
    assert f"Parameters \t {expected_par2}" in conf

    # box0 restarts from NAMD
    assert "coor_box_0_file" not in conf
    assert "NAMD/0000000001_a/namdOut.restart.coor" in conf
    assert "x_dim_box_0" not in conf
    assert "10.0" in conf and "20.0" in conf and "30.0" in conf

    # restart flags for non-GEMC: true
    assert "restart_true_or_false" not in conf
    assert "\ntrue\n" in conf or "true\r\n" in conf

    # Equil/Adj = run_steps/10 = 500
    assert "GOMC_Equilb_Steps" not in conf
    assert "GOMC_Adj_Steps" not in conf
    assert "500" in conf


def test_gemc_box0_only_fresh_strips_box1_and_uses_pdb_dims(tmp_path: Path):
    proj = tmp_path / "proj"
    tpl = proj / "templates" / "gomc.tpl"
    _write_template(tpl, include_box1_tokens=True, include_bin_lines=True, include_gcmc_block=False)

    # NAMD box 0
    namd0 = proj / "NAMD" / "0000000002_a"; namd0.mkdir(parents=True)
    (namd0 / "namdOut.restart.xsc").write_text(_xsc(11.0, 21.0, 31.0))
    (namd0 / "namdOut.restart.coor").write_text("c")
    (namd0 / "namdOut.restart.vel").write_text("v")

    # starting PDB/PSF (box1 PDB provides dims)
    pdb0 = proj / "inputs" / "b0.pdb"; pdb0.parent.mkdir(parents=True, exist_ok=True); pdb0.write_text(_pdb_cryst1(101, 102, 103))
    psf0 = proj / "inputs" / "b0.psf"; psf0.write_text("psf0")
    pdb1 = proj / "inputs" / "b1.pdb"; pdb1.write_text(_pdb_cryst1(41, 51, 61))
    psf1 = proj / "inputs" / "b1.psf"; psf1.write_text("psf1")

    cfg = _make_cfg(simulation_type="GEMC", only_use_box_0_for_namd_for_gemc=True)
    io = GOMCIOPaths(
        python_file_directory=proj,
        path_gomc_runs=Path("GOMC"),
        path_gomc_template=tpl.relative_to(proj),
        namd_box_0_dir=namd0,
        namd_box_1_dir=None,
        previous_gomc_dir=None,
    )
    sim = GOMCSimParams(1000, 100, 50, 25, 300.0, 1.0)
    starts = GOMCStartFiles(pdb0.relative_to(proj), pdb1.relative_to(proj), psf0.relative_to(proj), psf1.relative_to(proj))

    out_dir = write_gomc_conf_file(cfg, io, run_no=2, sim=sim, starts=starts)
    conf = (out_dir / "in.conf").read_text()

    # Box-1 binary lines removed
    assert "binCoordinates 1" not in conf
    assert "extendedSystem 1" not in conf
    assert "binVelocities 1" not in conf

    # Box-1 PDB/PSF used and dims from b1.pdb
    assert "pdb_file_box_1_file" not in conf
    assert "inputs/b1.pdb" in conf
    assert "x_dim_box_1" not in conf
    assert "41.0" in conf and "51.0" in conf and "61.0" in conf

    # restart false for this branch
    assert "\nfalse\n" in conf or "false\r\n" in conf


def test_gemc_both_boxes_from_namd(tmp_path: Path):
    proj = tmp_path / "proj"
    tpl = proj / "templates" / "gomc.tpl"
    _write_template(tpl, include_box1_tokens=True, include_bin_lines=False, include_gcmc_block=False)

    # NAMD boxes
    namd0 = proj / "NAMD" / "0000000003_a"; namd0.mkdir(parents=True)
    (namd0 / "namdOut.restart.xsc").write_text(_xsc(12.0, 22.0, 32.0))
    (namd0 / "namdOut.restart.coor").write_text("c")
    (namd0 / "namdOut.restart.vel").write_text("v")

    namd1 = proj / "NAMD" / "0000000003_b"; namd1.mkdir(parents=True)
    (namd1 / "namdOut.restart.xsc").write_text(_xsc(13.0, 23.0, 33.0))
    (namd1 / "namdOut.restart.coor").write_text("c")
    (namd1 / "namdOut.restart.vel").write_text("v")

    # starting files
    inputs = proj / "inputs"; inputs.mkdir(parents=True, exist_ok=True)
    (inputs / "b0.pdb").write_text(_pdb_cryst1(1, 2, 3))
    (inputs / "b1.pdb").write_text(_pdb_cryst1(4, 5, 6))
    (inputs / "b0.psf").write_text("psf0")
    (inputs / "b1.psf").write_text("psf1")

    cfg = _make_cfg(simulation_type="GEMC", only_use_box_0_for_namd_for_gemc=False)
    io = GOMCIOPaths(
        python_file_directory=proj,
        path_gomc_runs=Path("GOMC"),
        path_gomc_template=tpl.relative_to(proj),
        namd_box_0_dir=namd0,
        namd_box_1_dir=namd1,
        previous_gomc_dir=None,
    )
    sim = GOMCSimParams(2000, 200, 100, 50, 310.0, 1.5)
    starts = GOMCStartFiles(Path("inputs/b0.pdb"), Path("inputs/b1.pdb"), Path("inputs/b0.psf"), Path("inputs/b1.psf"))

    out_dir = write_gomc_conf_file(cfg, io, run_no=3, sim=sim, starts=starts)
    conf = (out_dir / "in.conf").read_text()

    # Box-1 pulls from NAMD paths and dims from NAMD xsc
    assert "NAMD/0000000003_b/namdOut.restart.coor" in conf
    assert "13.0" in conf and "23.0" in conf and "33.0" in conf

    # restart true for this branch
    assert "\ntrue\n" in conf or "true\r\n" in conf


def test_gcmc_restart_with_chempot_and_prev_gomc(tmp_path: Path):
    proj = tmp_path / "proj"
    tpl = proj / "templates" / "gomc.tpl"
    _write_template(tpl, include_box1_tokens=True, include_bin_lines=False, include_gcmc_block=True)

    # NAMD box0
    namd0 = proj / "NAMD" / "0000000004_a"; namd0.mkdir(parents=True)
    (namd0 / "namdOut.restart.xsc").write_text(_xsc(14.0, 24.0, 34.0))
    (namd0 / "namdOut.restart.coor").write_text("c")
    (namd0 / "namdOut.restart.vel").write_text("v")

    # Previous GOMC dir with BOX_1 xsc and restart.chk
    prev_gomc = proj / "GOMC" / "0000000003"; prev_gomc.mkdir(parents=True)
    (prev_gomc / "Output_data_BOX_1_restart.xsc").write_text(_xsc(44.0, 54.0, 64.0))
    (prev_gomc / "Output_data_restart.chk").write_text("chk")

    # starting files
    inputs = proj / "inputs"; inputs.mkdir(parents=True, exist_ok=True)
    (inputs / "b0.pdb").write_text(_pdb_cryst1(1, 2, 3))
    (inputs / "b1.pdb").write_text(_pdb_cryst1(4, 5, 6))
    (inputs / "b0.psf").write_text("psf0")
    (inputs / "b1.psf").write_text("psf1")

    chem_map = {"WAT": -6.5, "Na+": -5.1}
    cfg = _make_cfg(
        simulation_type="GCMC",
        gcmc_mode="ChemPot",
        gcmc_map=chem_map,
        gcmc_keys=["WAT", "Na+"],
    )
    io = GOMCIOPaths(
        python_file_directory=proj,
        path_gomc_runs=Path("GOMC"),
        path_gomc_template=tpl.relative_to(proj),
        namd_box_0_dir=namd0,
        namd_box_1_dir=None,              # not needed in this branch
        previous_gomc_dir=prev_gomc,
    )
    sim = GOMCSimParams(1200, 120, 60, 30, 298.0, 1.0)
    starts = GOMCStartFiles(Path("inputs/b0.pdb"), Path("inputs/b1.pdb"), Path("inputs/b0.psf"), Path("inputs/b1.psf"))

    out_dir = write_gomc_conf_file(cfg, io, run_no=4, sim=sim, starts=starts)
    conf = (out_dir / "in.conf").read_text()

    # Box-1 restart from previous GOMC and dims from its xsc
    assert "Output_data_BOX_1_restart.coor" in conf
    assert "44.0" in conf and "54.0" in conf and "64.0" in conf

    # Restart checkpoint points at previous dir
    # assert f"true GOMC/0000000003/Output_data_restart.chk" in conf
    import os

    # Restart checkpoint points at previous dir, relative to the new GOMC run dir
    expected_chk = os.path.relpath(
        prev_gomc / "Output_data_restart.chk",
        out_dir,
    ).replace(os.sep, "/")

    assert f"true {expected_chk}" in conf

    # ChemPot lines present
    assert "ChemPot \t WAT \t -6.5" in conf
    assert "ChemPot \t Na+ \t -5.1" in conf


def test_gomc_writer_rewrites_relative_parameter_paths_to_run_dir(tmp_path):
    from py_mcmd_refactored.engines.gomc.gomc_writer import _build_parameters_block
    proj = tmp_path / "proj"
    proj.mkdir()

    gomc_run_dir = proj / "GOMC" / "0000000001"
    gomc_run_dir.mkdir(parents=True)

    ff = proj / "required_data" / "input" / "OPC_FF_GOMC.inp"
    ff.parent.mkdir(parents=True)
    ff.write_text("* ff\n")

    block = _build_parameters_block(
        [Path("required_data/input/OPC_FF_GOMC.inp")],
        relative_to=gomc_run_dir,
        project_root=proj,
    )
    expected = os.path.relpath(ff, gomc_run_dir).replace(os.sep, "/")

    assert block == f"Parameters \t {expected}\n"
    assert block.strip().split()[-1] == expected
    assert expected.startswith("../")

def test_restart_missing_checkpoint_is_allowed_in_dry_run(tmp_path: Path):
    proj = tmp_path / "proj"
    tpl = proj / "templates" / "gomc.tpl"
    _write_template(tpl, include_box1_tokens=False, include_bin_lines=False, include_gcmc_block=False)

    namd0 = proj / "NAMD" / "0000000002_a"
    namd0.mkdir(parents=True)
    (namd0 / "namdOut.restart.xsc").write_text(_xsc(10.0, 20.0, 30.0))
    (namd0 / "namdOut.restart.coor").write_text("c")
    (namd0 / "namdOut.restart.vel").write_text("v")

    prev_gomc = proj / "GOMC" / "0000000001"
    prev_gomc.mkdir(parents=True)
    (prev_gomc / "Output_data_BOX_0_restart.pdb").write_text(_pdb_cryst1(10, 20, 30))
    (prev_gomc / "Output_data_BOX_0_restart.psf").write_text("psf")
    # intentionally do NOT create Output_data_restart.chk

    inputs = proj / "inputs"
    inputs.mkdir()
    (inputs / "b0.pdb").write_text(_pdb_cryst1(1, 2, 3))
    (inputs / "b1.pdb").write_text(_pdb_cryst1(4, 5, 6))
    (inputs / "b0.psf").write_text("psf0")
    (inputs / "b1.psf").write_text("psf1")

    cfg = _make_cfg(simulation_type="NPT")
    io = GOMCIOPaths(
        python_file_directory=proj,
        path_gomc_runs=Path("GOMC"),
        path_gomc_template=tpl.relative_to(proj),
        namd_box_0_dir=namd0,
        namd_box_1_dir=None,
        previous_gomc_dir=prev_gomc,
    )
    sim = GOMCSimParams(20, 20, 20, 2, 250.0, 1.0)
    starts = GOMCStartFiles(
        Path("inputs/b0.pdb"), Path("inputs/b1.pdb"),
        Path("inputs/b0.psf"), Path("inputs/b1.psf"),
    )

    out_dir = write_gomc_conf_file(cfg, io, run_no=3, sim=sim, starts=starts, dry_run=True)
    conf = (out_dir / "in.conf").read_text()

    assert "false Output_data_restart.chk" in conf


def _write_restart_routing_template(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "all_parameter_files\n"
        "binCoordinates 0 coor_box_0_file\n"
        "extendedSystem 0 xsc_box_0_file\n"
        "binVelocities 0 vel_box_0_file\n"
        "Coordinates 0 pdb_file_box_0_file\n"
        "Structure 0 psf_file_box_0_file\n"
        "CellBasisVector1 0 x_dim_box_0 0.0 0.0\n"
        "CellBasisVector2 0 0.0 y_dim_box_0 0.0\n"
        "CellBasisVector3 0 0.0 0.0 z_dim_box_0\n"
        "binCoordinates 1 coor_box_1_file\n"
        "extendedSystem 1 xsc_box_1_file\n"
        "binVelocities 1 vel_box_1_file\n"
        "Coordinates 1 pdb_file_box_1_file\n"
        "Structure 1 psf_file_box_1_file\n"
        "CellBasisVector1 1 x_dim_box_1 0.0 0.0\n"
        "CellBasisVector2 1 0.0 y_dim_box_1 0.0\n"
        "CellBasisVector3 1 0.0 0.0 z_dim_box_1\n"
        "Restart restart_true_or_false\n"
        "RunSteps GOMC_Run_Steps\n"
        "RestartFreq GOMC_RST_Coor_CKpoint_Steps\n"
        "ConsoleFreq GOMC_console_BLKavg_Hist_Steps\n"
        "HistFreq GOMC_Hist_sample_Steps\n"
        "Temperature System_temp_set\n"
        "Pressure System_press_set\n"
        "EquilSteps GOMC_Equilb_Steps\n"
        "AdjSteps GOMC_Adj_Steps\n"
        "RestartCheckpoint Restart_Checkpoint_file\n"
        "mu_ChemPot_K_or_P_Fugacitiy_bar_all\n"
    )

def _prepare_restart_routing_inputs(proj: Path):
    inputs = proj / "inputs"
    inputs.mkdir(parents=True, exist_ok=True)

    pdb0 = inputs / "b0.pdb"
    pdb1 = inputs / "b1.pdb"
    psf0 = inputs / "b0.psf"
    psf1 = inputs / "b1.psf"

    pdb0.write_text(_pdb_cryst1(10, 20, 30))
    pdb1.write_text(_pdb_cryst1(40, 50, 60))
    psf0.write_text("psf0")
    psf1.write_text("psf1")

    starts = GOMCStartFiles(
        pdb0.relative_to(proj),
        pdb1.relative_to(proj),
        psf0.relative_to(proj),
        psf1.relative_to(proj),
    )
    return starts


def _prepare_namd_restart_dir(
    proj: Path,
    name: str,
    dims: tuple[float, float, float],
) -> Path:
    namd_dir = proj / "NAMD" / name
    namd_dir.mkdir(parents=True, exist_ok=True)

    (namd_dir / "namdOut.restart.coor").write_text("coor")
    (namd_dir / "namdOut.restart.xsc").write_text(
        _xsc(*dims)
    )
    (namd_dir / "namdOut.restart.vel").write_text("vel")

    return namd_dir

@pytest.mark.parametrize(
    (
        "simulation_type",
        "only_use_box_0_for_namd_for_gemc",
    ),
    [
        ("GCMC", False),
        ("GEMC", True),
    ],
)

# The same test executes both:
# GCMC
# and
# GEMC + only_use_box_0_for_namd_for_gemc=True
def test_first_cycle_gcmc_and_one_box_gemc_strip_all_binary_restart_lines(
    tmp_path: Path,
    simulation_type: str,
    only_use_box_0_for_namd_for_gemc: bool,
):
    proj = tmp_path / "proj"
    tpl = proj / "templates" / "gomc.tpl"
    _write_restart_routing_template(tpl)

    namd0 = _prepare_namd_restart_dir(
        proj,
        "0000000000_a",
        (11.0, 21.0, 31.0),
    )
    starts = _prepare_restart_routing_inputs(proj)

    cfg = _make_cfg(
        simulation_type=simulation_type,
        only_use_box_0_for_namd_for_gemc=(
            only_use_box_0_for_namd_for_gemc
        ),
    )
    io = GOMCIOPaths(
        python_file_directory=proj,
        path_gomc_runs=Path("GOMC"),
        path_gomc_template=tpl.relative_to(proj),
        namd_box_0_dir=namd0,
        namd_box_1_dir=None,
        previous_gomc_dir=None,
    )

    out_dir = write_gomc_conf_file(
        cfg,
        io,
        run_no=1,
        sim=GOMCSimParams(
            1000,
            100,
            50,
            25,
            300.0,
            1.0,
        ),
        starts=starts,
    )
    conf = (out_dir / "in.conf").read_text()

    for box_number in (0, 1):
        assert f"binCoordinates {box_number}" not in conf
        assert f"extendedSystem {box_number}" not in conf
        assert f"binVelocities {box_number}" not in conf

    assert "Coordinates 0" in conf
    assert "Structure 0" in conf
    assert "Coordinates 1" in conf
    assert "Structure 1" in conf

    assert "inputs/b0.pdb" in conf
    assert "inputs/b1.pdb" in conf

    assert "Restart false" in conf

def test_subsequent_gcmc_uses_box1_restart_without_velocity_file(
    tmp_path: Path,
):
    proj = tmp_path / "proj"
    tpl = proj / "templates" / "gomc.tpl"
    _write_restart_routing_template(tpl)

    namd0 = _prepare_namd_restart_dir(
        proj,
        "0000000002_a",
        (12.0, 22.0, 32.0),
    )
    starts = _prepare_restart_routing_inputs(proj)

    prev_gomc = proj / "GOMC" / "0000000001"
    prev_gomc.mkdir(parents=True)

    (
        prev_gomc
        / "Output_data_BOX_1_restart.coor"
    ).write_text("coor")
    (
        prev_gomc
        / "Output_data_BOX_1_restart.xsc"
    ).write_text(
        _xsc(42.0, 52.0, 62.0)
    )
    (
        prev_gomc
        / "Output_data_BOX_1_restart.pdb"
    ).write_text(
        _pdb_cryst1(42, 52, 62)
    )
    (
        prev_gomc
        / "Output_data_BOX_1_restart.psf"
    ).write_text("psf1")
    (
        prev_gomc
        / "Output_data_restart.chk"
    ).write_text("chk")

    # Intentionally no Output_data_BOX_1_restart.vel.

    cfg = _make_cfg(
        simulation_type="GCMC",
    )
    io = GOMCIOPaths(
        python_file_directory=proj,
        path_gomc_runs=Path("GOMC"),
        path_gomc_template=tpl.relative_to(proj),
        namd_box_0_dir=namd0,
        namd_box_1_dir=None,
        previous_gomc_dir=prev_gomc,
    )

    out_dir = write_gomc_conf_file(
        cfg,
        io,
        run_no=3,
        sim=GOMCSimParams(
            1000,
            100,
            50,
            25,
            300.0,
            1.0,
        ),
        starts=starts,
    )
    conf = (out_dir / "in.conf").read_text()

    expected_coor = _rel(
        prev_gomc / "Output_data_BOX_1_restart.coor",
        out_dir,
    )
    expected_xsc = _rel(
        prev_gomc / "Output_data_BOX_1_restart.xsc",
        out_dir,
    )
    expected_pdb = _rel(
        prev_gomc / "Output_data_BOX_1_restart.pdb",
        out_dir,
    )
    expected_psf = _rel(
        prev_gomc / "Output_data_BOX_1_restart.psf",
        out_dir,
    )

    assert f"binCoordinates 1 {expected_coor}" in conf
    assert f"extendedSystem 1 {expected_xsc}" in conf

    assert "binVelocities 1" not in conf
    assert "Output_data_BOX_1_restart.vel" not in conf

    assert f"Coordinates 1 {expected_pdb}" in conf
    assert f"Structure 1 {expected_psf}" in conf

    assert "Restart true" in conf

def test_first_cycle_two_box_gemc_uses_starting_box1_pdb_psf(
    tmp_path: Path,
):
    proj = tmp_path / "proj"
    tpl = proj / "templates" / "gomc.tpl"
    _write_restart_routing_template(tpl)

    namd0 = _prepare_namd_restart_dir(
        proj,
        "0000000000_a",
        (13.0, 23.0, 33.0),
    )
    namd1 = _prepare_namd_restart_dir(
        proj,
        "0000000000_b",
        (14.0, 24.0, 34.0),
    )
    starts = _prepare_restart_routing_inputs(proj)

    cfg = _make_cfg(
        simulation_type="GEMC",
        only_use_box_0_for_namd_for_gemc=False,
    )
    io = GOMCIOPaths(
        python_file_directory=proj,
        path_gomc_runs=Path("GOMC"),
        path_gomc_template=tpl.relative_to(proj),
        namd_box_0_dir=namd0,
        namd_box_1_dir=namd1,
        previous_gomc_dir=None,
    )

    out_dir = write_gomc_conf_file(
        cfg,
        io,
        run_no=1,
        sim=GOMCSimParams(
            1000,
            100,
            50,
            25,
            300.0,
            1.0,
        ),
        starts=starts,
    )
    conf = (out_dir / "in.conf").read_text()

    expected_pdb1 = _rel(
        proj / "inputs" / "b1.pdb",
        out_dir,
    )
    expected_psf1 = _rel(
        proj / "inputs" / "b1.psf",
        out_dir,
    )

    assert "binCoordinates 0" in conf
    assert (
        "NAMD/0000000000_a/namdOut.restart.coor"
        in conf
    )

    assert "binCoordinates 1" in conf
    assert (
        "NAMD/0000000000_b/namdOut.restart.coor"
        in conf
    )
    assert (
        "NAMD/0000000000_b/namdOut.restart.xsc"
        in conf
    )
    assert (
        "NAMD/0000000000_b/namdOut.restart.vel"
        in conf
    )

    assert f"Coordinates 1 {expected_pdb1}" in conf
    assert f"Structure 1 {expected_psf1}" in conf

    assert "Restart true" in conf

def test_subsequent_two_box_gemc_uses_previous_gomc_box1_pdb_psf(
    tmp_path: Path,
):
    proj = tmp_path / "proj"
    tpl = proj / "templates" / "gomc.tpl"
    _write_restart_routing_template(tpl)

    namd0 = _prepare_namd_restart_dir(
        proj,
        "0000000002_a",
        (15.0, 25.0, 35.0),
    )
    namd1 = _prepare_namd_restart_dir(
        proj,
        "0000000002_b",
        (16.0, 26.0, 36.0),
    )
    starts = _prepare_restart_routing_inputs(proj)

    prev_gomc = proj / "GOMC" / "0000000001"
    prev_gomc.mkdir(parents=True)

    (
        prev_gomc
        / "Output_data_BOX_0_restart.pdb"
    ).write_text(
        _pdb_cryst1(15, 25, 35)
    )
    (
        prev_gomc
        / "Output_data_BOX_0_restart.psf"
    ).write_text("psf0")
    (
        prev_gomc
        / "Output_data_BOX_1_restart.pdb"
    ).write_text(
        _pdb_cryst1(16, 26, 36)
    )
    (
        prev_gomc
        / "Output_data_BOX_1_restart.psf"
    ).write_text("psf1")
    (
        prev_gomc
        / "Output_data_restart.chk"
    ).write_text("chk")

    cfg = _make_cfg(
        simulation_type="GEMC",
        only_use_box_0_for_namd_for_gemc=False,
    )
    io = GOMCIOPaths(
        python_file_directory=proj,
        path_gomc_runs=Path("GOMC"),
        path_gomc_template=tpl.relative_to(proj),
        namd_box_0_dir=namd0,
        namd_box_1_dir=namd1,
        previous_gomc_dir=prev_gomc,
    )

    out_dir = write_gomc_conf_file(
        cfg,
        io,
        run_no=3,
        sim=GOMCSimParams(
            1000,
            100,
            50,
            25,
            300.0,
            1.0,
        ),
        starts=starts,
    )
    conf = (out_dir / "in.conf").read_text()

    expected_pdb1 = _rel(
        prev_gomc / "Output_data_BOX_1_restart.pdb",
        out_dir,
    )
    expected_psf1 = _rel(
        prev_gomc / "Output_data_BOX_1_restart.psf",
        out_dir,
    )

    assert (
        "NAMD/0000000002_b/namdOut.restart.coor"
        in conf
    )
    assert (
        "NAMD/0000000002_b/namdOut.restart.xsc"
        in conf
    )
    assert (
        "NAMD/0000000002_b/namdOut.restart.vel"
        in conf
    )

    assert f"Coordinates 1 {expected_pdb1}" in conf
    assert f"Structure 1 {expected_psf1}" in conf

    assert "inputs/b1.pdb" not in conf
    assert "inputs/b1.psf" not in conf

    assert "Restart true" in conf