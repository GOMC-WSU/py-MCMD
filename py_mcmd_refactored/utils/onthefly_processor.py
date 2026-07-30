"""Append-only processing for completed NAMD and GOMC log files."""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path
from typing import Iterable, Optional, TextIO

from utils.fifo_store import _discover_managed_root
from utils.path import format_cycle_id

logger = logging.getLogger(__name__)


K_TO_KCAL_MOL = 1.98720425864083e-3
AMU_PER_ANGSTROM3_TO_G_PER_CM3 = 1.6605402


def _parse_namd_log(
    lines: Iterable[str],
    current_step: int,
    e_titles: Optional[list[str]] = None,
    e_titles_density: Optional[list[str]] = None,
) -> tuple[
    Optional[list[str]],
    Optional[list[str]],
    list[tuple[list[str], Optional[float]]],
    int,
]:
    """Parse NAMD ETITLE/ENERGY records and calculate density when possible."""
    line_list = list(lines)
    total_mass = None

    for line in line_list:
        parts = line.split()
        if (
            line.startswith("Info:")
            and len(parts) >= 5
            and parts[1:4] == ["TOTAL", "MASS", "="]
        ):
            try:
                total_mass = float(parts[4])
            except ValueError:
                pass

    rows: list[tuple[list[str], Optional[float]]] = []
    last_ts = int(current_step)

    for line in line_list:
        if line.startswith("ETITLE:") and e_titles is None:
            e_titles = line.split()
            e_titles_density = e_titles[1:] + ["DENSITY"]
            continue

        if not line.startswith("ENERGY:") or not e_titles:
            continue

        row = line.split()

        try:
            ts_idx = e_titles.index("TS")
        except ValueError:
            ts_idx = 1

        if ts_idx >= len(row):
            continue

        try:
            normalized_ts = int(row[ts_idx]) + int(current_step)
        except ValueError:
            continue

        row[ts_idx] = str(normalized_ts)
        last_ts = normalized_ts
        density = None

        try:
            volume_idx = e_titles.index("VOLUME")
        except ValueError:
            volume_idx = None

        if volume_idx is not None and volume_idx < len(row):
            try:
                volume = float(row[volume_idx])
                if total_mass is not None and volume > 0:
                    density = (
                        AMU_PER_ANGSTROM3_TO_G_PER_CM3
                        * total_mass
                        / volume
                        * 1000.0
                    )
            except ValueError:
                pass

        rows.append((row, density))

    return e_titles, e_titles_density, rows, last_ts


