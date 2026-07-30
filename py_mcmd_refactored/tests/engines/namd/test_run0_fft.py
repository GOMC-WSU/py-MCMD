import sys
sys.path.insert(0, "/home/arsalan/wsu-gomc/py-MCMD-hm/py_mcmd_refactored")

from pathlib import Path
from config.models import SimulationConfig
from engines.namd_engine import NamdEngine
import pytest

def make_cfg(tmp: Path, **kw):
    base = dict(
        total_cycles_namd_gomc_sims=1,
        starting_at_cycle_namd_gomc_sims=0,
        simulation_type="NPT",
        gomc_use_CPU_or_GPU="CPU",
        only_use_box_0_for_namd_for_gemc=True,
        no_core_box_0=1, no_core_box_1=0,
        simulation_temp_k=298.15, simulation_pressure_bar=1.0,
        namd_minimize_mult_scalar=1, namd_run_steps=10, gomc_run_steps=10,
        set_dims_box_0_list=[25,25,25], set_angle_box_0_list=[90,90,90],
        set_dims_box_1_list=[25,25,25], set_angle_box_1_list=[90,90,90],
        starting_ff_file_list_gomc=["a.inp"], starting_ff_file_list_namd=["b.inp"],
        starting_pdb_box_0_file="box0.pdb", starting_psf_box_0_file="box0.psf",
        starting_pdb_box_1_file="box1.pdb", starting_psf_box_1_file="box1.psf",
        namd2_bin_directory=str(tmp/"bin_namd"),
        gomc_bin_directory=str(tmp/"bin_gomc"),
        path_namd_runs=str(tmp/"NAMD"),
        path_gomc_runs=str(tmp/"GOMC"),
        log_dir=str(tmp/"logs"),
    )
    base.update(kw)
    return SimulationConfig(**base)

# from engines.namd.parser import get_run0_fft_filename
def test_get_run0_fft_filename_found(tmp_path: Path):
    cfg = make_cfg(tmp_path)
    run0 = tmp_path / "NAMD" / "00000000_a"
    run0.mkdir(parents=True, exist_ok=True)
    (run0 / "FFTW_NAMD_plan.txt").write_text("dummy")
    eng = NamdEngine(cfg, dry_run=True)
    name, dir_str = eng.get_run0_fft_filename(0)
    assert name == "FFTW_NAMD_plan.txt"
    assert dir_str.endswith("NAMD/00000000_a")

def test_get_run0_fft_filename_missing(tmp_path: Path):
    cfg = make_cfg(tmp_path)
    eng = NamdEngine(cfg, dry_run=True)
    # name, dir_str = eng.get_run0_fft_filename(1)
    # assert name is None
    # assert dir_str.endswith("NAMD/00000000_b")
    with pytest.raises(FileNotFoundError):
        eng.get_run0_fft_filename(1)

# Target functions
from engines.namd.parser import get_run0_dir 
def test_get_run0_dir_builds_expected_path(tmp_path):
    base = tmp_path / "namd_runs"
    base.mkdir()
    # run id 0 with id_width=8 → "00000000"; box 0 → suffix 'a'
    p0 = get_run0_dir(base, box_number=0, id_width=8)
    p1 = get_run0_dir(base, box_number=1, id_width=8)
    assert p0.name.endswith("_a")
    assert p1.name.endswith("_b")
    assert p0.parent == base
    assert p1.parent == base

def test_get_run0_fft_filename_passthrough_when_not_found(tmp_path, monkeypatch):
    # Force the finder to return None regardless of files
    monkeypatch.setattr("engines.namd.parser.find_run0_fft_filename", lambda _p: None)
    cfg = make_cfg(tmp_path)
    base = tmp_path / "namd_runs"
    (base / "00000000_a").mkdir(parents=True)
    cfg.path_namd_runs=str(base)
    engine = NamdEngine(cfg, dry_run=True)
    name, run0_dir = engine.get_run0_fft_filename(0)
    assert name is None
    assert Path(run0_dir).name == "00000000_a"


# -------------------------------
# Tests for delete_namd_run_0_fft_file
# -------------------------------
import io
import sys
from engines.namd_engine import NamdEngine
import engines.namd_engine as ne  # for logger patch
from pathlib import Path

def _patch_logger(monkeypatch):
    class DummyLogger:
        def info(self, *args, **kwargs): pass
    monkeypatch.setattr(ne, "logger", DummyLogger())

def test_delete_run0_fft_box0(tmp_path, monkeypatch):
    cfg = make_cfg(tmp_path)
    eng = NamdEngine(cfg, dry_run=True)

    run0_dir = tmp_path / "NAMD" / "00000000_a"
    run0_dir.mkdir(parents=True, exist_ok=True)
    fft_name = "FFTW_NAMD_plan_A"
    (run0_dir / fft_name).write_text("x")

    # Patch the INSTANCE method
    monkeypatch.setattr(
        NamdEngine,
        "get_run0_fft_filename",
        lambda self, box_number: (fft_name, str(run0_dir))
    )
    _patch_logger(monkeypatch)

    cap = io.StringIO()
    old = sys.stdout
    sys.stdout = cap
    try:
        eng.delete_namd_run_0_fft_file(0)
    finally:
        sys.stdout = old

    assert not (run0_dir / fft_name).exists()
    assert "The NAMD FFT file was deleted from Run 0 in Box 0" in cap.getvalue()


