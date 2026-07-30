# py_mcmd_refactored/tests/test_namd_run_segment.py

from __future__ import annotations

from pathlib import Path
import pytest

from config.models import SimulationConfig
from engines.namd_engine import NamdEngine
from orchestrator.state import RunState, PmeDims


def _cfg(tmp_path: Path, **kw) -> SimulationConfig:
    base = dict(
        total_cycles_namd_gomc_sims=2,
        starting_at_cycle_namd_gomc_sims=0,
        simulation_type="NPT",
        gomc_use_CPU_or_GPU="CPU",
        only_use_box_0_for_namd_for_gemc=True,
        no_core_box_0=2,
        no_core_box_1=2,
        simulation_temp_k=298.15,
        simulation_pressure_bar=1.0,
        namd_minimize_mult_scalar=1,
        namd_run_steps=10,
        gomc_run_steps=5,
        # derived fields expected by your refactored config
        namd_minimize_steps=10,
        namd_rst_dcd_xst_steps=10,
        namd_console_blkavg_e_and_p_steps=10,
        gomc_rst_coor_ckpoint_steps=5,
        gomc_console_blkavg_hist_steps=5,
        gomc_hist_sample_steps=5,
        set_dims_box_0_list=[25.0, 25.0, 25.0],
        set_dims_box_1_list=[25.0, 25.0, 25.0],
        set_angle_box_0_list=[90, 90, 90],
        set_angle_box_1_list=[90, 90, 90],
        starting_ff_file_list_gomc=["ff_gomc.inp"],
        starting_ff_file_list_namd=["ff_namd.inp"],
        starting_pdb_box_0_file="box0.pdb",
        starting_psf_box_0_file="box0.psf",
        starting_pdb_box_1_file="box1.pdb",
        starting_psf_box_1_file="box1.psf",
        namd2_bin_directory=str(tmp_path / "bin_namd"),
        gomc_bin_directory=str(tmp_path / "bin_gomc"),
        path_namd_runs=str(tmp_path / "NAMD"),
        path_gomc_runs=str(tmp_path / "GOMC"),
        path_namd_template=str(tmp_path / "templates" / "namd.inp"),
        path_gomc_template=str(tmp_path / "templates" / "gomc.inp"),
        log_dir=str(tmp_path / "logs"),
        namd_simulation_order="series",
        total_no_cores=4,
        starting_sims_namd_gomc=0,
        total_sims_namd_gomc=4,
    )
    base.update(kw)
    return SimulationConfig(**base)


def _state() -> RunState:
    st = RunState(current_step=0)
    st.pme_box0 = PmeDims()
    st.pme_box1 = PmeDims()
    return st


def _write_minimal_namd_out(out_path: Path, pot_i: float, pot_f: float, vpe_i: float, vpe_f: float) -> None:
    """
    Minimal out.dat fixture. If your parser expects different tokens,
    tweak these lines to match get_namd_energy_data() logic.
    """
    text = (
        "ETITLE: TS BOND ANGLE DIHED IMPRP ELECT VDW TOTAL TEMP POTENTIAL\n"
        f"ENERGY: 0 0 0 0 0 0 0 0 0 0 {pot_i}\n"
        f"ENERGY: 1 0 0 0 0 0 0 0 0 0 {pot_f}\n"
        f"VDW_PLUS_ELEC: {vpe_i}\n"
        f"VDW_PLUS_ELEC: {vpe_f}\n"
    )
    out_path.write_text(text, encoding="utf-8")


@pytest.fixture
def monkeypatch_writer(monkeypatch):
    """
    Patch write_namd_conf_file so run_segment doesn't require real templates
    and produces deterministic per-run directories.
    """
    import engines.namd_engine as ne

    def fake_write_namd_conf_file(
        python_file_directory,
        path_namd_template,
        path_namd_runs,
        gomc_newdir,
        run_no,
        box_number,
        *args,
        **kwargs,
    ):
        run_root = Path(path_namd_runs)
        run_root.mkdir(parents=True, exist_ok=True)
        suffix = "a" if box_number == 0 else "b"

        run_dir = run_root / f"run_{int(run_no):02d}_{suffix}"
        run_dir.mkdir(parents=True, exist_ok=True)

        (run_dir / "in.conf").write_text("# dummy\n", encoding="utf-8")
        return str(run_dir)

    monkeypatch.setattr(ne, "write_namd_conf_file", fake_write_namd_conf_file)
    return True


def test_run_segment_run0_updates_step_includes_minimize(tmp_path: Path, monkeypatch_writer):
    cfg = _cfg(tmp_path, starting_sims_namd_gomc=0)
    eng = NamdEngine(cfg, dry_run=True)
    st = _state()

    res = eng.run_segment(run_no=0, state=st)
    out0 = Path(res["namd_box0_dir"]) / "out.dat"

    _write_minimal_namd_out(out0, pot_i=1.0, pot_f=2.0, vpe_i=3.0, vpe_f=4.0)
    st.current_step = 0
    eng.run_segment(run_no=0, state=st)

    assert st.current_step == cfg.namd_run_steps + cfg.namd_minimize_steps


