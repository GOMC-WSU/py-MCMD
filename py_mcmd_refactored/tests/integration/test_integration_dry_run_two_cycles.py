# py_mcmd_refactored/tests/test_integration_dry_run_two_cycles.py

from __future__ import annotations

from pathlib import Path

import orchestrator.manager as mgr
import pytest
from config.models import SimulationConfig


def _cfg(tmp_path: Path, **overrides) -> SimulationConfig:
    base = dict(
        total_cycles_namd_gomc_sims=2,  # 2 cycles => run_no 0..3
        starting_at_cycle_namd_gomc_sims=0,
        gomc_use_CPU_or_GPU="CPU",
        simulation_type="NPT",
        only_use_box_0_for_namd_for_gemc=True,  # single-box NAMD
        no_core_box_0=2,
        no_core_box_1=0,
        simulation_temp_k=250,
        simulation_pressure_bar=1.0,
        GCMC_ChemPot_or_Fugacity="ChemPot",
        GCMC_ChemPot_or_Fugacity_dict={"WAT": -2000},
        namd_minimize_mult_scalar=1,
        namd_run_steps=10,
        gomc_run_steps=5,
        # derived fields (some configs compute these automatically, but tests keep explicit)
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
    base.update(overrides)
    return SimulationConfig(**base)


def test_integration_dry_run_two_cycles(tmp_path: Path, monkeypatch):
    """
    End-to-end dry-run that exercises the real orchestrator parity loop:
      NAMD(0) -> GOMC(1) -> NAMD(2) -> GOMC(3)
    while monkeypatching writers/parsers to avoid external templates/binaries.
    """
    cfg = _cfg(tmp_path)
    call_order = []

    # ---------------------------
    # Patch perf_counter for deterministic TIME_STATS
    # (even run_no start tick, odd run_no end tick)
    # cycle0 start=0 end=20; cycle1 start=100 end=130
    # ---------------------------

    import itertools

    tick_values = [0.0, 20.0, 100.0, 130.0]
    ticks = itertools.chain(tick_values, itertools.repeat(tick_values[-1]))
    monkeypatch.setattr(mgr.time, "perf_counter", lambda: next(ticks))

    # ---------------------------
    # Patch NAMD writer to create per-run dirs + in.conf
    # ---------------------------
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
        root = Path(path_namd_runs)
        root.mkdir(parents=True, exist_ok=True)
        suffix = "a" if box_number == 0 else "b"
        run_dir = root / f"run_{int(run_no):02d}_{suffix}"
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "in.conf").write_text("# dummy namd\n", encoding="utf-8")
        return str(run_dir)

    monkeypatch.setattr(ne, "write_namd_conf_file", fake_write_namd_conf_file)

    # ---------------------------
    # Patch GOMC writer to create per-run dirs + in.conf
    # ---------------------------
    from pathlib import Path

    import engines.gomc_engine as ge

    def fake_write_gomc_conf_file(cfg, io, run_no, sim, starts, **kwargs):
        root = Path(io.path_gomc_runs)
        root.mkdir(parents=True, exist_ok=True)
        run_dir = root / f"run_{int(run_no):02d}"
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "in.conf").write_text("# dummy gomc\n", encoding="utf-8")
        return str(run_dir)

    monkeypatch.setattr(ge, "write_gomc_conf_file", fake_write_gomc_conf_file)

    # ---------------------------
    # Patch energy parsers to deterministic values
    # - NAMD: set initial/final potential and vdw+elec
    # - GOMC: set initial/final potential and vdw+elec
    # ---------------------------
    def fake_get_namd_energy_data(lines, titles):
        # returns tuple expected by NamdEngine.run_segment parsing:
        # (elect_series, elect_init, elect_final,
        #  pot_series, pot_init, pot_final,
        #  vpe_series, vpe_init, vpe_final)
        return (None, None, None, None, 10.0, 11.0, None, 20.0, 21.0)

    monkeypatch.setattr(ne, "get_namd_energy_data", fake_get_namd_energy_data)

    monkeypatch.setattr(
        ge,
        "get_gomc_energy_data",
        lambda cfg, lines, box_number: object(),
    )
    monkeypatch.setattr(
        ge,
        "get_gomc_energy_data_kcal_per_mol",
        lambda df: (
            None,
            None,
            None,
            None,
            100.0,
            101.0,
            None,
            None,
            None,
            None,
            200.0,
            201.0,
        ),
    )

    # ---------------------------
    # Patch continuity compare to just record calls (no assertions on values here)
    # ---------------------------
    compare_calls = []

    monkeypatch.setattr(
        ne,
        "compare_namd_gomc_energies",
        lambda *args, **kwargs: compare_calls.append(
            ("GOMC->NAMD", args[-2], args[-1])
        ),
    )
    monkeypatch.setattr(
        ge,
        "compare_namd_gomc_energies",
        lambda *args, **kwargs: compare_calls.append(
            ("NAMD->GOMC", args[-2], args[-1])
        ),
    )

    # ---------------------------
    # Patch FFT run0 lookup so nonzero run_no does not require real run0 dirs
    # (Return (None, <some_dir>) so linking is skipped cleanly.)
    # ---------------------------
    monkeypatch.setattr(
        ne.NamdEngine,
        "get_run0_fft_filename",
        lambda self, bn: (None, str(tmp_path / "NAMD" / "00000000_a")),
    )

    # ---------------------------
    # Wrap engines to record call order while still using real run_segment logic
    # ---------------------------
    RealNamd = ne.NamdEngine
    RealGomc = ge.GomcEngine

    class TrackedNamd(RealNamd):
        def run_segment(self, *, run_no: int, state, fifo_resources=None):
            call_order.append(("NAMD", int(run_no)))
            state.timings.max_namd_cycle_time_s = 10.0
            return super().run_segment(
                run_no=run_no,
                state=state,
                fifo_resources=fifo_resources,
            )

    class TrackedGomc(RealGomc):
        def run_segment(self, *, run_no: int, state, fifo_resources=None):
            call_order.append(("GOMC", int(run_no)))
            state.timings.gomc_cycle_time_s = 5.0
            return super().run_segment(
                run_no=run_no,
                state=state,
                fifo_resources=fifo_resources,
            )

    monkeypatch.setattr(mgr, "NamdEngine", TrackedNamd)
    monkeypatch.setattr(mgr, "GomcEngine", TrackedGomc)

    # ---------------------------
    # Run orchestrator
    # ---------------------------
    orch = mgr.SimulationOrchestrator(cfg, dry_run=True)
    summary = orch.run()

    # Verify order: 0..3 with parity
    assert call_order == [("NAMD", 0), ("GOMC", 1), ("NAMD", 2), ("GOMC", 3)]
    assert summary["cycles_completed"] == 2

    # Verify step increments (legacy)
    expected_step = (
        (cfg.namd_run_steps + cfg.namd_minimize_steps)  # run_no=0
        + cfg.gomc_run_steps  # run_no=1
        + cfg.namd_run_steps  # run_no=2
        + cfg.gomc_run_steps  # run_no=3
    )
    assert orch.state.current_step == expected_step

    # TIME_STATS: header + 2 data lines
    lines = summary["time_stats_lines"]
    assert len(lines) == 3
    assert "TIME_STATS_TITLE" in lines[0]
    assert "TIME_STATS_DATA" in lines[1]
    assert "TIME_STATS_DATA" in lines[2]


