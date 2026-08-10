from __future__ import annotations

from pathlib import Path

import pytest
from config.models import SimulationConfig
from engines.namd_engine import NamdEngine


def make_cfg(tmp: Path, **kw) -> SimulationConfig:
    base = dict(
        total_cycles_namd_gomc_sims=1,
        starting_at_cycle_namd_gomc_sims=0,
        simulation_type="NPT",
        gomc_use_CPU_or_GPU="CPU",
        only_use_box_0_for_namd_for_gemc=True,
        no_core_box_0=1,
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
        namd2_bin_directory=str(tmp / "bin_namd"),
        gomc_bin_directory=str(tmp / "bin_gomc"),
        path_namd_runs=str(tmp / "NAMD"),
        path_gomc_runs=str(tmp / "GOMC"),
        log_dir=str(tmp / "logs"),
    )
    base.update(kw)
    return SimulationConfig(**base)


def test_link_run0_fft_creates_symlink(tmp_path: Path):
    cfg = make_cfg(tmp_path)
    eng = NamdEngine(cfg, dry_run=True)

    run0_dir = tmp_path / "NAMD" / "00000000_a"
    run0_dir.mkdir(parents=True, exist_ok=True)
    fft_name = "FFTW_NAMD_plan.txt"
    src = run0_dir / fft_name
    src.write_text("dummy")

    dest_dir = tmp_path / "NAMD" / "00000002_a"
    dest_dir.mkdir(parents=True, exist_ok=True)

    eng.link_run0_fft_file_into_dir(0, dest_dir)

    dst = dest_dir / fft_name
    assert dst.is_symlink()
    assert dst.resolve() == src.resolve()


def test_link_run0_fft_overwrites_existing_file(tmp_path: Path):
    cfg = make_cfg(tmp_path)
    eng = NamdEngine(cfg, dry_run=True)

    run0_dir = tmp_path / "NAMD" / "00000000_a"
    run0_dir.mkdir(parents=True, exist_ok=True)
    fft_name = "FFTW_NAMD_plan.txt"
    src = run0_dir / fft_name
    src.write_text("dummy")

    dest_dir = tmp_path / "NAMD" / "00000002_a"
    dest_dir.mkdir(parents=True, exist_ok=True)
    (dest_dir / fft_name).write_text("old")  # existing regular file

    eng.link_run0_fft_file_into_dir(0, dest_dir)

    dst = dest_dir / fft_name
    assert dst.is_symlink()
    assert dst.resolve() == src.resolve()


def test_link_run0_fft_noop_when_not_found(tmp_path: Path, monkeypatch):
    cfg = make_cfg(tmp_path)
    eng = NamdEngine(cfg, dry_run=True)

    dest_dir = tmp_path / "NAMD" / "00000002_a"
    dest_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        NamdEngine,
        "get_run0_fft_filename",
        lambda self, bn: (None, str(tmp_path / "NAMD" / "00000000_a")),
    )

    eng.link_run0_fft_file_into_dir(0, dest_dir)
    assert list(dest_dir.iterdir()) == []


def test_link_run0_fft_skips_missing_source_file_in_dry_run(
    tmp_path: Path, monkeypatch
):
    cfg = make_cfg(tmp_path)
    eng = NamdEngine(cfg, dry_run=True)

    dest_dir = tmp_path / "NAMD" / "00000002_a"
    dest_dir.mkdir(parents=True, exist_ok=True)

    run0_dir = tmp_path / "NAMD" / "00000000_a"
    run0_dir.mkdir(parents=True, exist_ok=True)

    fft_name = "FFTW_NAMD_plan.txt"
    monkeypatch.setattr(
        NamdEngine,
        "get_run0_fft_filename",
        lambda self, bn: (fft_name, str(run0_dir)),
    )

    eng.link_run0_fft_file_into_dir(0, dest_dir)

    src = run0_dir / fft_name
    dst = dest_dir / fft_name

    assert not src.exists()
    assert not dst.exists()


def test_link_run0_fft_prefers_cached_copy_when_runtime_run0_removed(
    tmp_path: Path,
):
    cfg = make_cfg(tmp_path)
    eng = NamdEngine(cfg, dry_run=True)

    managed_root = tmp_path / "managed"
    cache_dir = managed_root / "_engine_cache" / "NAMD" / "run0_fft_box0"
    cache_dir.mkdir(parents=True, exist_ok=True)

    fft_name = "FFTW_NAMD_plan.txt"
    cached_src = cache_dir / fft_name
    cached_src.write_text("cached")

    dest_dir = tmp_path / "NAMD" / "00000004_a"
    dest_dir.mkdir(parents=True, exist_ok=True)

    eng.link_run0_fft_file_into_dir(
        0,
        dest_dir,
        run_root=tmp_path / "missing_runtime",
        managed_root=managed_root,
    )

    dst = dest_dir / fft_name
    assert dst.is_symlink()
    assert dst.resolve() == cached_src.resolve()