def _parse_gomc_log(
    lines: Iterable[str],
    box_no: int,
    current_step: int,
    e_titles: Optional[list[str]] = None,
) -> tuple[
    Optional[list[str]],
    list[str],
    list[str],
    list[list[str]],
    list[list[str]],
    list[tuple[str, str]],
    int,
]:
    """Parse and merge GOMC energy/statistics records for one box."""
    energy_label = f"ENER_{box_no}:"
    stat_label = f"STAT_{box_no}:"

    stat_titles = None
    pending_energy = None

    merged_rows: list[list[str]] = []
    kcal_rows: list[list[str]] = []
    raw_lines: list[tuple[str, str]] = []

    last_step = int(current_step)

    for line in lines:
        if line.startswith("ETITLE:") and e_titles is None:
            e_titles = line.split()
            raw_lines.append(("ETITLE", line))
            continue

        if line.startswith(energy_label) and e_titles:
            values = line.split()

            row: list[str] = []
            kcal_row: list[str] = []
            raw_values: list[str] = []

            for index, value in enumerate(values):
                title = e_titles[index] if index < len(e_titles) else ""

                if title == "ETITLE:":
                    row.append(value)
                    kcal_row.append(value)
                    raw_values.append(value)

                elif title == "STEP":
                    try:
                        normalized = str(int(value) + int(current_step))
                    except ValueError:
                        normalized = value

                    row.append(normalized)
                    kcal_row.append(normalized)
                    raw_values.append(normalized)

                else:
                    try:
                        numeric = float(value)

                        row.append(str(numeric))
                        kcal_row.append(str(numeric * K_TO_KCAL_MOL))
                        raw_values.append(str(numeric))

                    except ValueError:
                        row.append(value)
                        kcal_row.append(value)
                        raw_values.append(value)

            pending_energy = (
                row,
                kcal_row,
            )

            raw_lines.append(
                (
                    "ENER",
                    "\t ".join(raw_values) + " \n",
                )
            )

            continue

        if line.startswith("STITLE:") and stat_titles is None:
            stat_titles = line.split()
            raw_lines.append(("STITLE", line))
            continue

        if (
            line.startswith(stat_label)
            and pending_energy is not None
            and stat_titles
        ):
            values = line.split()

            stat_row: list[str] = []
            raw_values: list[str] = []

            for index, value in enumerate(values):
                title = stat_titles[index] if index < len(stat_titles) else ""

                if title == "STITLE:":
                    stat_row.append(value)
                    raw_values.append(value)

                elif title == "STEP":
                    try:
                        normalized = str(int(value) + int(current_step))
                    except ValueError:
                        normalized = value

                    stat_row.append(normalized)
                    raw_values.append(normalized)

                else:
                    try:
                        numeric = str(float(value))

                        stat_row.append(numeric)
                        raw_values.append(numeric)

                    except ValueError:
                        stat_row.append(value)
                        raw_values.append(value)

            raw_lines.append(
                (
                    "STAT",
                    "\t ".join(raw_values) + " \n",
                )
            )

            energy_row, energy_kcal_row = pending_energy

            merged = energy_row[1:]
            merged_kcal = energy_kcal_row[1:]

            for index in range(2, len(stat_row)):
                value = stat_row[index]
                title = stat_titles[index] if index < len(stat_titles) else ""

                merged.append(value)

                if title == "TOT_DENSITY":
                    try:
                        merged_kcal.append(str(float(value) / 1000.0))
                    except ValueError:
                        merged_kcal.append(value)

                else:
                    merged_kcal.append(value)

            merged_rows.append(merged)
            kcal_rows.append(merged_kcal)

            try:
                last_step = int(merged[0])
            except (ValueError, IndexError):
                pass

            pending_energy = None

    merged_titles = list(e_titles[1:]) if e_titles else []

    kcal_titles = list(e_titles[1:]) if e_titles else []

    if stat_titles:
        merged_titles.extend(stat_titles[2:])
        kcal_titles.extend(stat_titles[2:])

    if merged_titles and not merged_titles[0].startswith("#"):
        merged_titles[0] = f"#{merged_titles[0]}"

    if kcal_titles and not kcal_titles[0].startswith("#"):
        kcal_titles[0] = f"#{kcal_titles[0]}"

    return (
        e_titles,
        merged_titles,
        kcal_titles,
        merged_rows,
        kcal_rows,
        raw_lines,
        last_step,
    )


# Module-level cache for which CPU core catdcd should be pinned to.
# Set once by the processor based on NAMD's core count. catdcd is pinned
# to a core OUTSIDE NAMD's range so it does not steal CPU from NAMD's
# compute-bound threads -- this keeps NAMD fast (like the old code) while
# still combining DCDs every cycle (crash-safe, unlike deferring to the end).
_CATDCD_CORE: Optional[int] = None


def _set_catdcd_core(core_id: Optional[int]) -> None:
    global _CATDCD_CORE
    _CATDCD_CORE = core_id