def test_run_segment_nonzero_updates_step_without_minimize(tmp_path: Path, monkeypatch_writer):
    cfg = _cfg(tmp_path, starting_sims_namd_gomc=0)
    eng = NamdEngine(cfg, dry_run=True)
    st = _state()

    # REQUIRED: create run0 dir for FFT lookup when run_no != 0
    (tmp_path / "NAMD" / "00000000_a").mkdir(parents=True, exist_ok=True)

    res = eng.run_segment(run_no=2, state=st)
    out0 = Path(res["namd_box0_dir"]) / "out.dat"
    _write_minimal_namd_out(out0, pot_i=1.0, pot_f=2.0, vpe_i=3.0, vpe_f=4.0)

    st.current_step = 0
    eng.run_segment(run_no=2, state=st)

    assert st.current_step == cfg.namd_run_steps


def test_run_segment_skips_continuity_check_on_first_segment_after_restart(tmp_path: Path, monkeypatch, monkeypatch_writer):
    cfg = _cfg(tmp_path, starting_sims_namd_gomc=2, starting_at_cycle_namd_gomc_sims=1)
    eng = NamdEngine(cfg, dry_run=True)
    st = _state()

    # REQUIRED: create run0 dir for FFT lookup when run_no != 0
    (tmp_path / "NAMD" / "00000000_a").mkdir(parents=True, exist_ok=True)

    st.energy_box0.gomc_potential_final = 10.0
    st.energy_box0.gomc_vdw_plus_elec_final = 20.0

    called = {"n": 0}
    import engines.namd_engine as ne

    def fake_compare(*args, **kwargs):
        called["n"] += 1

    monkeypatch.setattr(ne, "compare_namd_gomc_energies", fake_compare)

    res = eng.run_segment(run_no=2, state=st)
    out0 = Path(res["namd_box0_dir"]) / "out.dat"
    _write_minimal_namd_out(out0, pot_i=10.0, pot_f=11.0, vpe_i=20.0, vpe_f=21.0)

    eng.run_segment(run_no=2, state=st)
    assert called["n"] == 0


def test_run_segment_calls_continuity_check_when_expected(tmp_path: Path, monkeypatch, monkeypatch_writer):
    cfg = _cfg(tmp_path, starting_sims_namd_gomc=0)
    eng = NamdEngine(cfg, dry_run=True)
    st = _state()

    # REQUIRED: create run0 dir for FFT lookup when run_no != 0
    (tmp_path / "NAMD" / "00000000_a").mkdir(parents=True, exist_ok=True)

    st.energy_box0.gomc_potential_final = 10.0
    st.energy_box0.gomc_vdw_plus_elec_final = 20.0

    calls = []
    import engines.namd_engine as ne

    def fake_compare(cfg_, gomc_pot_f, namd_pot_i, gomc_vpe_f, namd_vpe_i, run_no, box_number):
        calls.append((gomc_pot_f, namd_pot_i, gomc_vpe_f, namd_vpe_i, run_no, box_number))

    monkeypatch.setattr(ne, "compare_namd_gomc_energies", fake_compare)

    res = eng.run_segment(run_no=2, state=st)
    out0 = Path(res["namd_box0_dir"]) / "out.dat"
    _write_minimal_namd_out(out0, pot_i=10.0, pot_f=11.0, vpe_i=20.0, vpe_f=21.0)

    eng.run_segment(run_no=2, state=st)

    assert len(calls) == 1
    assert calls[0][-2:] == (2, 0)  # run_no=2, box=0


def test_run_segment_two_box_parallel_creates_both_out_files(tmp_path: Path, monkeypatch_writer):
    cfg = _cfg(
        tmp_path,
        simulation_type="GEMC",
        only_use_box_0_for_namd_for_gemc=False,
        namd_simulation_order="parallel",
        no_core_box_0=2,
        no_core_box_1=2,
        starting_sims_namd_gomc=0,
    )
    eng = NamdEngine(cfg, dry_run=True)
    st = _state()

    # REQUIRED: create run0 dirs for FFT lookup
    (tmp_path / "NAMD" / "00000000_a").mkdir(parents=True, exist_ok=True)
    (tmp_path / "NAMD" / "00000000_b").mkdir(parents=True, exist_ok=True)

    res = eng.run_segment(run_no=0, state=st)

    assert res["namd_box0_dir"] is not None
    assert res["namd_box1_dir"] is not None
    assert (Path(res["namd_box0_dir"]) / "out.dat").exists()
    assert (Path(res["namd_box1_dir"]) / "out.dat").exists()