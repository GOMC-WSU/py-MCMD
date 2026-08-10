import os
import stat
import sys
from pathlib import Path

import pytest

sys.path.insert(0, "/home/arsalan/wsu-gomc/py-MCMD-hm/py_mcmd_refactored")

from utils.fifo_store import (
    FifoStore,
    ManagedArtifactStore,
    _discover_managed_root,
)

pytestmark = pytest.mark.skipif(
    not hasattr(os, "mkfifo"),
    reason="FIFO tests require os.mkfifo support",
)


def make_store(tmp_path: Path, **kwargs) -> FifoStore:
    base = dict(
        root_dir=tmp_path / "fifo_store",
        output_basenames_by_engine={
            "NAMD": ["namdOut.restart.coor", "out.dat"],
            "GOMC": ["Output_data_BOX_0_restart.coor", "out.dat"],
        },
    )
    base.update(kwargs)
    return FifoStore(**base)


def test_prepare_step_creates_fifo_endpoints(tmp_path: Path):
    store = make_store(tmp_path)

    resources = store.prepare_step("NAMD", 0)

    assert resources.engine == "NAMD"
    assert resources.step_id == "0"
    assert resources.status == "prepared"
    assert sorted(resources.endpoints) == ["namdOut.restart.coor", "out.dat"]

    coor_path = resources.endpoints["namdOut.restart.coor"].fifo_path
    out_path = resources.endpoints["out.dat"].fifo_path

    assert coor_path.exists()
    assert out_path.exists()
    assert stat.S_ISFIFO(coor_path.stat().st_mode)
    assert stat.S_ISFIFO(out_path.stat().st_mode)


def test_get_fifo_path_exposes_prior_step_resource_for_consumer(tmp_path: Path):
    store = make_store(tmp_path)
    store.prepare_step("GOMC", 1)

    fifo_path = store.get_fifo_path("GOMC", 1, "Output_data_BOX_0_restart.coor")

    assert fifo_path.name == "Output_data_BOX_0_restart.coor"
    assert fifo_path.exists()
    assert stat.S_ISFIFO(fifo_path.stat().st_mode)


def test_finalize_step_success_marks_step_without_cleaning_it(tmp_path: Path):
    store = make_store(tmp_path)
    resources = store.prepare_step("NAMD", 2)

    fifo_path = resources.endpoints["out.dat"].fifo_path
    assert fifo_path.exists()

    store.finalize_step_success("NAMD", 2)

    saved = store.get_step("NAMD", 2)
    assert saved.status == "success"
    assert fifo_path.exists()
    assert stat.S_ISFIFO(fifo_path.stat().st_mode)


def test_finalize_step_failure_cleans_up_step_resources(tmp_path: Path):
    store = make_store(tmp_path)
    resources = store.prepare_step("GOMC", 3)

    fifo_path = resources.endpoints["out.dat"].fifo_path
    assert fifo_path.exists()

    store.finalize_step_failure("GOMC", 3)

    assert not fifo_path.exists()
    with pytest.raises(KeyError):
        store.get_step("GOMC", 3)


def test_cleanup_step_removes_fifo_resources_after_success(tmp_path: Path):
    store = make_store(tmp_path)
    resources = store.prepare_step("NAMD", 4)
    store.finalize_step_success("NAMD", 4)

    fifo_path = resources.endpoints["namdOut.restart.coor"].fifo_path
    assert fifo_path.exists()

    store.cleanup_step("NAMD", 4)

    assert not fifo_path.exists()
    with pytest.raises(KeyError):
        store.get_step("NAMD", 4)


def test_cleanup_all_removes_every_registered_step(tmp_path: Path):
    store = make_store(tmp_path)
    s0 = store.prepare_step("NAMD", 0)
    s1 = store.prepare_step("GOMC", 1)

    assert s0.endpoints["out.dat"].fifo_path.exists()
    assert s1.endpoints["out.dat"].fifo_path.exists()

    store.cleanup_all()

    assert not s0.endpoints["out.dat"].fifo_path.exists()
    assert not s1.endpoints["out.dat"].fifo_path.exists()

    with pytest.raises(KeyError):
        store.get_step("NAMD", 0)
    with pytest.raises(KeyError):
        store.get_step("GOMC", 1)


def test_prepare_step_rejects_duplicate_engine_step_registration(
    tmp_path: Path,
):
    store = make_store(tmp_path)
    store.prepare_step("NAMD", 5)

    with pytest.raises(ValueError, match="already prepared"):
        store.prepare_step("NAMD", 5)


def test_unknown_engine_is_rejected(tmp_path: Path):
    store = make_store(tmp_path)

    with pytest.raises(ValueError, match="Unsupported engine"):
        store.prepare_step("LAMMPS", 0)