def _append_dcd(
    catdcd_bin: str | Path,
    src_dcd: str | Path,
    dst_dcd: str | Path,
) -> bool:
    """Append one DCD segment to a combined trajectory atomically.

    catdcd is pinned (via taskset) to a dedicated CPU core outside NAMD's
    range when _CATDCD_CORE is set, so the combine step does not compete
    with NAMD's compute-bound threads for CPU.
    """
    src = Path(src_dcd)
    dst = Path(dst_dcd)

    if not src.exists():
        logger.warning(
            "[OnTheFly] DCD source not found: %s",
            src,
        )
        return False

    dst.parent.mkdir(parents=True, exist_ok=True)

    tmp = dst.with_name(f"{dst.name}.tmp")
    tmp.unlink(missing_ok=True)

    command = [
        str(catdcd_bin),
        "-o",
        str(tmp),
    ]

    if dst.exists():
        command.append(str(dst))

    command.append(str(src))

    # Pin catdcd to its dedicated core (outside NAMD's range) if available.
    # taskset is standard on Linux; if unavailable the command still runs
    # normally, just without pinning.
    if _CATDCD_CORE is not None:
        import shutil as _shutil

        if _shutil.which("taskset"):
            command = ["taskset", "-c", str(_CATDCD_CORE)] + command

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            logger.warning(
                "[OnTheFly] catdcd failed: %s",
                result.stderr[:200],
            )
            tmp.unlink(missing_ok=True)
            return False

        if not tmp.exists():
            logger.warning(
                "[OnTheFly] catdcd did not create output: %s",
                tmp,
            )
            return False

        tmp.replace(dst)
        return True

    except OSError as exc:
        logger.warning(
            "[OnTheFly] DCD append error: %s",
            exc,
        )
        tmp.unlink(missing_ok=True)
        return False