def _patch_managed_store_dry_run_dependencies(tmp_path: Path, monkeypatch):
    import itertools

    import engines.gomc_engine as ge
    import engines.namd_engine as ne

    tick_values = [0.0, 20.0, 100.0, 130.0]
    ticks = itertools.chain(tick_values, itertools.repeat(tick_values[-1]))
    monkeypatch.setattr(mgr.time, "perf_counter", lambda: next(ticks))

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
        root = Path(path_namd_runs)
        root.mkdir(parents=True, exist_ok=True)
        suffix = "a" if int(box_number) == 0 else "b"
        run_dir = root / f"{int(run_no):010d}_{suffix}"
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "in.conf").write_text("# dummy namd\n", encoding="utf-8")
        return str(run_dir)

    def fake_write_gomc_conf_file(*args, **kwargs):
        run_no = kwargs.get("run_no")
        if run_no is None and len(args) >= 3:
            run_no = args[2]
        io = kwargs.get("io")
        if io is None and len(args) >= 2:
            io = args[1]

        root = Path(io.path_gomc_runs)
        root.mkdir(parents=True, exist_ok=True)
        run_dir = root / f"{int(run_no):010d}"
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "in.conf").write_text("# dummy gomc\n", encoding="utf-8")
        return str(run_dir)

    monkeypatch.setattr(ne, "write_namd_conf_file", fake_write_namd_conf_file)
    monkeypatch.setattr(ge, "write_gomc_conf_file", fake_write_gomc_conf_file)

    monkeypatch.setattr(
        ne,
        "get_namd_energy_data",
        lambda lines, titles: (
            None,
            None,
            None,
            None,
            10.0,
            11.0,
            None,
            20.0,
            21.0,
        ),
    )
    monkeypatch.setattr(
        ge, "get_gomc_energy_data", lambda cfg, lines, box_number: object()
    )
    monkeypatch.setattr(
        ge,
        "get_gomc_energy_data_kcal_per_mol",
        lambda df: (
            None,
            None,
            None,
            None,
            100.0,
            101.0,
            None,
            None,
            None,
            None,
            200.0,
            201.0,
        ),
    )

    monkeypatch.setattr(
        ne, "compare_namd_gomc_energies", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(
        ge, "compare_namd_gomc_energies", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(
        ne.NamdEngine,
        "get_run0_fft_filename",
        lambda self, bn: (None, str(tmp_path / "NAMD" / "0000000000_a")),
    )


# def test_integration_dry_run_default_mode_persists_only_out_dat_on_disk(tmp_path: Path, monkeypatch):
#     monkeypatch.setenv("PY_MCMD_MANAGED_OUTPUT_ROOT", str(tmp_path / "managed_runtime"))
#     _patch_managed_store_dry_run_dependencies(tmp_path, monkeypatch)

#     cfg = _cfg(tmp_path, developer_mode=False)
#     orch = mgr.SimulationOrchestrator(cfg, dry_run=True)
#     summary = orch.run()

#     assert summary["cycles_completed"] == 2

#     namd_disk_run0 = tmp_path / "NAMD" / "0000000000_a"
#     namd_disk_run2 = tmp_path / "NAMD" / "0000000002_a"
#     gomc_disk_run1 = tmp_path / "GOMC" / "0000000001"
#     gomc_disk_run3 = tmp_path / "GOMC" / "0000000003"

#     assert (namd_disk_run0 / "out.dat").exists()
#     assert (namd_disk_run2 / "out.dat").exists()
#     assert (gomc_disk_run1 / "out.dat").exists()
#     assert (gomc_disk_run3 / "out.dat").exists()

#     assert not (namd_disk_run0 / "in.conf").exists()
#     assert not (namd_disk_run2 / "in.conf").exists()
#     assert not (gomc_disk_run1 / "in.conf").exists()
#     assert not (gomc_disk_run3 / "in.conf").exists()


#     managed_root = tmp_path / "managed_runtime"
#     assert not (managed_root / "NAMD").exists()
#     assert not (managed_root / "GOMC").exists()
def test_integration_dry_run_default_mode_keeps_managed_outputs_off_disk(
    tmp_path: Path,
    monkeypatch,
):
    monkeypatch.setenv(
        "PY_MCMD_MANAGED_OUTPUT_ROOT",
        str(tmp_path / "managed_runtime"),
    )
    _patch_managed_store_dry_run_dependencies(tmp_path, monkeypatch)

    cfg = _cfg(tmp_path, developer_mode=False)
    orch = mgr.SimulationOrchestrator(cfg, dry_run=True)
    summary = orch.run()

    assert summary["cycles_completed"] == 2

    namd_disk_run0 = tmp_path / "NAMD" / "0000000000_a"
    namd_disk_run2 = tmp_path / "NAMD" / "0000000002_a"
    gomc_disk_run1 = tmp_path / "GOMC" / "0000000001"
    gomc_disk_run3 = tmp_path / "GOMC" / "0000000003"

    assert not (namd_disk_run0 / "out.dat").exists()
    assert not (namd_disk_run2 / "out.dat").exists()
    assert not (gomc_disk_run1 / "out.dat").exists()
    assert not (gomc_disk_run3 / "out.dat").exists()

    assert not (namd_disk_run0 / "in.conf").exists()
    assert not (namd_disk_run2 / "in.conf").exists()
    assert not (gomc_disk_run1 / "in.conf").exists()
    assert not (gomc_disk_run3 / "in.conf").exists()

    managed_root = tmp_path / "managed_runtime"
    assert not (managed_root / "NAMD").exists()
    assert not (managed_root / "GOMC").exists()


def test_integration_dry_run_developer_mode_mirrors_managed_outputs_to_disk(
    tmp_path: Path, monkeypatch
):
    monkeypatch.setenv(
        "PY_MCMD_MANAGED_OUTPUT_ROOT", str(tmp_path / "managed_runtime")
    )
    _patch_managed_store_dry_run_dependencies(tmp_path, monkeypatch)

    cfg = _cfg(tmp_path, developer_mode=True)
    orch = mgr.SimulationOrchestrator(cfg, dry_run=True)
    summary = orch.run()

    assert summary["cycles_completed"] == 2

    namd_disk_run0 = tmp_path / "NAMD" / "0000000000_a"
    namd_disk_run2 = tmp_path / "NAMD" / "0000000002_a"
    gomc_disk_run1 = tmp_path / "GOMC" / "0000000001"
    gomc_disk_run3 = tmp_path / "GOMC" / "0000000003"

    assert (namd_disk_run0 / "out.dat").exists()
    assert (namd_disk_run0 / "in.conf").exists()
    assert (namd_disk_run2 / "in.conf").exists()

    assert (gomc_disk_run1 / "out.dat").exists()
    assert (gomc_disk_run1 / "in.conf").exists()
    assert (gomc_disk_run3 / "in.conf").exists()

    managed_root = tmp_path / "managed_runtime"
    assert not (managed_root / "NAMD").exists()
    assert not (managed_root / "GOMC").exists()
