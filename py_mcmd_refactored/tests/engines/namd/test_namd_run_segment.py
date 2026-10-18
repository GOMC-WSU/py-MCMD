# py_mcmd_refactored/tests/test_namd_run_segment.py

from __future__ import annotations

from pathlib import Path

import pytest
from config.models import SimulationConfig
from engines.namd_engine import NamdEngine
from orchestrator.state import PmeDims, RunState


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


def _write_minimal_namd_out(
    out_path: Path, pot_i: float, pot_f: float, vpe_i: float, vpe_f: float
) -> None:
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


def test_run_segment_run0_updates_step_includes_minimize(
    tmp_path: Path, monkeypatch_writer
):
    cfg = _cfg(tmp_path, starting_sims_namd_gomc=0)
    eng = NamdEngine(cfg, dry_run=True)
    st = _state()

    res = eng.run_segment(run_no=0, state=st)
    out0 = Path(res["namd_box0_dir"]) / "out.dat"

    _write_minimal_namd_out(out0, pot_i=1.0, pot_f=2.0, vpe_i=3.0, vpe_f=4.0)
    st.current_step = 0
    eng.run_segment(run_no=0, state=st)

    assert st.current_step == cfg.namd_run_steps + cfg.namd_minimize_steps


def test_run_segment_nonzero_updates_step_without_minimize(
    tmp_path: Path, monkeypatch_writer
):
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


def test_run_segment_skips_continuity_check_on_first_segment_after_restart(
    tmp_path: Path, monkeypatch, monkeypatch_writer
):
    cfg = _cfg(
        tmp_path, starting_sims_namd_gomc=2, starting_at_cycle_namd_gomc_sims=1
    )
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
    _write_minimal_namd_out(
        out0, pot_i=10.0, pot_f=11.0, vpe_i=20.0, vpe_f=21.0
    )

    eng.run_segment(run_no=2, state=st)
    assert called["n"] == 0


def test_run_segment_calls_continuity_check_when_expected(
    tmp_path: Path, monkeypatch, monkeypatch_writer
):
    cfg = _cfg(tmp_path, starting_sims_namd_gomc=0)
    eng = NamdEngine(cfg, dry_run=True)
    st = _state()

    # REQUIRED: create run0 dir for FFT lookup when run_no != 0
    (tmp_path / "NAMD" / "00000000_a").mkdir(parents=True, exist_ok=True)

    st.energy_box0.gomc_potential_final = 10.0
    st.energy_box0.gomc_vdw_plus_elec_final = 20.0

    calls = []
    import engines.namd_engine as ne

    def fake_compare(
        cfg_, gomc_pot_f, namd_pot_i, gomc_vpe_f, namd_vpe_i, run_no, box_number
    ):
        calls.append(
            (gomc_pot_f, namd_pot_i, gomc_vpe_f, namd_vpe_i, run_no, box_number)
        )

    monkeypatch.setattr(ne, "compare_namd_gomc_energies", fake_compare)

    res = eng.run_segment(run_no=2, state=st)
    out0 = Path(res["namd_box0_dir"]) / "out.dat"
    _write_minimal_namd_out(
        out0, pot_i=10.0, pot_f=11.0, vpe_i=20.0, vpe_f=21.0
    )

    eng.run_segment(run_no=2, state=st)

    assert len(calls) == 1
    assert calls[0][-2:] == (2, 0)  # run_no=2, box=0


def test_run_segment_two_box_parallel_creates_both_out_files(
    tmp_path: Path, monkeypatch_writer
):
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