def test_developer_mode_records_dual_write_paths_via_hook(tmp_path: Path):
    def dual_write_factory(engine: str, step_id: str, basename: str) -> Path:
        return tmp_path / "mirror" / engine / step_id / basename

    store = make_store(
        tmp_path,
        developer_mode=True,
        dual_write_path_factory=dual_write_factory,
    )

    resources = store.prepare_step("GOMC", 7)
    endpoint = resources.endpoints["out.dat"]

    assert (
        endpoint.dual_write_path
        == tmp_path / "mirror" / "GOMC" / "7" / "out.dat"
    )
    assert endpoint.dual_write_path.parent.exists()


def test_managed_artifact_store_cleanup_all_removes_engine_cache(
    tmp_path: Path,
):
    store = ManagedArtifactStore(
        disk_roots={"NAMD": tmp_path / "NAMD", "GOMC": tmp_path / "GOMC"},
        managed_root=tmp_path / "managed",
    )

    cache_dir = store.cache_dir("NAMD")
    cache_file = cache_dir / "run0_fft_box0" / "FFTW_NAMD_plan.txt"
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text("fft")

    assert cache_file.exists()

    store.cleanup_all()

    assert not cache_file.exists()


def test_managed_artifact_store_prepare_step_creates_expected_runtime_dirs(
    tmp_path: Path,
):
    store = ManagedArtifactStore(
        disk_roots={"NAMD": tmp_path / "NAMD", "GOMC": tmp_path / "GOMC"},
        managed_root=tmp_path / "managed",
    )

    namd = store.prepare_step("NAMD", "0000000000")
    gomc = store.prepare_step("GOMC", "0000000001")

    assert namd.runtime_dir(0).is_dir()
    assert namd.runtime_dir(1).is_dir()
    assert gomc.runtime_dir().is_dir()
    assert namd.disk_dir(0) == tmp_path / "NAMD" / "0000000000_a"
    assert namd.disk_dir(1) == tmp_path / "NAMD" / "0000000000_b"
    assert gomc.disk_dir() == tmp_path / "GOMC" / "0000000001"


def test_managed_artifact_store_default_mode_does_not_mirror_runtime_outputs_to_disk(
    tmp_path: Path,
):
    store = ManagedArtifactStore(
        disk_roots={"NAMD": tmp_path / "NAMD", "GOMC": tmp_path / "GOMC"},
        managed_root=tmp_path / "managed",
        developer_mode=False,
    )

    step = store.prepare_step("NAMD", "0000000000")
    runtime_box0 = step.runtime_dir(0)
    runtime_box1 = step.runtime_dir(1)

    (runtime_box0 / "out.dat").write_text("stdout box0\n", encoding="utf-8")
    (runtime_box0 / "namdOut.restart.coor").write_text(
        "coor box0\n", encoding="utf-8"
    )
    (runtime_box1 / "out.dat").write_text("stdout box1\n", encoding="utf-8")

    store.finalize_step_success("NAMD", "0000000000")

    assert (runtime_box0 / "out.dat").exists()
    assert (runtime_box0 / "namdOut.restart.coor").exists()
    assert (runtime_box1 / "out.dat").exists()

    assert not (step.disk_dir(0) / "out.dat").exists()
    assert not (step.disk_dir(0) / "namdOut.restart.coor").exists()
    assert not (step.disk_dir(1) / "out.dat").exists()


def test_managed_artifact_store_developer_mode_mirrors_namd_outputs_to_disk(
    tmp_path: Path,
):
    store = ManagedArtifactStore(
        disk_roots={"NAMD": tmp_path / "NAMD", "GOMC": tmp_path / "GOMC"},
        managed_root=tmp_path / "managed",
        developer_mode=True,
    )

    step = store.prepare_step("NAMD", "0000000002")
    (step.runtime_dir(0) / "out.dat").write_text("stdout0\n", encoding="utf-8")
    (step.runtime_dir(0) / "namdOut.restart.coor").write_text(
        "coor0\n", encoding="utf-8"
    )
    (step.runtime_dir(1) / "out.dat").write_text("stdout1\n", encoding="utf-8")

    store.finalize_step_success("NAMD", "0000000002")

    assert (step.disk_dir(0) / "out.dat").read_text(
        encoding="utf-8"
    ) == "stdout0\n"
    assert (step.disk_dir(0) / "namdOut.restart.coor").read_text(
        encoding="utf-8"
    ) == "coor0\n"
    assert (step.disk_dir(1) / "out.dat").read_text(
        encoding="utf-8"
    ) == "stdout1\n"


def test_managed_artifact_store_developer_mode_mirrors_gomc_outputs_to_disk(
    tmp_path: Path,
):
    store = ManagedArtifactStore(
        disk_roots={"NAMD": tmp_path / "NAMD", "GOMC": tmp_path / "GOMC"},
        managed_root=tmp_path / "managed",
        developer_mode=True,
    )

    step = store.prepare_step("GOMC", "0000000001")
    (step.runtime_dir() / "out.dat").write_text(
        "gomc stdout\n", encoding="utf-8"
    )
    (step.runtime_dir() / "Output_data_BOX_0_restart.coor").write_text(
        "gomc coor\n", encoding="utf-8"
    )

    store.finalize_step_success("GOMC", "0000000001")

    assert (step.disk_dir() / "out.dat").read_text(
        encoding="utf-8"
    ) == "gomc stdout\n"
    assert (step.disk_dir() / "Output_data_BOX_0_restart.coor").read_text(
        encoding="utf-8"
    ) == "gomc coor\n"


