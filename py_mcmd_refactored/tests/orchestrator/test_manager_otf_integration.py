from __future__ import annotations

import threading
from pathlib import Path
from types import SimpleNamespace

import orchestrator.manager as mgr
import pytest
from config.models import SimulationConfig


def _cfg(
    tmp_path: Path,
    **overrides,
) -> SimulationConfig:
    base = dict(
        total_cycles_namd_gomc_sims=2,
        starting_at_cycle_namd_gomc_sims=0,
        gomc_use_CPU_or_GPU="CPU",
        simulation_type="NPT",
        only_use_box_0_for_namd_for_gemc=True,
        no_core_box_0=1,
        no_core_box_1=0,
        simulation_temp_k=250.0,
        simulation_pressure_bar=1.0,
        GCMC_ChemPot_or_Fugacity="ChemPot",
        GCMC_ChemPot_or_Fugacity_dict={"WAT": -2000},
        namd_minimize_mult_scalar=1,
        namd_run_steps=10,
        gomc_run_steps=5,
        namd_minimize_steps=10,
        set_dims_box_0_list=[
            25.0,
            25.0,
            25.0,
        ],
        set_dims_box_1_list=[
            25.0,
            25.0,
            25.0,
        ],
        set_angle_box_0_list=[
            90,
            90,
            90,
        ],
        set_angle_box_1_list=[
            90,
            90,
            90,
        ],
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
        log_dir=str(tmp_path / "logs"),
        developer_mode=False,
        process_on_the_fly=False,
        combined_data_dir=str(tmp_path / "combined_data"),
        disk_cleanup_mode="compact",
        otf_keep_raw_cycles=1,
    )

    base.update(overrides)

    return SimulationConfig(**base)


class FakeFifoStore:
    timeline: list[tuple] | None = None

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        self.calls = []

        disk_roots = kwargs.get(
            "disk_roots",
            {},
        )

        namd_root = Path(
            disk_roots.get(
                "NAMD",
                "/tmp/NAMD",
            )
        )

        self.managed_root = namd_root.parent / "managed_runtime"

    def _record(
        self,
        *call,
    ):
        self.calls.append(call)

        if self.timeline is not None:
            self.timeline.append(call)

    def prepare_step(
        self,
        engine,
        step_id,
    ):
        self._record(
            "prepare",
            engine,
            step_id,
        )

        endpoints = {
            "box0.out.dat": SimpleNamespace(
                fifo_path=Path("/tmp/box0.out.dat")
            ),
            "box1.out.dat": SimpleNamespace(
                fifo_path=Path("/tmp/box1.out.dat")
            ),
            "out.dat": SimpleNamespace(fifo_path=Path("/tmp/out.dat")),
        }

        return SimpleNamespace(
            engine=engine,
            step_id=step_id,
            endpoints=endpoints,
        )

    def finalize_step_success(
        self,
        engine,
        step_id,
    ):
        self._record(
            "success",
            engine,
            step_id,
        )

    def finalize_step_failure(
        self,
        engine,
        step_id,
    ):
        self._record(
            "failure",
            engine,
            step_id,
        )

    def release_step(
        self,
        engine,
        step_id,
    ):
        self._record(
            "release",
            engine,
            step_id,
        )

    def cleanup_cache_dir(
        self,
        engine,
    ):
        self._record(
            "cleanup_cache",
            engine,
        )

    def cleanup_all(self):
        self._record(
            "cleanup_all",
        )


def _patch_successful_engines(
    orch,
    monkeypatch,
):
    monkeypatch.setattr(
        orch.namd,
        "run_segment",
        lambda *, run_no, state, fifo_resources=None: {"run_no": run_no},
        raising=True,
    )

    monkeypatch.setattr(
        orch.gomc,
        "run_segment",
        lambda *, run_no, state, fifo_resources=None: {"run_no": run_no},
        raising=True,
    )


def test_otf_processor_is_not_created_when_processing_is_disabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        mgr,
        "FifoStore",
        FakeFifoStore,
    )

    def fail_if_constructed(
        *args,
        **kwargs,
    ):
        raise AssertionError("OnTheFlyProcessor should not be constructed")

    monkeypatch.setattr(
        mgr,
        "OnTheFlyProcessor",
        fail_if_constructed,
    )

    orch = mgr.SimulationOrchestrator(
        _cfg(
            tmp_path,
            process_on_the_fly=False,
        ),
        dry_run=True,
    )

    _patch_successful_engines(
        orch,
        monkeypatch,
    )

    summary = orch.run()

    assert summary["cycles_completed"] == 2

    assert orch._otf_processor is None


