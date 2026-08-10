from pathlib import Path
from types import SimpleNamespace

import pytest
import utils.onthefly_processor as otf_mod
from utils.onthefly_processor import (
    AMU_PER_ANGSTROM3_TO_G_PER_CM3,
    K_TO_KCAL_MOL,
    OnTheFlyProcessor,
    _append_dcd,
    _parse_gomc_log,
    _parse_namd_log,
)


def _cfg(
    tmp_path: Path,
    simulation_type: str = "NVT",
) -> SimpleNamespace:
    return SimpleNamespace(
        path_namd_runs=str(tmp_path / "NAMD"),
        path_gomc_runs=str(tmp_path / "GOMC"),
        simulation_type=simulation_type,
    )


def _write_log(
    path: Path,
    text: str,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    path.write_text(
        text,
        encoding="utf-8",
    )


def _namd_log(
    *,
    steps: tuple[int, ...] = (0, 5),
    mass: float = 100.0,
) -> str:
    lines = [
        f"Info: TOTAL MASS = {mass}\n",
        ("ETITLE: TS POTENTIAL ELECT " "PRESSURE VOLUME\n"),
    ]

    for step in steps:
        lines.append((f"ENERGY: {step} " "-10.0 -2.0 1.0 1000.0\n"))

    return "".join(lines)


def _gomc_log(
    *,
    box_no: int = 0,
    steps: tuple[int, ...] = (0,),
) -> str:
    lines = [
        "ETITLE: STEP TOTAL TOTAL_ELECT\n",
        ("STITLE: STEP PRESSURE " "VOLUME TOT_DENSITY\n"),
    ]

    for step in steps:
        lines.extend(
            [
                (f"ENER_{box_no}: " f"{step} 1000.0 500.0\n"),
                (f"STAT_{box_no}: " f"{step} 1.5 2000.0 900.0\n"),
            ]
        )

    return "".join(lines)


def test_parse_namd_log_normalizes_steps_and_calculates_density():
    (
        titles,
        density_titles,
        rows,
        last_ts,
    ) = _parse_namd_log(
        _namd_log().splitlines(keepends=True),
        current_step=100,
    )

    assert titles == [
        "ETITLE:",
        "TS",
        "POTENTIAL",
        "ELECT",
        "PRESSURE",
        "VOLUME",
    ]
    assert density_titles == [
        "TS",
        "POTENTIAL",
        "ELECT",
        "PRESSURE",
        "VOLUME",
        "DENSITY",
    ]

    assert [row[1] for row, _ in rows] == [
        "100",
        "105",
    ]

    assert last_ts == 105

    expected_density = AMU_PER_ANGSTROM3_TO_G_PER_CM3 * 100.0 / 1000.0 * 1000.0

    assert rows[0][1] == pytest.approx(expected_density)
    assert rows[1][1] == pytest.approx(expected_density)


@pytest.mark.parametrize(
    "box_no",
    [0, 1],
)
def test_parse_gomc_log_merges_rows_offsets_steps_and_converts_units(
    box_no: int,
):
    (
        titles,
        merged_titles,
        kcal_titles,
        merged_rows,
        kcal_rows,
        raw_lines,
        last_step,
    ) = _parse_gomc_log(
        _gomc_log(
            box_no=box_no,
            steps=(0, 5),
        ).splitlines(keepends=True),
        box_no=box_no,
        current_step=10,
    )

    assert titles == [
        "ETITLE:",
        "STEP",
        "TOTAL",
        "TOTAL_ELECT",
    ]

    assert merged_titles == [
        "#STEP",
        "TOTAL",
        "TOTAL_ELECT",
        "PRESSURE",
        "VOLUME",
        "TOT_DENSITY",
    ]

    assert kcal_titles == merged_titles

    assert [row[0] for row in merged_rows] == [
        "10",
        "15",
    ]

    assert [row[0] for row in kcal_rows] == [
        "10",
        "15",
    ]

    assert last_step == 15

    assert float(kcal_rows[0][1]) == pytest.approx(1000.0 * K_TO_KCAL_MOL)

    assert float(kcal_rows[0][2]) == pytest.approx(500.0 * K_TO_KCAL_MOL)

    assert float(kcal_rows[0][-1]) == pytest.approx(0.9)

    raw_energy_lines = [
        content for kind, content in raw_lines if kind == "ENER"
    ]

    raw_stat_lines = [content for kind, content in raw_lines if kind == "STAT"]

    assert "10" in raw_energy_lines[0]
    assert "15" in raw_energy_lines[1]
    assert "10" in raw_stat_lines[0]
    assert "15" in raw_stat_lines[1]


def test_resolve_log_path_prefers_runtime_then_falls_back_to_disk(
    tmp_path: Path,
):
    runtime_dir = tmp_path / "managed" / "NAMD" / "0000000000_a"

    disk_dir = tmp_path / "NAMD" / "0000000000_a"

    runtime_log = runtime_dir / "out.dat"
    disk_log = disk_dir / "out.dat"

    _write_log(
        disk_log,
        "disk\n",
    )
    _write_log(
        runtime_log,
        "runtime\n",
    )

    assert (
        OnTheFlyProcessor._resolve_log_path(
            runtime_dir,
            disk_dir,
        )
        == runtime_log
    )

    runtime_log.unlink()

    assert (
        OnTheFlyProcessor._resolve_log_path(
            runtime_dir,
            disk_dir,
        )
        == disk_log
    )

    disk_log.unlink()

    assert (
        OnTheFlyProcessor._resolve_log_path(
            runtime_dir,
            disk_dir,
        )
        is None
    )


def test_process_cycle_appends_rows_once_per_cycle_and_preserves_step_offsets(
    tmp_path: Path,
):
    managed_root = tmp_path / "managed"
    combined_dir = tmp_path / "combined"
    cfg = _cfg(tmp_path)

    _write_log(
        (managed_root / "NAMD" / "0000000000_a" / "out.dat"),
        _namd_log(
            steps=(0, 5),
        ),
    )

    _write_log(
        (managed_root / "GOMC" / "0000000001" / "out.dat"),
        _gomc_log(
            steps=(0,),
        ),
    )

    _write_log(
        (managed_root / "NAMD" / "0000000002_a" / "out.dat"),
        _namd_log(
            steps=(0, 5),
        ),
    )

    _write_log(
        (managed_root / "GOMC" / "0000000003" / "out.dat"),
        _gomc_log(
            steps=(0,),
        ),
    )

    processor = OnTheFlyProcessor(
        cfg,
        combined_dir,
        managed_root=managed_root,
    )

    try:
        processor.process_cycle(
            0,
            1,
        )
        processor.process_cycle(
            2,
            3,
        )

    finally:
        processor.close()

    namd_lines = (combined_dir / "NAMD_data_box_0.txt").read_text().splitlines()

    assert sum(line.startswith("ETITLE:") for line in namd_lines) == 1

    energy_lines = [line for line in namd_lines if line.startswith("ENERGY:")]

    assert [line.split()[1] for line in energy_lines] == [
        "0",
        "5",
        "5",
        "10",
    ]

    density_lines = (
        (combined_dir / "NAMD_data_density_box_0.txt").read_text().splitlines()
    )

    assert density_lines[0].endswith("DENSITY")

    assert len(density_lines) == 5

    gomc_stat_lines = (
        (combined_dir / "GOMC_Energies_Stat_box_0.txt").read_text().splitlines()
    )

    assert sum(line.startswith("#STEP") for line in gomc_stat_lines) == 1

    assert [line.split()[0] for line in gomc_stat_lines[1:]] == [
        "5",
        "10",
    ]

    combined_lines = (
        (combined_dir / "combined_NAMD_GOMC_data_box_0.txt")
        .read_text()
        .splitlines()
    )

    assert sum(line.startswith("#ENGINE") for line in combined_lines) == 1

    assert [line.split()[0] for line in combined_lines[1:]] == [
        "NAMD",
        "NAMD",
        "GOMC",
        "NAMD",
        "NAMD",
        "GOMC",
    ]

    assert [line.split()[1] for line in combined_lines[1:]] == [
        "0",
        "5",
        "5",
        "5",
        "10",
        "10",
    ]


def test_process_cycle_writes_kcal_and_density_converted_gomc_output(
    tmp_path: Path,
):
    managed_root = tmp_path / "managed"
    combined_dir = tmp_path / "combined"
    cfg = _cfg(tmp_path)

    _write_log(
        (managed_root / "NAMD" / "0000000000_a" / "out.dat"),
        _namd_log(
            steps=(0, 5),
        ),
    )

    _write_log(
        (managed_root / "GOMC" / "0000000001" / "out.dat"),
        _gomc_log(
            steps=(0,),
        ),
    )

    processor = OnTheFlyProcessor(
        cfg,
        combined_dir,
        managed_root=managed_root,
    )

    try:
        processor.process_cycle(
            0,
            1,
        )

    finally:
        processor.close()

    lines = (
        (combined_dir / ("GOMC_Energies_Stat_" "kcal_per_mol_box_0.txt"))
        .read_text()
        .splitlines()
    )

    assert lines[0].split() == [
        "#STEP",
        "TOTAL",
        "TOTAL_ELECT",
        "PRESSURE",
        "VOLUME",
        "TOT_DENSITY",
    ]

    values = lines[1].split()

    assert values[0] == "5"

    assert float(values[1]) == pytest.approx(1000.0 * K_TO_KCAL_MOL)

    assert float(values[2]) == pytest.approx(500.0 * K_TO_KCAL_MOL)

    assert float(values[-1]) == pytest.approx(0.9)


def test_process_cycle_handles_missing_logs_without_crashing(
    tmp_path: Path,
):
    processor = OnTheFlyProcessor(
        _cfg(tmp_path),
        tmp_path / "combined",
        managed_root=tmp_path / "managed",
    )

    try:
        processor.process_cycle(
            0,
            1,
        )

    finally:
        processor.close()

    combined = tmp_path / "combined" / "combined_NAMD_GOMC_data_box_0.txt"

    assert combined.read_text() == ""


def test_append_dcd_uses_temporary_output_and_replaces_destination_atomically(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    src = tmp_path / "segment.dcd"
    dst = tmp_path / "combined.dcd"
    src.write_text("segment-1", encoding="utf-8")

    calls: list[list[str]] = []

    def fake_run(command, **kwargs):
        calls.append(command)
        tmp_output = Path(command[2])
        input_paths = [Path(value) for value in command[3:]]
        tmp_output.write_text(
            "|".join(path.read_text(encoding="utf-8") for path in input_paths),
            encoding="utf-8",
        )
        return SimpleNamespace(
            returncode=0,
            stdout="",
            stderr="",
        )

    monkeypatch.setattr(
        otf_mod.subprocess,
        "run",
        fake_run,
    )

    assert (
        _append_dcd(
            "catdcd",
            src,
            dst,
        )
        is True
    )

    assert calls == [
        [
            "catdcd",
            "-o",
            str(tmp_path / "combined.dcd.tmp"),
            str(src),
        ]
    ]

    assert dst.read_text(encoding="utf-8") == "segment-1"

    assert not (tmp_path / "combined.dcd.tmp").exists()


def test_append_dcd_chains_existing_combined_trajectory_before_new_segment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    src = tmp_path / "segment-2.dcd"
    dst = tmp_path / "combined.dcd"

    src.write_text(
        "segment-2",
        encoding="utf-8",
    )
    dst.write_text(
        "segment-1",
        encoding="utf-8",
    )

    calls: list[list[str]] = []

    def fake_run(command, **kwargs):
        calls.append(command)
        tmp_output = Path(command[2])
        input_paths = [Path(value) for value in command[3:]]
        tmp_output.write_text(
            "|".join(path.read_text(encoding="utf-8") for path in input_paths),
            encoding="utf-8",
        )
        return SimpleNamespace(
            returncode=0,
            stdout="",
            stderr="",
        )

    monkeypatch.setattr(
        otf_mod.subprocess,
        "run",
        fake_run,
    )

    assert (
        _append_dcd(
            "catdcd",
            src,
            dst,
        )
        is True
    )

    assert calls == [
        [
            "catdcd",
            "-o",
            str(tmp_path / "combined.dcd.tmp"),
            str(dst),
            str(src),
        ]
    ]

    assert dst.read_text(encoding="utf-8") == "segment-1|segment-2"

    assert not (tmp_path / "combined.dcd.tmp").exists()


def test_append_dcd_failure_preserves_existing_combined_trajectory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    src = tmp_path / "segment-2.dcd"
    dst = tmp_path / "combined.dcd"

    src.write_text(
        "segment-2",
        encoding="utf-8",
    )
    dst.write_text(
        "stable-combined-data",
        encoding="utf-8",
    )

    def fake_run(command, **kwargs):
        Path(command[2]).write_text(
            "partial-output",
            encoding="utf-8",
        )
        return SimpleNamespace(
            returncode=1,
            stdout="",
            stderr="catdcd failed",
        )

    monkeypatch.setattr(
        otf_mod.subprocess,
        "run",
        fake_run,
    )

    assert (
        _append_dcd(
            "catdcd",
            src,
            dst,
        )
        is False
    )

    assert dst.read_text(encoding="utf-8") == "stable-combined-data"

    assert not (tmp_path / "combined.dcd.tmp").exists()


def test_process_cycle_skips_dcd_combination_when_flags_are_disabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    cfg = _cfg(tmp_path)
    cfg.combine_namd_dcd_file = False
    cfg.combine_gomc_dcd_file = False

    processor = OnTheFlyProcessor(
        cfg,
        tmp_path / "combined",
        managed_root=tmp_path / "managed",
    )

    dcd_calls: list[tuple[str, int]] = []

    monkeypatch.setattr(
        processor,
        "_append_namd_dcd",
        lambda run_no: dcd_calls.append(("NAMD", run_no)),
    )
    monkeypatch.setattr(
        processor,
        "_append_gomc_dcd",
        lambda run_no: dcd_calls.append(("GOMC", run_no)),
    )

    try:
        processor.process_cycle(
            0,
            1,
        )
    finally:
        processor.close()

    assert dcd_calls == []


def test_append_namd_dcd_prefers_runtime_artifact_over_disk_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    managed_root = tmp_path / "managed"

    processor = OnTheFlyProcessor(
        _cfg(tmp_path),
        tmp_path / "combined",
        managed_root=managed_root,
    )

    runtime_dcd = managed_root / "NAMD" / "0000000000_a" / "namdOut.dcd"
    disk_dcd = tmp_path / "NAMD" / "0000000000_a" / "namdOut.dcd"

    _write_log(
        runtime_dcd,
        "runtime-dcd",
    )
    _write_log(
        disk_dcd,
        "disk-dcd",
    )

    calls: list[tuple[Path, Path]] = []

    def fake_append_dcd(
        catdcd_bin,
        src_dcd,
        dst_dcd,
    ):
        calls.append(
            (
                Path(src_dcd),
                Path(dst_dcd),
            )
        )
        return True

    monkeypatch.setattr(
        otf_mod,
        "_append_dcd",
        fake_append_dcd,
    )

    try:
        assert processor._append_namd_dcd(0) is True
    finally:
        processor.close()

    assert calls == [
        (
            runtime_dcd,
            (tmp_path / "combined" / "combined_box_0_NAMD_dcd_files.dcd"),
        )
    ]


def test_append_gomc_dcd_prefers_runtime_artifacts_for_active_boxes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    managed_root = tmp_path / "managed"

    processor = OnTheFlyProcessor(
        _cfg(
            tmp_path,
            simulation_type="GCMC",
        ),
        tmp_path / "combined",
        managed_root=managed_root,
    )

    runtime_box0 = (
        managed_root / "GOMC" / "0000000001" / "Output_data_BOX_0.dcd"
    )
    runtime_box1 = (
        managed_root / "GOMC" / "0000000001" / "Output_data_BOX_1.dcd"
    )

    disk_box0 = tmp_path / "GOMC" / "0000000001" / "Output_data_BOX_0.dcd"
    disk_box1 = tmp_path / "GOMC" / "0000000001" / "Output_data_BOX_1.dcd"

    _write_log(
        runtime_box0,
        "runtime-box0",
    )
    _write_log(
        runtime_box1,
        "runtime-box1",
    )
    _write_log(
        disk_box0,
        "disk-box0",
    )
    _write_log(
        disk_box1,
        "disk-box1",
    )

    calls: list[tuple[Path, Path]] = []

    def fake_append_dcd(
        catdcd_bin,
        src_dcd,
        dst_dcd,
    ):
        calls.append(
            (
                Path(src_dcd),
                Path(dst_dcd),
            )
        )
        return True

    monkeypatch.setattr(
        otf_mod,
        "_append_dcd",
        fake_append_dcd,
    )

    try:
        results = processor._append_gomc_dcd(1)
    finally:
        processor.close()

    assert results == {
        0: True,
        1: True,
    }

    assert calls == [
        (
            runtime_box0,
            (tmp_path / "combined" / "combined_box_0_GOMC_dcd_files.dcd"),
        ),
        (
            runtime_box1,
            (tmp_path / "combined" / "combined_box_1_GOMC_dcd_files.dcd"),
        ),
    ]


def test_copy_merged_psf_prefers_runtime_source_and_copies_only_once(
    tmp_path: Path,
):
    managed_root = tmp_path / "managed"
    combined_dir = tmp_path / "combined"

    processor = OnTheFlyProcessor(
        _cfg(tmp_path),
        combined_dir,
        managed_root=managed_root,
    )

    runtime_psf = (
        managed_root / "GOMC" / "0000000001" / "Output_data_merged.psf"
    )
    disk_psf = tmp_path / "GOMC" / "0000000001" / "Output_data_merged.psf"

    _write_log(
        runtime_psf,
        "runtime-psf",
    )
    _write_log(
        disk_psf,
        "disk-psf",
    )

    try:
        assert processor._copy_merged_psf(1) is True

        destination = combined_dir / "Output_data_merged.psf"

        assert destination.read_text(encoding="utf-8") == "runtime-psf"

        runtime_psf.write_text(
            "changed-runtime-psf",
            encoding="utf-8",
        )

        assert processor._copy_merged_psf(1) is False

        assert destination.read_text(encoding="utf-8") == "runtime-psf"

    finally:
        processor.close()


def test_archive_cycle_logs_uses_unique_names_and_prefers_runtime_logs(
    tmp_path: Path,
):
    managed_root = tmp_path / "managed"
    combined_dir = tmp_path / "combined"

    processor = OnTheFlyProcessor(
        _cfg(tmp_path),
        combined_dir,
        managed_root=managed_root,
    )

    runtime_logs = {
        "NAMD_0000000000_a_out.dat": (
            (managed_root / "NAMD" / "0000000000_a" / "out.dat"),
            "runtime-namd-0",
        ),
        "GOMC_0000000001_out.dat": (
            (managed_root / "GOMC" / "0000000001" / "out.dat"),
            "runtime-gomc-1",
        ),
        "NAMD_0000000002_a_out.dat": (
            (managed_root / "NAMD" / "0000000002_a" / "out.dat"),
            "runtime-namd-2",
        ),
        "GOMC_0000000003_out.dat": (
            (managed_root / "GOMC" / "0000000003" / "out.dat"),
            "runtime-gomc-3",
        ),
    }

    for (
        archive_name,
        (
            runtime_path,
            runtime_text,
        ),
    ) in runtime_logs.items():
        _write_log(
            runtime_path,
            runtime_text,
        )

        parts = archive_name.split("_")

        if archive_name.startswith("NAMD"):
            disk_dir_name = "_".join(parts[1:3])
            disk_path = tmp_path / "NAMD" / disk_dir_name / "out.dat"

        else:
            disk_dir_name = parts[1]
            disk_path = tmp_path / "GOMC" / disk_dir_name / "out.dat"

        _write_log(
            disk_path,
            f"disk-{runtime_text}",
        )

    try:
        processor._archive_cycle_logs(
            0,
            1,
        )
        processor._archive_cycle_logs(
            2,
            3,
        )

        logs_dir = combined_dir / "cycle_logs"

        assert sorted(path.name for path in logs_dir.iterdir()) == sorted(
            runtime_logs
        )

        for (
            archive_name,
            (
                _,
                runtime_text,
            ),
        ) in runtime_logs.items():
            assert (logs_dir / archive_name).read_text(
                encoding="utf-8"
            ) == runtime_text

        first_runtime_log = runtime_logs["NAMD_0000000000_a_out.dat"][0]

        first_runtime_log.write_text(
            "changed-runtime-log",
            encoding="utf-8",
        )

        processor._archive_cycle_logs(
            0,
            1,
        )

        assert (logs_dir / "NAMD_0000000000_a_out.dat").read_text(
            encoding="utf-8"
        ) == "runtime-namd-0"

    finally:
        processor.close()