# def test_managed_artifact_store_failure_cleans_runtime_dirs_without_disk_mirror_in_default_mode(tmp_path: Path):
#     store = ManagedArtifactStore(
#         disk_roots={"NAMD": tmp_path / "NAMD", "GOMC": tmp_path / "GOMC"},
#         managed_root=tmp_path / "managed",
#         developer_mode=False,
#     )

#     step = store.prepare_step("GOMC", "0000000003")
#     runtime_dir = step.runtime_dir()
#     disk_dir = step.disk_dir()

#     (runtime_dir / "out.dat").write_text("stdout\n", encoding="utf-8")
#     (runtime_dir / "Output_data_BOX_0_restart.coor").write_text("coor\n", encoding="utf-8")

#     store.finalize_step_failure("GOMC", "0000000003")

#     assert not runtime_dir.exists()
#     assert not disk_dir.exists()
#     with pytest.raises(KeyError):
#         store.get_step("GOMC", "0000000003")


def test_managed_artifact_store_failure_preserves_runtime_dirs_for_debugging(
    tmp_path: Path,
):
    store = ManagedArtifactStore(
        disk_roots={"NAMD": tmp_path / "NAMD", "GOMC": tmp_path / "GOMC"},
        managed_root=tmp_path / "managed",
        developer_mode=False,
    )

    step = store.prepare_step("GOMC", "0000000003")
    runtime_dir = step.runtime_dir()
    disk_dir = step.disk_dir()

    (runtime_dir / "out.dat").write_text("stdout\n", encoding="utf-8")
    (runtime_dir / "Output_data_BOX_0_restart.coor").write_text(
        "coor\n",
        encoding="utf-8",
    )

    store.finalize_step_failure("GOMC", "0000000003")

    assert runtime_dir.exists()
    assert (runtime_dir / "out.dat").exists()
    assert (runtime_dir / "Output_data_BOX_0_restart.coor").exists()
    assert not disk_dir.exists()
    assert store.get_step("GOMC", "0000000003").status == "failed"


def test_discover_managed_root_prefers_explicit_root_over_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    explicit_root = tmp_path / "explicit"
    monkeypatch.setenv(
        "PY_MCMD_MANAGED_OUTPUT_ROOT",
        str(tmp_path / "environment"),
    )

    assert _discover_managed_root(explicit_root) == explicit_root


def test_discover_managed_root_uses_environment_override(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    environment_root = tmp_path / "environment"
    monkeypatch.setenv(
        "PY_MCMD_MANAGED_OUTPUT_ROOT",
        str(environment_root),
    )

    assert _discover_managed_root() == environment_root


def test_discover_managed_root_is_unique_per_working_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    simulation_a = tmp_path / "simulation_a"
    simulation_b = tmp_path / "simulation_b"
    simulation_a.mkdir()
    simulation_b.mkdir()
    monkeypatch.delenv("PY_MCMD_MANAGED_OUTPUT_ROOT", raising=False)

    monkeypatch.chdir(simulation_a)
    root_a = _discover_managed_root()

    monkeypatch.chdir(simulation_b)
    root_b = _discover_managed_root()

    assert root_a != root_b

    if root_a.parent == Path("/dev/shm"):
        assert root_a.name.startswith("py_mcmd_")
        assert root_b.name.startswith("py_mcmd_")


def test_managed_artifact_store_release_step_removes_runtime_resources(
    tmp_path: Path,
):
    store = ManagedArtifactStore(
        disk_roots={"NAMD": tmp_path / "NAMD", "GOMC": tmp_path / "GOMC"},
        managed_root=tmp_path / "managed",
    )

    step = store.prepare_step("NAMD", "0000000004")
    runtime_box0 = step.runtime_dir(0)
    runtime_box1 = step.runtime_dir(1)

    (runtime_box0 / "out.dat").write_text(
        "stdout\n",
        encoding="utf-8",
    )

    store.release_step("NAMD", "0000000004")

    assert not runtime_box0.exists()
    assert not runtime_box1.exists()

    with pytest.raises(KeyError):
        store.get_step("NAMD", "0000000004")


def test_legacy_fifo_store_release_step_matches_cleanup_behavior(
    tmp_path: Path,
):
    store = make_store(tmp_path)
    resources = store.prepare_step("GOMC", 8)
    fifo_path = resources.endpoints["out.dat"].fifo_path

    assert fifo_path.exists()

    store.release_step("GOMC", 8)

    assert not fifo_path.exists()

    with pytest.raises(KeyError):
        store.get_step("GOMC", 8)