"""
Verifies

GOMC 1 complete
    ↓
process_cycle(0, 1)

GOMC 3 complete
    ↓
process_cycle(2, 3)

and

all workers complete
    ↓
processor.close()

"""


def test_otf_processor_processes_each_cycle_pair_and_closes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        mgr,
        "FifoStore",
        FakeFifoStore,
    )

    created = []

    class RecordingProcessor:
        def __init__(
            self,
            cfg,
            combined_data_dir,
            *,
            managed_root=None,
        ):
            self.combined_data_dir = combined_data_dir
            self.managed_root = managed_root
            self.processed = []
            self.seeded_steps = []
            self.closed = False

            created.append(self)

        def set_current_step(
            self,
            current_step,
        ):
            self.seeded_steps.append(int(current_step))

        def process_cycle(
            self,
            namd_run_no,
            gomc_run_no,
        ):
            self.processed.append(
                (
                    namd_run_no,
                    gomc_run_no,
                )
            )

        def close(self):
            self.closed = True

    monkeypatch.setattr(
        mgr,
        "OnTheFlyProcessor",
        RecordingProcessor,
    )

    cfg = _cfg(
        tmp_path,
        process_on_the_fly=True,
        disk_cleanup_mode="off",
    )

    orch = mgr.SimulationOrchestrator(
        cfg,
        dry_run=True,
    )

    _patch_successful_engines(
        orch,
        monkeypatch,
    )

    orch.run()

    assert len(created) == 1

    processor = created[0]

    assert processor.processed == [
        (
            0,
            1,
        ),
        (
            2,
            3,
        ),
    ]

    assert processor.closed is True

    assert processor.combined_data_dir == cfg.combined_data_dir

    assert processor.managed_root == orch.fifo_store.managed_root