class OnTheFlyProcessor:
    """
    Append newly parsed NAMD/GOMC rows to combined outputs per cycle.

    processing
    trajectory handling
    artifact preservation
    combined-output formatting
    """

    def __init__(
        self,
        cfg,
        combined_data_dir: str | Path,
        *,
        managed_root: Optional[str | Path] = None,
    ) -> None:
        self.cfg = cfg

        self.combined_dir = Path(combined_data_dir)
        self.combined_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.namd_root = Path(cfg.path_namd_runs)
        self.gomc_root = Path(cfg.path_gomc_runs)

        # self.sim_type = str(
        #     cfg.simulation_type
        # ).upper()

        # self._managed_root = _discover_managed_root(
        #     managed_root
        # )

        # self._current_step = 0

        self.sim_type = str(cfg.simulation_type).upper()

        self._managed_root = _discover_managed_root(managed_root)

        # Pin catdcd to the CPU core specified in the JSON (catdcd_core),
        # so the per-cycle DCD combine does not steal CPU from NAMD's
        # compute threads. Set catdcd_core in the JSON to a core OUTSIDE
        # NAMD's range (e.g. NAMD uses cores 0-7, set catdcd_core=8).
        # This keeps NAMD fast (like the old code) while still combining
        # every cycle so partial data survives a crash.
        try:
            catdcd_core = getattr(cfg, "catdcd_core", None)
            enable_affinity = bool(getattr(cfg, "enable_cpu_affinity", False))
            reserved = getattr(cfg, "otf_reserved_cores", None)

            chosen_core = None
            if catdcd_core is not None:
                # Explicit core ID takes priority
                chosen_core = int(catdcd_core)
            elif enable_affinity:
                # Derive the core from NAMD's range + reserved offset
                namd_cores = int(getattr(cfg, "no_core_box_0", 1)) + int(
                    getattr(cfg, "no_core_box_1", 0)
                )
                chosen_core = namd_cores  # first core past NAMD's range

            if chosen_core is not None:
                _set_catdcd_core(chosen_core)
                logger.info("[OnTheFly] catdcd pinned to core %d", chosen_core)
            else:
                logger.info("[OnTheFly] catdcd runs without CPU pinning.")
        except Exception as _exc:
            logger.warning(
                "[OnTheFly] Could not set catdcd CPU affinity: %s", _exc
            )

        self.catdcd_bin = Path(
            getattr(
                cfg,
                "rel_path_to_combine_binary_catdcd",
                (
                    "required_data/bin/catdcd-4.0b/"
                    "LINUXAMD64/bin/catdcd4.0/catdcd"
                ),
            )
        )

        self.combine_namd_dcd = bool(
            getattr(
                cfg,
                "combine_namd_dcd_file",
                True,
            )
        )

        self.combine_gomc_dcd = (
            bool(
                getattr(
                    cfg,
                    "combine_gomc_dcd_file",
                    True,
                )
            )
            and self.sim_type != "GCMC"
        )

        self._current_step = 0

        self._namd_e_titles = None
        self._namd_density_titles = None

        self._gomc_titles = {
            0: {
                "energy": None,
                "stat": None,
                "kcal": None,
            },
            1: {
                "energy": None,
                "stat": None,
                "kcal": None,
            },
        }

        self._header_written = {
            "combined": False,
            "namd_raw": False,
            "namd_density": False,
            "gomc_stat": False,
            "gomc_kcal": False,
            "gomc0_etitle": False,
            "gomc0_stitle": False,
            "gomc1_etitle": False,
            "gomc1_stitle": False,
        }

        self._namd_log_fh = self._open_append("NAMD_data_box_0.txt")

        self._gomc_log_fh = {
            0: self._open_append("GOMC_data_box_0.txt"),
            1: None,
        }

        if self.sim_type in {"GEMC", "GCMC"}:
            self._gomc_log_fh[1] = self._open_append("GOMC_data_box_1.txt")

        self._combined_fh = self._open_append(
            "combined_NAMD_GOMC_data_box_0.txt"
        )

        self._namd_density_fh = self._open_append("NAMD_data_density_box_0.txt")

        self._gomc_stat_fh = self._open_append("GOMC_Energies_Stat_box_0.txt")

        self._gomc_kcal_fh = self._open_append(
            "GOMC_Energies_Stat_kcal_per_mol_box_0.txt"
        )

        logger.info(
            "[OnTheFly] Initialized core processor. " "Output dir: %s",
            self.combined_dir,
        )

    def _open_append(
        self,
        basename: str,
    ) -> TextIO:
        return (self.combined_dir / basename).open(
            "a",
            encoding="utf-8",
            buffering=1,
        )

    def _namd_dir(
        self,
        run_no: int,
        box: int = 0,
    ) -> Path:
        suffix = "a" if box == 0 else "b"

        return self.namd_root / (f"{format_cycle_id(run_no, 10)}" f"_{suffix}")

    def _gomc_dir(
        self,
        run_no: int,
    ) -> Path:
        return self.gomc_root / format_cycle_id(run_no, 10)

    def _runtime_namd_dir(
        self,
        run_no: int,
        box: int = 0,
    ) -> Path:
        suffix = "a" if box == 0 else "b"

        return (
            self._managed_root
            / "NAMD"
            / (f"{format_cycle_id(run_no, 10)}" f"_{suffix}")
        )

    def _runtime_gomc_dir(
        self,
        run_no: int,
    ) -> Path:
        return self._managed_root / "GOMC" / format_cycle_id(run_no, 10)

    # @staticmethod
    # def _resolve_log_path(
    #     runtime_dir: Path,
    #     disk_dir: Path,
    # ) -> Optional[Path]:
    #     runtime_log = runtime_dir / "out.dat"

    #     if runtime_log.exists():
    #         return runtime_log

    #     disk_log = disk_dir / "out.dat"

    #     if disk_log.exists():
    #         return disk_log

    #     return None
    @staticmethod
    def _resolve_artifact_path(
        runtime_dir: Path,
        disk_dir: Path,
        basename: str,
    ) -> Optional[Path]:
        runtime_path = runtime_dir / basename

        if runtime_path.exists():
            return runtime_path

        disk_path = disk_dir / basename

        if disk_path.exists():
            return disk_path

        return None

    @staticmethod
    def _resolve_log_path(
        runtime_dir: Path,
        disk_dir: Path,
    ) -> Optional[Path]:
        return OnTheFlyProcessor._resolve_artifact_path(
            runtime_dir,
            disk_dir,
            "out.dat",
        )

    def set_current_step(
        self,
        current_step: int,
    ) -> None:
        """Seed the global step offset when processing a restarted simulation."""
        self._current_step = int(current_step)

    # def process_cycle(
    #     self,
    #     namd_run_no: int,
    #     gomc_run_no: int,
    # ) -> None:
    #     self._process_namd_step(namd_run_no)
    #     self._process_gomc_step(gomc_run_no)
    def process_cycle(
        self,
        namd_run_no: int,
        gomc_run_no: int,
    ) -> None:
        self._process_namd_step(namd_run_no)
        self._process_gomc_step(gomc_run_no)

        if self.combine_namd_dcd and self.sim_type in {"NVT", "NPT"}:
            self._append_namd_dcd(namd_run_no)

        if self.combine_gomc_dcd:
            self._append_gomc_dcd(gomc_run_no)

        self._copy_merged_psf(gomc_run_no)

        self._archive_cycle_logs(
            namd_run_no,
            gomc_run_no,
        )

    def close(self) -> None:
        handles = [
            self._namd_log_fh,
            self._gomc_log_fh[0],
            self._gomc_log_fh[1],
            self._combined_fh,
            self._namd_density_fh,
            self._gomc_stat_fh,
            self._gomc_kcal_fh,
        ]

        for handle in handles:
            if handle is None:
                continue

            try:
                handle.flush()
                handle.close()

            except Exception:
                logger.exception("[OnTheFly] Failed to close output file")

    def _process_namd_step(
        self,
        run_no: int,
    ) -> list[dict[str, str]]:
        out_path = self._resolve_log_path(
            self._runtime_namd_dir(run_no),
            self._namd_dir(run_no),
        )

        if out_path is None:
            logger.warning(
                "[OnTheFly] NAMD out.dat missing " "for run %d",
                run_no,
            )
            return []

        lines = out_path.read_text(
            encoding="utf-8",
            errors="ignore",
        ).splitlines(keepends=True)

        (
            self._namd_e_titles,
            self._namd_density_titles,
            raw_rows,
            last_ts,
        ) = _parse_namd_log(
            lines,
            self._current_step,
            self._namd_e_titles,
            self._namd_density_titles,
        )

        if self._namd_e_titles and not self._header_written["namd_raw"]:
            self._namd_log_fh.write("\t ".join(self._namd_e_titles) + "\n")

            self._header_written["namd_raw"] = True

        combined_rows = []

        for row, density in raw_rows:
            self._namd_log_fh.write("\t ".join(row) + " \n")

            if (
                self._namd_density_titles
                and not self._header_written["namd_density"]
            ):
                self._namd_density_fh.write(
                    "\t".join(self._namd_density_titles) + "\n"
                )

                self._header_written["namd_density"] = True

            density_value = str(density) if density is not None else "NA"

            self._namd_density_fh.write(
                "\t".join(row[1:] + [density_value]) + "\n"
            )

            def _column(
                title: str,
            ) -> str:
                try:
                    return row[self._namd_e_titles.index(title)]

                except (
                    ValueError,
                    IndexError,
                    AttributeError,
                ):
                    return "NA"

            combined_rows.append(
                {
                    "ENGINE": "NAMD",
                    "STEP": _column("TS"),
                    "TOTAL_POT": _column("POTENTIAL"),
                    "TOTAL_ELECT": _column("ELECT"),
                    "PRESSURE": _column("PRESSURE"),
                    "VOLUME": _column("VOLUME"),
                    "DENSITY": density_value,
                }
            )

        self._current_step = last_ts

        self._append_combined_rows(combined_rows)

        return combined_rows

    def _process_gomc_step(
        self,
        run_no: int,
    ) -> list[list[str]]:
        out_path = self._resolve_log_path(
            self._runtime_gomc_dir(run_no),
            self._gomc_dir(run_no),
        )

        if out_path is None:
            logger.warning(
                "[OnTheFly] GOMC out.dat missing " "for run %d",
                run_no,
            )
            return []

        lines = out_path.read_text(
            encoding="utf-8",
            errors="ignore",
        ).splitlines(keepends=True)

        step_offset = self._current_step

        (
            merged_rows,
            kcal_rows,
            raw_lines,
            last_step,
        ) = self._parse_gomc_box(
            lines,
            box_no=0,
            step_offset=step_offset,
        )

        self._append_raw_gomc_lines(
            raw_lines,
            box_no=0,
        )

        rows_to_write = merged_rows[1:] if len(merged_rows) > 1 else merged_rows

        kcal_to_write = kcal_rows[1:] if len(kcal_rows) > 1 else kcal_rows

        box0_titles = self._gomc_titles[0]

        if rows_to_write and box0_titles["stat"]:
            if not self._header_written["gomc_stat"]:
                self._gomc_stat_fh.write("\t".join(box0_titles["stat"]) + "\n")

                self._header_written["gomc_stat"] = True

            for row in rows_to_write:
                self._gomc_stat_fh.write("\t".join(row) + "\n")

                self._append_gomc_combined_row(row)

        if kcal_to_write and box0_titles["kcal"]:
            if not self._header_written["gomc_kcal"]:
                self._gomc_kcal_fh.write("\t".join(box0_titles["kcal"]) + "\n")

                self._header_written["gomc_kcal"] = True

            for row in kcal_to_write:
                self._gomc_kcal_fh.write("\t".join(row) + "\n")

        self._current_step = last_step

        if self.sim_type in {
            "GEMC",
            "GCMC",
        }:
            (
                _,
                _,
                raw_box1,
                _,
            ) = self._parse_gomc_box(
                lines,
                box_no=1,
                step_offset=step_offset,
            )

            self._append_raw_gomc_lines(
                raw_box1,
                box_no=1,
                skip_duplicate_pair=True,
            )

        return rows_to_write

    def _parse_gomc_box(
        self,
        lines: Iterable[str],
        *,
        box_no: int,
        step_offset: int,
    ) -> tuple[
        list[list[str]],
        list[list[str]],
        list[tuple[str, str]],
        int,
    ]:
        titles = self._gomc_titles[box_no]

        (
            titles["energy"],
            titles["stat"],
            titles["kcal"],
            merged_rows,
            kcal_rows,
            raw_lines,
            last_step,
        ) = _parse_gomc_log(
            lines,
            box_no,
            step_offset,
            titles["energy"],
        )

        return (
            merged_rows,
            kcal_rows,
            raw_lines,
            last_step,
        )

    def _append_raw_gomc_lines(
        self,
        raw_lines: list[tuple[str, str]],
        *,
        box_no: int,
        skip_duplicate_pair: bool = False,
    ) -> None:
        handle = self._gomc_log_fh[box_no]

        if handle is None:
            return

        energy_seen = 0
        stat_seen = 0

        energy_count = sum(1 for kind, _ in raw_lines if kind == "ENER")

        for kind, content in raw_lines:
            header_key = None

            if kind == "ETITLE":
                header_key = f"gomc{box_no}_etitle"

            elif kind == "STITLE":
                header_key = f"gomc{box_no}_stitle"

            if header_key is not None:
                if not self._header_written[header_key]:
                    handle.write(content)

                    self._header_written[header_key] = True

                continue

            if kind == "ENER":
                energy_seen += 1

                if (
                    skip_duplicate_pair
                    and energy_count > 1
                    and energy_seen == 1
                ):
                    continue

            elif kind == "STAT":
                stat_seen += 1

                if skip_duplicate_pair and energy_count > 1 and stat_seen == 1:
                    continue

            handle.write(content)

    def _append_namd_dcd(
        self,
        run_no: int,
    ) -> bool:
        src = self._resolve_artifact_path(
            self._runtime_namd_dir(
                run_no,
                0,
            ),
            self._namd_dir(
                run_no,
                0,
            ),
            "namdOut.dcd",
        )

        if src is None:
            logger.warning(
                "[OnTheFly] NAMD DCD missing for run %d",
                run_no,
            )
            return False

        dst = self.combined_dir / "combined_box_0_NAMD_dcd_files.dcd"

        return _append_dcd(
            self.catdcd_bin,
            src,
            dst,
        )

    def _append_gomc_dcd(
        self,
        run_no: int,
    ) -> dict[int, bool]:
        results: dict[int, bool] = {}

        boxes = [0]

        if self.sim_type in {"GEMC", "GCMC"}:
            boxes.append(1)

        for box_no in boxes:
            basename = f"Output_data_BOX_{box_no}.dcd"

            src = self._resolve_artifact_path(
                self._runtime_gomc_dir(run_no),
                self._gomc_dir(run_no),
                basename,
            )

            if src is None:
                logger.warning(
                    "[OnTheFly] GOMC box-%d DCD missing " "for run %d",
                    box_no,
                    run_no,
                )
                results[box_no] = False
                continue

            dst = self.combined_dir / (
                f"combined_box_{box_no}_" "GOMC_dcd_files.dcd"
            )

            results[box_no] = _append_dcd(
                self.catdcd_bin,
                src,
                dst,
            )

        return results

    def _copy_merged_psf(
        self,
        gomc_run_no: int,
    ) -> bool:
        dst = self.combined_dir / "Output_data_merged.psf"

        if dst.exists():
            return False

        src = self._resolve_artifact_path(
            self._runtime_gomc_dir(gomc_run_no),
            self._gomc_dir(gomc_run_no),
            "Output_data_merged.psf",
        )

        if src is None:
            logger.warning(
                "[OnTheFly] Merged GOMC PSF missing " "for run %d",
                gomc_run_no,
            )
            return False

        try:
            shutil.copy2(
                src,
                dst,
            )
            return True

        except OSError as exc:
            logger.warning(
                "[OnTheFly] Failed to copy merged PSF " "%s: %s",
                src,
                exc,
            )
            return False

    def _archive_cycle_log(
        self,
        *,
        engine: str,
        runtime_dir: Path,
        disk_dir: Path,
    ) -> bool:
        src = self._resolve_log_path(
            runtime_dir,
            disk_dir,
        )

        if src is None:
            return False

        logs_dir = self.combined_dir / "cycle_logs"

        logs_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        dst = logs_dir / (f"{engine.upper()}_" f"{runtime_dir.name}_out.dat")

        if dst.exists():
            return False

        try:
            shutil.copy2(
                src,
                dst,
            )
            return True

        except OSError as exc:
            logger.warning(
                "[OnTheFly] Failed to archive %s: %s",
                src,
                exc,
            )
            return False

    def _archive_cycle_logs(
        self,
        namd_run_no: int,
        gomc_run_no: int,
    ) -> None:
        namd_boxes = [0]

        if self.sim_type == "GEMC" and not bool(
            getattr(
                self.cfg,
                "only_use_box_0_for_namd_for_gemc",
                True,
            )
        ):
            namd_boxes.append(1)

        for box_no in namd_boxes:
            self._archive_cycle_log(
                engine="NAMD",
                runtime_dir=self._runtime_namd_dir(
                    namd_run_no,
                    box_no,
                ),
                disk_dir=self._namd_dir(
                    namd_run_no,
                    box_no,
                ),
            )

        self._archive_cycle_log(
            engine="GOMC",
            runtime_dir=self._runtime_gomc_dir(gomc_run_no),
            disk_dir=self._gomc_dir(gomc_run_no),
        )

    def _append_combined_rows(
        self,
        rows: list[dict[str, str]],
    ) -> None:
        if rows and not self._header_written["combined"]:
            self._combined_fh.write(
                "#ENGINE\tSTEP\tTOTAL_POT\t"
                "TOTAL_ELECT\tPRESSURE\t"
                "VOLUME\tDENSITY\n"
            )

            self._header_written["combined"] = True

        for row in rows:
            self._combined_fh.write(
                f"{row['ENGINE']}\t"
                f"{row['STEP']}\t"
                f"{row['TOTAL_POT']}\t"
                f"{row['TOTAL_ELECT']}\t"
                f"{row['PRESSURE']}\t"
                f"{row['VOLUME']}\t"
                f"{row['DENSITY']}\n"
            )

    def _append_gomc_combined_row(
        self,
        row: list[str],
    ) -> None:
        titles = self._gomc_titles[0]

        stat_titles = titles["stat"]
        energy_titles = titles["energy"]

        if not stat_titles or not energy_titles:
            return

        def _stat_column(
            title: str,
        ) -> str:
            try:
                return row[stat_titles.index(title)]

            except (
                ValueError,
                IndexError,
            ):
                return "NA"

        def _energy_column(
            title: str,
        ) -> str:
            try:
                return row[energy_titles.index(title) - 1]

            except (
                ValueError,
                IndexError,
            ):
                return "NA"

        self._append_combined_rows(
            [
                {
                    "ENGINE": "GOMC",
                    "STEP": (row[0] if row else "NA"),
                    "TOTAL_POT": _energy_column("TOTAL"),
                    "TOTAL_ELECT": _energy_column("TOTAL_ELECT"),
                    "PRESSURE": _stat_column("PRESSURE"),
                    "VOLUME": _stat_column("VOLUME"),
                    "DENSITY": _stat_column("TOT_DENSITY"),
                }
            ]
        )