@pytest.mark.parametrize("template_mode", ["per_box", "shared", "automatic"])
def test_two_box_templates_and_parallel_execution_through_restart(
    tmp_path, monkeypatch, template_mode
):
    """Render real inputs and verify launch order and per-box restart data."""
    from utils.subprocess_runner import DryRunSubprocessRunner

    repo = Path(__file__).resolve().parents[4]
    shared = repo / "required_data/config_files/namd/nvt.conf"
    liquid = repo / "required_data/config_files/namd/gemc_liquid.conf"
    gas = repo / "required_data/config_files/namd/gemc_gas.conf"
    cfg = _cfg(
        tmp_path, simulation_type="GEMC",
        only_use_box_0_for_namd_for_gemc=False,
        namd_simulation_order="parallel", no_core_box_0=2, no_core_box_1=3,
        path_namd_template=str(shared) if template_mode != "automatic" else None,
        path_namd_template_box_0=str(liquid) if template_mode == "per_box" else None,
        path_namd_template_box_1=str(gas) if template_mode == "per_box" else None,
    )
    monkeypatch.chdir(tmp_path)
    if template_mode == "automatic":
        (tmp_path / "required_data").symlink_to(
            repo / "required_data", target_is_directory=True
        )
    for box in (0, 1):
        (tmp_path / f"box{box}.pdb").write_text(
            f"CRYST1 {25 + 75 * box} {25 + 75 * box} {25 + 75 * box} 90 90 90\n"
        )
        (tmp_path / f"box{box}.psf").write_text("PSF\n 1 !NATOM\n")

    class RecordingRunner(DryRunSubprocessRunner):
        def __init__(self):
            super().__init__()
            self.calls = []

        def start(self, cmd):
            self.calls.append(("start", cmd))
            return super().start(cmd)

        def wait(self, handle):
            self.calls.append(("wait", handle.command))
            return super().wait(handle)

    eng = NamdEngine(cfg, dry_run=True)
    eng.runner = RecordingRunner()
    st = _state()
    for run_no in (0, 2):
        eng.runner.calls.clear()
        result = eng.run_segment(run_no=run_no, state=st)
        assert result["mode"] == "parallel"
        assert [kind for kind, _ in eng.runner.calls] == [
            "start", "start", "wait", "wait"
        ]
        assert eng.runner.calls[0][1].argv[1] == "+p2"
        assert eng.runner.calls[1][1].argv[1] == "+p3"
        for box in (0, 1):
            conf = (Path(result[f"namd_box{box}_dir"]) / "in.conf").read_text()
            expected = "4.0" if template_mode != "shared" and box == 1 else (
                "1.0" if template_mode != "shared" else "1"
            )
            assert f"PMEGridSpacing      {expected}\n" in conf
            expected_cutoff = "8.0" if template_mode == "shared" else (
                "12.0" if box == 0 else "50.0"
            )
            assert f"cutoff              {expected_cutoff}\n" in conf
            assert "PMEGridSizeX        ${PME_Grid_Size_X}" not in (
                "\n".join(
                    line for line in conf.splitlines()
                    if not line.startswith("#")
                )
            )
            if run_no == 2:
                assert f"Output_data_BOX_{box}_restart.pdb" in conf

        if run_no == 0:
            # GOMC changes dimensions and molecule counts before the next MD.
            previous_mc = tmp_path / "previous_mc"
            previous_mc.mkdir()
            for box in (0, 1):
                dim = 30 + 80 * box
                (previous_mc / f"Output_data_BOX_{box}_restart.pdb").write_text(
                    f"CRYST1 {dim} {dim} {dim} 90 90 90\n"
                )
                (previous_mc / f"Output_data_BOX_{box}_restart.psf").write_text(
                    "PSF\n 2 !NATOM\n"
                )
            st.gomc_dir = previous_mc


def test_missing_gas_template_fails_before_starting_either_box(
    tmp_path, monkeypatch
):
    repo = Path(__file__).resolve().parents[4]
    cfg = _cfg(
        tmp_path, simulation_type="GEMC",
        only_use_box_0_for_namd_for_gemc=False,
        path_namd_template=str(repo / "required_data/config_files/namd/nvt.conf"),
        path_namd_template_box_1=str(tmp_path / "missing.conf"),
        starting_pdb_box_0_file=str(
            repo / "required_data/input/GEMC_OPC_T350_N1000_BOX_0.pdb"
        ),
    )
    eng = NamdEngine(cfg, dry_run=True)
    monkeypatch.setattr(
        eng.runner, "start", lambda cmd: pytest.fail("started NAMD")
    )
    with pytest.raises(FileNotFoundError, match="NAMD template not found"):
        eng.run_segment(run_no=0, state=_state())


@pytest.mark.parametrize("ensemble", ["NPT", "NVT", "GCMC"])
def test_non_gemc_uses_shared_template_and_ignores_gemc_overrides(
    tmp_path, ensemble
):
    repo = Path(__file__).resolve().parents[4]
    pdb = tmp_path / "box0.pdb"
    pdb.write_text("CRYST1 25 25 25 90 90 90\n")
    cfg = _cfg(
        tmp_path, simulation_type=ensemble,
        only_use_box_0_for_namd_for_gemc=False,
        namd_simulation_order="parallel",
        path_namd_template=str(repo / "required_data/config_files/namd/nvt.conf"),
        path_namd_template_box_0=str(tmp_path / "unused_liquid.conf"),
        path_namd_template_box_1=str(tmp_path / "unused_gas.conf"),
        starting_pdb_box_0_file=str(pdb),
        GCMC_ChemPot_or_Fugacity="ChemPot" if ensemble == "GCMC" else None,
        GCMC_ChemPot_or_Fugacity_dict={"TIP4": -1000} if ensemble == "GCMC" else None,
    )
    engine = NamdEngine(cfg, dry_run=True)
    result = engine.run_segment(run_no=0, state=_state())
    assert result["mode"] == "series"
    assert result["namd_box1_dir"] is None
    text = (Path(result["namd_box0_dir"]) / "in.conf").read_text()
    assert "# NAMD NVT MD segment for hybrid NVT, NPT, GCMC" in text