def test_otf_worker_overlaps_next_cycle_and_release_waits_for_consumption(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    timeline = []

    FakeFifoStore.timeline = timeline

    monkeypatch.setattr(
        mgr,
        "FifoStore",
        FakeFifoStore,
    )

    first_started = threading.Event()
    allow_first_finish = threading.Event()

    class BlockingProcessor:
        def __init__(
            self,
            *args,
            **kwargs,
        ):
            pass

        def set_current_step(
            self,
            current_step,
        ):
            pass

        def process_cycle(
            self,
            namd_run_no,
            gomc_run_no,
        ):
            timeline.append(
                (
                    "otf_start",
                    namd_run_no,
                    gomc_run_no,
                )
            )

            if (
                namd_run_no,
                gomc_run_no,
            ) == (
                0,
                1,
            ):
                first_started.set()

                assert allow_first_finish.wait(timeout=2.0)

            timeline.append(
                (
                    "otf_finish",
                    namd_run_no,
                    gomc_run_no,
                )
            )

        def close(self):
            timeline.append(("otf_close",))

    monkeypatch.setattr(
        mgr,
        "OnTheFlyProcessor",
        BlockingProcessor,
    )

    cfg = _cfg(
        tmp_path,
        process_on_the_fly=True,
        disk_cleanup_mode="minimal",
        otf_keep_raw_cycles=1,
    )

    orch = mgr.SimulationOrchestrator(
        cfg,
        dry_run=True,
    )

    def namd_run(
        *,
        run_no,
        state,
        fifo_resources=None,
    ):
        timeline.append(
            (
                "engine",
                "NAMD",
                run_no,
            )
        )

        if run_no == 2:
            assert first_started.wait(timeout=2.0)

            assert not any(
                call[:3]
                == (
                    "release",
                    "NAMD",
                    "0000000000",
                )
                for call in timeline
            )

            allow_first_finish.set()

        return {"run_no": run_no}

    def gomc_run(
        *,
        run_no,
        state,
        fifo_resources=None,
    ):
        timeline.append(
            (
                "engine",
                "GOMC",
                run_no,
            )
        )

        return {"run_no": run_no}

    monkeypatch.setattr(
        orch.namd,
        "run_segment",
        namd_run,
        raising=True,
    )

    monkeypatch.setattr(
        orch.gomc,
        "run_segment",
        gomc_run,
        raising=True,
    )

    try:
        orch.run()

    finally:
        FakeFifoStore.timeline = None

    assert timeline.index(
        (
            "engine",
            "NAMD",
            2,
        )
    ) < timeline.index(
        (
            "otf_finish",
            0,
            1,
        )
    )

    release_index = timeline.index(
        (
            "release",
            "NAMD",
            "0000000000",
        )
    )

    assert release_index > timeline.index(
        (
            "otf_finish",
            0,
            1,
        )
    )

    assert release_index > timeline.index(
        (
            "otf_finish",
            2,
            3,
        )
    )

    assert (
        "release",
        "GOMC",
        "0000000001",
    ) in timeline


"""
engine simulation succeeds
        ↓
OTF thread fails
        ↓
_wait_for_otf_worker()
        ↓
raise original RuntimeError
        ↓
run_succeeded stays False
        ↓
no cleanup_all()

"""


def test_background_otf_failure_is_propagated_and_skips_success_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        mgr,
        "FifoStore",
        FakeFifoStore,
    )

    created = []

    class FailingProcessor:
        def __init__(
            self,
            *args,
            **kwargs,
        ):
            self.closed = False

            created.append(self)

        def set_current_step(
            self,
            current_step,
        ):
            pass

        def process_cycle(
            self,
            namd_run_no,
            gomc_run_no,
        ):
            raise RuntimeError("otf failed")

        def close(self):
            self.closed = True

    monkeypatch.setattr(
        mgr,
        "OnTheFlyProcessor",
        FailingProcessor,
    )

    cfg = _cfg(
        tmp_path,
        total_cycles_namd_gomc_sims=1,
        process_on_the_fly=True,
        disk_cleanup_mode="compact",
    )

    orch = mgr.SimulationOrchestrator(
        cfg,
        dry_run=True,
    )

    _patch_successful_engines(
        orch,
        monkeypatch,
    )

    with pytest.raises(
        RuntimeError,
        match="otf failed",
    ):
        orch.run()

    assert created[0].closed is True

    assert (
        "success",
        "NAMD",
        "0000000000",
    ) in orch.fifo_store.calls

    assert (
        "success",
        "GOMC",
        "0000000001",
    ) in orch.fifo_store.calls

    assert ("cleanup_all",) not in orch.fifo_store.calls

    assert not any(call[0] == "release" for call in orch.fifo_store.calls)


def test_restart_current_step_is_seeded_into_otf_processor_before_processing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        mgr,
        "FifoStore",
        FakeFifoStore,
    )

    events = []

    class RecordingProcessor:
        def __init__(
            self,
            *args,
            **kwargs,
        ):
            pass

        def set_current_step(
            self,
            current_step,
        ):
            events.append(
                (
                    "seed",
                    int(current_step),
                )
            )

        def process_cycle(
            self,
            namd_run_no,
            gomc_run_no,
        ):
            events.append(
                (
                    "process",
                    namd_run_no,
                    gomc_run_no,
                )
            )

        def close(self):
            events.append(("close",))

    monkeypatch.setattr(
        mgr,
        "OnTheFlyProcessor",
        RecordingProcessor,
    )

    cfg = _cfg(
        tmp_path,
        total_cycles_namd_gomc_sims=2,
        starting_at_cycle_namd_gomc_sims=1,
        process_on_the_fly=True,
        disk_cleanup_mode="off",
    )

    orch = mgr.SimulationOrchestrator(
        cfg,
        dry_run=True,
    )

    monkeypatch.setattr(
        orch,
        "refresh_pme_dims_from_run0",
        lambda: None,
        raising=True,
    )

    _patch_successful_engines(
        orch,
        monkeypatch,
    )

    orch.run()

    expected_restart_step = (
        cfg.namd_run_steps + cfg.gomc_run_steps
    ) * cfg.starting_at_cycle_namd_gomc_sims + cfg.namd_minimize_steps

    assert events[0] == (
        "seed",
        expected_restart_step,
    )

    assert (
        "process",
        2,
        3,
    ) in events

    assert events.index(
        (
            "seed",
            expected_restart_step,
        )
    ) < events.index(
        (
            "process",
            2,
            3,
        )
    )