def test_delete_run0_fft_box1(tmp_path, monkeypatch):
    cfg = make_cfg(tmp_path)
    eng = NamdEngine(cfg, dry_run=True)

    run0_dir = tmp_path / "NAMD" / "00000000_b"
    run0_dir.mkdir(parents=True, exist_ok=True)
    fft_name = "FFTW_NAMD_plan_B"
    (run0_dir / fft_name).write_text("y")

    monkeypatch.setattr(
        NamdEngine,
        "get_run0_fft_filename",
        lambda self, box_number: (fft_name, str(run0_dir))
    )
    _patch_logger(monkeypatch)

    cap = io.StringIO()
    old = sys.stdout
    sys.stdout = cap
    try:
        eng.delete_namd_run_0_fft_file(1)
    finally:
        sys.stdout = old

    assert not (run0_dir / fft_name).exists()
    assert "The NAMD FFT file was deleted from Run 0 in Box 1" in cap.getvalue()


def test_delete_run0_fft_missing_file_ok(tmp_path, monkeypatch):
    cfg = make_cfg(tmp_path)
    eng = NamdEngine(cfg, dry_run=True)

    run0_dir = tmp_path / "NAMD" / "00000000_a"
    run0_dir.mkdir(parents=True, exist_ok=True)
    fft_name = "FFTW_NAMD_nonexistent"  # won't be created

    monkeypatch.setattr(
        NamdEngine,
        "get_run0_fft_filename",
        lambda self, box_number: (fft_name, str(run0_dir))
    )
    _patch_logger(monkeypatch)

    cap = io.StringIO()
    old = sys.stdout
    sys.stdout = cap
    try:
        eng.delete_namd_run_0_fft_file(0)  # should not raise
    finally:
        sys.stdout = old

    assert "The NAMD FFT file was deleted from Run 0 in Box 0" in cap.getvalue()
    assert not (run0_dir / fft_name).exists()


def test_delete_run0_fft_missing_dir_ok(tmp_path, monkeypatch):
    cfg = make_cfg(tmp_path)
    eng = NamdEngine(cfg, dry_run=True)

    run0_dir = tmp_path / "NAMD" / "00000000_b"  # do NOT create it
    fft_name = "FFTW_NAMD_plan_B"

    monkeypatch.setattr(
        NamdEngine,
        "get_run0_fft_filename",
        lambda self, box_number: (fft_name, str(run0_dir))
    )
    _patch_logger(monkeypatch)

    cap = io.StringIO()
    old = sys.stdout
    sys.stdout = cap
    try:
        eng.delete_namd_run_0_fft_file(1)  # should not raise
    finally:
        sys.stdout = old

    assert "The NAMD FFT file was deleted from Run 0 in Box 1" in cap.getvalue()
    assert not run0_dir.exists()


def test_delete_run0_fft_invalid_box_raises(tmp_path):
    cfg = make_cfg(tmp_path)
    eng = NamdEngine(cfg, dry_run=True)
    with pytest.raises(ValueError) as ei:
        eng.delete_namd_run_0_fft_file(2)
    assert "ERROR Enter an interger of 0 or 1" in str(ei.value)

def test_cache_run0_fft_file_copies_fft_into_managed_cache(tmp_path: Path):
    cfg = make_cfg(tmp_path)
    eng = NamdEngine(cfg, dry_run=True)

    runtime_root = tmp_path / "managed_runtime" / "NAMD"
    run0_dir = runtime_root / "0000000000_a"
    run0_dir.mkdir(parents=True, exist_ok=True)

    fft_name = "FFTW_NAMD_plan.txt"
    src = run0_dir / fft_name
    src.write_text("fft")

    managed_root = tmp_path / "managed_runtime"
    cached = eng.cache_run0_fft_file(
        0,
        run_root=runtime_root,
        managed_root=managed_root,
    )

    assert cached == managed_root / "_engine_cache" / "NAMD" / "run0_fft_box0" / fft_name
    assert cached.exists()
    assert cached.read_text() == "fft"


def test_get_cached_run0_fft_filename_returns_cached_entry(tmp_path: Path):
    cfg = make_cfg(tmp_path)
    eng = NamdEngine(cfg, dry_run=True)

    managed_root = tmp_path / "managed_runtime"
    cache_dir = managed_root / "_engine_cache" / "NAMD" / "run0_fft_box0"
    cache_dir.mkdir(parents=True, exist_ok=True)

    fft_name = "FFTW_NAMD_plan.txt"
    (cache_dir / fft_name).write_text("fft")

    name, dir_str = eng.get_cached_run0_fft_filename(0, managed_root=managed_root)

    assert name == fft_name
    assert Path(dir_str) == cache_dir