@pytest.mark.parametrize("ensemble", ["NPT", "GCMC"])
def test_single_box_selects_its_workflow_template_without_explicit_paths(
    tmp_path, ensemble
):
    pdb = tmp_path / "box0.pdb"
    pdb.write_text("CRYST1 25 25 25 90 90 90\n")
    cfg = _cfg(
        tmp_path, simulation_type=ensemble, path_namd_template=None,
        path_gomc_template=None, starting_pdb_box_0_file=str(pdb),
        GCMC_ChemPot_or_Fugacity="ChemPot" if ensemble == "GCMC" else None,
        GCMC_ChemPot_or_Fugacity_dict={"TIP4": -1000} if ensemble == "GCMC" else None,
    )
    assert cfg.path_namd_template.endswith(f"namd/{ensemble.lower()}.conf")
    assert cfg.path_gomc_template.endswith(f"gomc/{ensemble.lower()}.conf")
    engine = NamdEngine(cfg, dry_run=True)
    result = engine.run_segment(run_no=0, state=_state())
    assert result["namd_box1_dir"] is None
    text = (Path(result["namd_box0_dir"]) / "in.conf").read_text()
    assert f"# NAMD stage for the py-MCMD hybrid {ensemble} workflow." in text
    assert "langevinPiston        off" in text
    assert "cutoff              8.0" in text


@pytest.mark.parametrize("initial_waters", [0, 1])
def test_sparse_gas_skips_md_and_resumes_after_population_recovers(
    tmp_path, monkeypatch, monkeypatch_writer, initial_waters
):
    from engines.namd.sparse_box import SKIPPED_MARKER
    from tests.engines.namd.test_sparse_box import write_water_psf
    from utils.subprocess_runner import DryRunSubprocessRunner

    monkeypatch.chdir(tmp_path)
    previous = tmp_path / "GOMC" / "previous"
    previous.mkdir(parents=True)
    gas_psf = previous / "Output_data_BOX_1_restart.psf"
    write_water_psf(gas_psf, initial_waters)
    cfg = _cfg(tmp_path, simulation_type="GEMC",
               only_use_box_0_for_namd_for_gemc=False,
               namd_simulation_order="parallel")
    engine = NamdEngine(cfg, dry_run=True)
    engine.dry_run = False
    monkeypatch.setattr(engine, "link_run0_fft_file_into_dir", lambda *a, **k: None)

    class Recorder(DryRunSubprocessRunner):
        def __init__(self):
            super().__init__()
            self.started = []

        def start(self, cmd):
            self.started.append(cmd)
            return super().start(cmd)

        def wait(self, handle):
            rc = super().wait(handle)
            handle.command.stdout_path.write_text(
                "ETITLE: TS BOND ANGLE DIHED ELECT VDW POTENTIAL\n"
                "ENERGY: 0 0 0 0 -2 1 -1\n"
                "ENERGY: 10 0 0 0 -2 1 -1\n"
            )
            return rc

    engine.runner = Recorder()
    state = _state()
    state.gomc_dir = previous
    state.energy_box1.namd_potential_final = 123.0
    state.energy_box1.namd_potential_initial = 123.0
    state.energy_box1.namd_vdw_plus_elec_final = 123.0
    state.energy_box1.namd_vdw_plus_elec_initial = 123.0
    result = engine.run_segment(run_no=2, state=state)
    assert len(engine.runner.started) == 1
    assert result["gas_namd_skipped"]
    assert state.namd_box1_dir is None
    assert state.energy_box1.namd_potential_final is None
    assert state.energy_box1.namd_vdw_plus_elec_initial is None
    assert (Path(cfg.path_namd_runs) / "0000000002_b" / SKIPPED_MARKER).is_file()

    write_water_psf(gas_psf, 2)
    engine.runner.started.clear()
    result = engine.run_segment(run_no=4, state=state)
    assert len(engine.runner.started) == 2
    assert not result["gas_namd_skipped"]
    assert state.namd_box1_dir is not None
    assert state.energy_box1.namd_potential_final is not None
