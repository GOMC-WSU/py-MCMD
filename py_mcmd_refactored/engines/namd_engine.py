import logging
import os
import shutil
import time
from pathlib import Path
from turtle import width
from typing import Optional

from engines.base import Engine as BaseEngine
from engines.namd.constants import DEFAULT_NAMD_E_TITLES_LIST
from engines.namd.energy import get_namd_energy_data
from engines.namd.energy_compare import compare_namd_gomc_energies
from engines.namd.namd_writer import write_namd_conf_file
from engines.namd.parser import (
    extract_pme_grid_from_out,
    find_run0_fft_filename,
    get_run0_dir,
)
from orchestrator.state import RunState
from utils.path import format_cycle_id
from utils.persisted_file_lists import persisted_output_path
from utils.subprocess_runner import Command, SubprocessRunner

logger = logging.getLogger(__name__)


from engines.namd.plan import NamdExecutionPlan, build_namd_execution_plan

logger = logging.getLogger(__name__)


class NamdEngine(BaseEngine):

    def __init__(self, cfg, engine_type="NAMD", dry_run: bool = False):
        super().__init__(cfg, engine_type, dry_run=dry_run)
        self.dry_run = dry_run

        self.bin_dir = Path(cfg.namd2_bin_directory)
        self.path_template = (
            Path(cfg.path_namd_template) if cfg.path_namd_template else None
        )

        if self.bin_dir.exists():
            self.exec_path = str((self.bin_dir / "namd2").resolve())
        else:
            if self.dry_run:
                logger.warning(
                    "NAMD bin dir %s not found; continuing in dry_run.",
                    self.bin_dir,
                )
                self.exec_path = "namd2"
            else:
                raise FileNotFoundError(
                    f"NAMD binary directory {self.bin_dir} does not exist."
                )

        # IMPORTANT: do NOT use `self.run_steps` as an int (it must remain callable)
        self.steps_per_run = int(getattr(cfg, "namd_run_steps", 0))

        # subprocess adapter
        self.runner = SubprocessRunner(dry_run=self.dry_run)

    def run(self):
        raise NotImplementedError("Use NamdEngine.run_segment(...) instead.")

    # -------------------------------------------------------------------------
    # Run-0 PME helpers
    # -------------------------------------------------------------------------
    def get_run0_pme_dims(
        self,
        box_number: int,
        run_root: Optional[Path] = None,
    ) -> tuple[Optional[int], Optional[int], Optional[int], str]:
        """
        Returns (nx, ny, nz, run0_dir_path) for the given box (0 or 1).
        Never raises on missing files; returns (None, None, None, run0_dir_path).
        """
        if not isinstance(box_number, int) or box_number not in (0, 1):
            raise ValueError("box_number must be integer 0 or 1")

        # Run 0 directory name (zero-padded run id + suffix a/b)
        run0_id = format_cycle_id(0)  # default width in utils.path is 10
        suffix = "a" if box_number == 0 else "b"

        root = (
            Path(run_root)
            if run_root is not None
            else Path(self.cfg.path_namd_runs)
        )
        run0_dir = root / f"{run0_id}_{suffix}"

        out_path = run0_dir / "out.dat"
        nx, ny, nz = extract_pme_grid_from_out(out_path)

        if nx is None:
            logger.warning(
                "[NAMD] PME grid not found in %s (box=%s)", out_path, box_number
            )

        return nx, ny, nz, str(run0_dir)

    # -------------------------------------------------------------------------
    # Run-0 FFT helpers (with 10-digit→8-digit fallback)
    # -------------------------------------------------------------------------

    def get_run0_fft_filename(
        self,
        box_number: int,
        run_root: Optional[Path] = None,
    ) -> tuple[Optional[str], str]:
        """
        Returns (fft_filename or None, run0_dir_path_str) for box_number ∈ {0, 1}.

        Behavior (matches existing unit tests):
        - If run0 directory exists (8-digit or 10-digit), return:
            - (filename, dir) if a file starting with 'FFTW_NAMD' exists
            - (None, dir) if no matching file exists
        - If neither 8-digit nor 10-digit run0 dir exists, raise FileNotFoundError.
        """
        if not isinstance(box_number, int) or box_number not in (0, 1):
            raise ValueError("box_number must be integer 0 or 1")

        # IMPORTANT: existing tests create 8-digit dirs (00000000_a), so try 8 first.
        widths_to_try = (8, 10)

        for width in widths_to_try:
            base_root = (
                Path(run_root)
                if run_root is not None
                else Path(self.cfg.path_namd_runs)
            )
            run0_dir = get_run0_dir(base_root, box_number, id_width=width)

            if not run0_dir.exists():
                continue  # try next width

            # Directory exists -> safe to call finder (which raises if dir missing)
            fft_name = find_run0_fft_filename(run0_dir)

            if fft_name is None:
                logger.warning(
                    "[NAMD] FFTW plan file not detected in run0 dir %s (box=%s)",
                    run0_dir,
                    box_number,
                )
            return fft_name, str(run0_dir)

        # Neither width exists -> keep test behavior for missing run0 dir
        base = Path(self.cfg.path_namd_runs)
        suffix = "a" if box_number == 0 else "b"
        raise FileNotFoundError(
            f"Run-0 directory not found for box={box_number}. Tried: "
            f"{base}/00000000_{suffix} and {base}/0000000000_{suffix}"
        )

    def delete_namd_run_0_fft_file(
        self, box_number: int, run_root: Optional[Path] = None
    ) -> None:
        """
        Deletes the run 0 (1st NAMD simulation) FFT filename.

        Parameters
        ----------
        box_number : int
            The simulation box number, which can only be 0 or 1
        """
        # Preserve legacy error message text, but modernize validation
        if not isinstance(box_number, int) or box_number not in (0, 1):
            raise ValueError(
                "ERROR Enter an interger of 0 or 1  for box_number in "
                "the get_namd_run_0_pme_dim function. \n"
            )

        write_log_data = (
            "*************************************************\n"
            "The NAMD FFT file was deleted from Run 0 in Box {} \n"
            "************************************************* \n".format(
                str(box_number)
            )
        )

        try:
            # Use the parser to locate the FFT file and directory

            fft_filename, run0_dir = self._get_run0_fft_filename_compat(
                box_number=box_number,
                run_root=run_root,
            )

            # If we found a filename, delete it. Mirror legacy: swallow errors.
            if fft_filename:
                fft_path = Path(run0_dir) / fft_filename
                try:
                    # Python 3.8+: missing_ok available
                    fft_path.unlink(missing_ok=True)  # type: ignore[arg-type]
                except TypeError:
                    # Fallback for Python < 3.8
                    try:
                        fft_path.unlink()
                    except FileNotFoundError:
                        pass

            # Log/print banner regardless of outcome (legacy parity)
            logger.info(write_log_data.strip("\n"))
            print(write_log_data)

        except Exception:
            # Legacy behavior: still emit the banner even if something goes wrong
            logger.info(write_log_data.strip("\n"))
            print(write_log_data)

    def run_steps(
        self,
        *,
        run_dir: Path,
        cores: int,
        fifo_resources=None,
        fifo_basename: str = "box0.out.dat",
    ) -> int:
        cmd = Command(
            argv=[str(self.exec_path), f"+p{int(cores)}", "in.conf"],
            cwd=Path(run_dir),
            **self._stdout_command_kwargs(
                run_dir=Path(run_dir),
                fifo_resources=fifo_resources,
                fifo_basename=fifo_basename,
            ),
        )
        return self.runner.run_and_wait(cmd)

    def _run0_fft_cache_dir(self, box_number: int, managed_root: Path) -> Path:
        if not isinstance(box_number, int) or box_number not in (0, 1):
            raise ValueError("box_number must be integer 0 or 1")
        return (
            Path(managed_root)
            / "_engine_cache"
            / "NAMD"
            / f"run0_fft_box{box_number}"
        )

    def get_cached_run0_fft_filename(
        self,
        box_number: int,
        *,
        managed_root: Path,
    ) -> tuple[Optional[str], str]:
        cache_dir = self._run0_fft_cache_dir(box_number, managed_root)
        fft_name = (
            find_run0_fft_filename(cache_dir) if cache_dir.exists() else None
        )
        return fft_name, str(cache_dir)

    def cache_run0_fft_file(
        self,
        box_number: int,
        *,
        run_root: Optional[Path] = None,
        managed_root: Optional[Path] = None,
    ) -> Optional[Path]:
        if managed_root is None:
            return None

        fft_filename, run0_dir = self._get_run0_fft_filename_compat(
            box_number,
            run_root=run_root,
        )
        if not fft_filename:
            logger.warning(
                "[NAMD] Cannot cache run0 FFT file: none detected for box=%s (run0_dir=%s)",
                box_number,
                run0_dir,
            )
            return None

        src = Path(run0_dir) / fft_filename
        if not src.exists():
            logger.warning(
                "[NAMD] Cannot cache run0 FFT file because source is missing: %s",
                src,
            )
            return None

        cache_dir = self._run0_fft_cache_dir(box_number, managed_root)
        cache_dir.mkdir(parents=True, exist_ok=True)

        for existing in cache_dir.iterdir():
            if existing.is_file() and existing.name.startswith("FFTW_NAMD"):
                existing.unlink()

        dst = cache_dir / fft_filename
        shutil.copy2(src, dst)
        logger.info(
            "[NAMD] Cached run0 FFT file for box=%s: %s -> %s",
            box_number,
            src,
            dst,
        )
        return dst

    def link_run0_fft_file_into_dir(
        self,
        box_number: int,
        dest_dir: Path,
        run_root: Optional[Path] = None,
        managed_root: Optional[Path] = None,
    ) -> None:
        if not isinstance(box_number, int) or box_number not in (0, 1):
            raise ValueError("box_number must be integer 0 or 1")

        dest_dir = Path(dest_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)

        fft_filename = None
        run0_dir = None

        try:
            if managed_root is not None:
                cached_fft_filename, cached_dir = (
                    self.get_cached_run0_fft_filename(
                        box_number,
                        managed_root=Path(managed_root),
                    )
                )
                if cached_fft_filename:
                    fft_filename = cached_fft_filename
                    run0_dir = cached_dir

            if fft_filename is None:
                fft_filename, run0_dir = self._get_run0_fft_filename_compat(
                    box_number,
                    run_root=run_root,
                )

        except FileNotFoundError as e:
            if self.dry_run:
                logger.warning(
                    "[NAMD] Dry-run: run0 FFT source directory missing for box=%s; skipping FFT link. %s",
                    box_number,
                    e,
                )
                return
            raise

        if not fft_filename:
            logger.warning(
                "[NAMD] Cannot link run0 FFT file: none detected for box=%s (run0_dir=%s)",
                box_number,
                run0_dir,
            )
            return

        src = Path(run0_dir) / fft_filename
        dst = dest_dir / fft_filename

        try:
            if dst.is_symlink() or dst.is_file():
                dst.unlink()
        except FileNotFoundError:
            pass

        if dst.exists() and dst.is_dir():
            raise IsADirectoryError(
                f"Destination path {dst} is a directory; cannot overwrite with symlink"
            )

        if not src.exists():
            if self.dry_run:
                logger.warning(
                    "[NAMD] Dry-run: run0 FFT source file missing for box=%s; skipping FFT link: %s",
                    box_number,
                    src,
                )
                return
            raise FileNotFoundError(f"Run-0 FFT file not found: {src}")

        dst.symlink_to(src)
        logger.info(
            "[NAMD] Linked run0 FFT file for box=%s: %s -> %s",
            box_number,
            dst,
            src,
        )

    def build_execution_plan(
        self, *, box0_dir: Path, box1_dir: Optional[Path]
    ) -> NamdExecutionPlan:
        exec_path = (
            str(self.exec_path) if self.exec_path is not None else "namd2"
        )
        return build_namd_execution_plan(
            self.cfg,
            exec_path=exec_path,
            box0_dir=Path(box0_dir),
            box1_dir=Path(box1_dir) if box1_dir is not None else None,
        )

    def execute_plan(self, plan: NamdExecutionPlan) -> dict:
        """Execute the plan with legacy wait semantics.

        - series: start+wait box0, then start+wait box1
        - parallel: start box0, start box1, then wait box0, wait box1
        """
        if plan.mode == "series" or plan.box1 is None:
            h0 = self.runner.start(plan.box0)
            rc0 = self.runner.wait(h0)
            rc1 = None
            if plan.box1 is not None:
                h1 = self.runner.start(plan.box1)
                rc1 = self.runner.wait(h1)
            return {"rc_box0": rc0, "rc_box1": rc1, "mode": plan.mode}

        # parallel
        h0 = self.runner.start(plan.box0)
        h1 = self.runner.start(plan.box1)
        rc0 = self.runner.wait(h0)
        rc1 = self.runner.wait(h1)
        return {"rc_box0": rc0, "rc_box1": rc1, "mode": plan.mode}

    # -------------------------------------------------------------------------
    # NAMD phase end-to-end (even run_no)
    # -------------------------------------------------------------------------
    def _two_box_enabled(self) -> bool:
        return (self.cfg.simulation_type == "GEMC") and (
            self.cfg.only_use_box_0_for_namd_for_gemc is False
        )

    def run_segment(
        self, *, run_no: int, state: RunState, fifo_resources=None
    ) -> dict:
        """Run the full NAMD segment for an even run_no and update RunState."""

        # runtime_namd_root = self._runtime_namd_root(fifo_resources)
        runtime_namd_root = self._runtime_namd_root(fifo_resources)
        managed_root = (
            Path(fifo_resources.managed_root)
            if fifo_resources is not None
            else None
        )

        if int(run_no) % 2 != 0:
            raise ValueError(
                f"NAMD segment must be called for even run_no; got run_no={run_no}"
            )

        box0 = 0
        box1 = 1
        two_box = self._two_box_enabled()

        gomc_newdir = (
            str(state.gomc_dir) if state.gomc_dir is not None else "NA"
        )

        self._ensure_pme_dims_for_dry_run(state)

        # --- Ensure namd_writer globals are wired from config (required for real runs) ---
        from engines.namd import namd_writer as nw

        # Resolve FF/parameter files from config (must not be empty for real NAMD runs)
        ff_files = getattr(self.cfg, "starting_ff_file_list_namd", None) or []
        if not ff_files:
            raise ValueError(
                "No NAMD parameter files provided. Set `starting_ff_file_list_namd` "
                "in user_input_NAMD_GOMC.json to one or more CHARMM parameter files."
            )

        root = Path.cwd()  # repo root where you run the CLI
        nw.starting_ff_file_list_namd = [
            (
                (root / f).resolve()
                if not Path(f).is_absolute()
                else Path(f).resolve()
            )
            for f in ff_files
        ]

        # namd_writer also uses this global when computing PME behavior
        nw.simulation_type = self.cfg.simulation_type
        # 1) Write NAMD config(s)
        python_file_directory = Path.cwd()

        namd_box0_dir = write_namd_conf_file(
            python_file_directory,
            self.cfg.path_namd_template,
            # self.cfg.path_namd_runs,
            runtime_namd_root,
            gomc_newdir,
            run_no,
            box0,
            self.cfg.namd_run_steps,
            self.cfg.namd_minimize_steps,
            self.cfg.namd_rst_dcd_xst_steps,
            self.cfg.namd_console_blkavg_e_and_p_steps,
            self.cfg.simulation_temp_k,
            self.cfg.simulation_pressure_bar,
            self.cfg.starting_pdb_box_0_file,
            self.cfg.starting_psf_box_0_file,
            state.pme_box0.x,
            state.pme_box0.y,
            state.pme_box0.z,
            set_x_dim=self.cfg.set_dims_box_0_list[0],
            set_y_dim=self.cfg.set_dims_box_0_list[1],
            set_z_dim=self.cfg.set_dims_box_0_list[2],
        )
        state.namd_box0_dir = Path(namd_box0_dir)

        namd_box1_dir: Optional[str] = None
        if two_box:
            namd_box1_dir = write_namd_conf_file(
                python_file_directory,
                self.cfg.path_namd_template,
                # self.cfg.path_namd_runs,
                runtime_namd_root,
                gomc_newdir,
                run_no,
                box1,
                self.cfg.namd_run_steps,
                self.cfg.namd_minimize_steps,
                self.cfg.namd_rst_dcd_xst_steps,
                self.cfg.namd_console_blkavg_e_and_p_steps,
                self.cfg.simulation_temp_k,
                self.cfg.simulation_pressure_bar,
                self.cfg.starting_pdb_box_1_file,
                self.cfg.starting_psf_box_1_file,
                state.pme_box1.x,
                state.pme_box1.y,
                state.pme_box1.z,
                set_x_dim=self.cfg.set_dims_box_1_list[0],
                set_y_dim=self.cfg.set_dims_box_1_list[1],
                set_z_dim=self.cfg.set_dims_box_1_list[2],
                fft_add_namd_ang_to_box_dim=0,
            )
            state.namd_box1_dir = Path(namd_box1_dir)

        if self.dry_run:
            # Box 0 placeholders (use configured dims)
            self._ensure_dry_run_restart_files(
                Path(state.namd_box0_dir),
                self.cfg.set_dims_box_0_list,
            )

            # Box 1 placeholders if two-box NAMD is enabled
            if getattr(state, "namd_box1_dir", None) is not None:
                self._ensure_dry_run_restart_files(
                    Path(state.namd_box1_dir),
                    self.cfg.set_dims_box_1_list,
                )
        # 2) FFT housekeeping
        if run_no == 0:
            # self.delete_namd_run_0_fft_file(box0)
            self.delete_namd_run_0_fft_file(box0, run_root=runtime_namd_root)
            if two_box:
                # self.delete_namd_run_0_fft_file(box1)
                self.delete_namd_run_0_fft_file(
                    box1, run_root=runtime_namd_root
                )
        else:

            self.link_run0_fft_file_into_dir(
                box0,
                Path(namd_box0_dir),
                run_root=runtime_namd_root,
                managed_root=managed_root,
            )
            if two_box and namd_box1_dir is not None:

                self.link_run0_fft_file_into_dir(
                    box1,
                    Path(namd_box1_dir),
                    run_root=runtime_namd_root,
                    managed_root=managed_root,
                )

        # 3) Execute NAMD with legacy series/parallel semantics
        mode = self.cfg.namd_simulation_order if two_box else "series"

        cores0 = (
            int(self.cfg.total_no_cores)
            if (not two_box or mode == "series")
            else int(self.cfg.no_core_box_0)
        )

        disk_box0_dir = self._disk_namd_dir(fifo_resources, 0, run_no)
        disk_box0_dir.mkdir(parents=True, exist_ok=True)

        cmd0 = Command(
            argv=[str(self.exec_path), f"+p{cores0}", "in.conf"],
            cwd=Path(namd_box0_dir),
            **self._stdout_command_kwargs(
                runtime_dir=Path(namd_box0_dir),
                disk_dir=disk_box0_dir,
            ),
        )

        cmd1: Optional[Command] = None
        if two_box and namd_box1_dir is not None:
            cores1 = (
                int(self.cfg.total_no_cores)
                if mode == "series"
                else int(self.cfg.no_core_box_1)
            )

            disk_box1_dir = self._disk_namd_dir(fifo_resources, 1, run_no)
            disk_box1_dir.mkdir(parents=True, exist_ok=True)

            cmd1 = Command(
                argv=[str(self.exec_path), f"+p{cores1}", "in.conf"],
                cwd=Path(namd_box1_dir),
                **self._stdout_command_kwargs(
                    runtime_dir=Path(namd_box1_dir),
                    disk_dir=disk_box1_dir,
                ),
            )

        rc0 = rc1 = None
        box0_time = 0.0
        box1_time = 0.0

        if cmd1 is None or mode == "series":
            t0 = time.perf_counter()
            h0 = self.runner.start(cmd0)
            rc0 = self.runner.wait(h0)
            box0_time = time.perf_counter() - t0

            if cmd1 is not None:
                t1 = time.perf_counter()
                h1 = self.runner.start(cmd1)
                rc1 = self.runner.wait(h1)
                box1_time = time.perf_counter() - t1

            max_namd_cycle_time_s = box0_time + box1_time
        else:
            t0 = time.perf_counter()
            h0 = self.runner.start(cmd0)
            t1 = time.perf_counter()
            h1 = self.runner.start(cmd1)

            rc0 = self.runner.wait(h0)
            end0 = time.perf_counter()
            rc1 = self.runner.wait(h1)
            end1 = time.perf_counter()

            box0_time = end0 - t0
            box1_time = end1 - t1
            max_namd_cycle_time_s = max(box0_time, box1_time)

        state.timings.max_namd_cycle_time_s = round(max_namd_cycle_time_s, 6)

        if (rc0 not in (None, 0)) or (rc1 not in (None, 0)):
            if not self.dry_run:
                raise RuntimeError(
                    f"NAMD failed (rc0={rc0}, rc1={rc1}, mode={mode})"
                )

        # 4) Parse energies -> cache in state
        def _parse_to_energy(run_dir: Path, energy_obj) -> None:
            lines = (
                (run_dir / "out.dat")
                .read_text(errors="ignore")
                .splitlines(True)
            )
            (
                _elect_series,
                _elect_initial,
                _elect_final,
                _pot_series,
                pot_initial,
                pot_final,
                _vpe_series,
                vpe_initial,
                vpe_final,
            ) = get_namd_energy_data(lines, DEFAULT_NAMD_E_TITLES_LIST)
            energy_obj.namd_potential_initial = pot_initial
            energy_obj.namd_potential_final = pot_final
            energy_obj.namd_vdw_plus_elec_initial = vpe_initial
            energy_obj.namd_vdw_plus_elec_final = vpe_final

        try:
            _parse_to_energy(Path(namd_box0_dir), state.energy_box0)
        except Exception as e:
            if self.dry_run:
                logger.warning(
                    "[NAMD] Energy parse failed for box0 (dry_run): %s", e
                )
            else:
                raise

        if two_box and namd_box1_dir is not None:
            try:
                _parse_to_energy(Path(namd_box1_dir), state.energy_box1)
            except Exception as e:
                if self.dry_run:
                    logger.warning(
                        "[NAMD] Energy parse failed for box1 (dry_run): %s", e
                    )
                else:
                    raise

        # 5) Continuity check (GOMC -> NAMD) when applicable
        if (run_no != 0) and (run_no != int(self.cfg.starting_sims_namd_gomc)):
            e0 = state.energy_box0
            if (
                (e0.gomc_potential_final is not None)
                and (e0.namd_potential_initial is not None)
                and (e0.gomc_vdw_plus_elec_final is not None)
                and (e0.namd_vdw_plus_elec_initial is not None)
            ):
                compare_namd_gomc_energies(
                    self.cfg,
                    e0.gomc_potential_final,
                    e0.namd_potential_initial,
                    e0.gomc_vdw_plus_elec_final,
                    e0.namd_vdw_plus_elec_initial,
                    run_no,
                    0,
                )

            if two_box:
                e1 = state.energy_box1
                if (
                    (e1.gomc_potential_final is not None)
                    and (e1.namd_potential_initial is not None)
                    and (e1.gomc_vdw_plus_elec_final is not None)
                    and (e1.namd_vdw_plus_elec_initial is not None)
                ):
                    compare_namd_gomc_energies(
                        self.cfg,
                        e1.gomc_potential_final,
                        e1.namd_potential_initial,
                        e1.gomc_vdw_plus_elec_final,
                        e1.namd_vdw_plus_elec_initial,
                        run_no,
                        1,
                    )

        # 6) Update PME dims after Run-0 (out.dat exists now)
        if run_no == 0:
            nx0, ny0, nz0, _ = self.get_run0_pme_dims(
                0, run_root=runtime_namd_root
            )
            if (nx0 is not None) and (ny0 is not None) and (nz0 is not None):
                state.pme_box0.x, state.pme_box0.y, state.pme_box0.z = (
                    int(nx0),
                    int(ny0),
                    int(nz0),
                )

            self.cache_run0_fft_file(
                0,
                run_root=runtime_namd_root,
                managed_root=managed_root,
            )

            if two_box:
                nx1, ny1, nz1, _ = self.get_run0_pme_dims(
                    1, run_root=runtime_namd_root
                )

                if (
                    (nx1 is not None)
                    and (ny1 is not None)
                    and (nz1 is not None)
                ):
                    state.pme_box1.x, state.pme_box1.y, state.pme_box1.z = (
                        int(nx1),
                        int(ny1),
                        int(nz1),
                    )

                self.cache_run0_fft_file(
                    1,
                    run_root=runtime_namd_root,
                    managed_root=managed_root,
                )

        # 7) Update step counter (legacy rule)
        if run_no == 0:
            state.current_step += int(self.cfg.namd_run_steps) + int(
                self.cfg.namd_minimize_steps
            )
        else:
            state.current_step += int(self.cfg.namd_run_steps)

        return {
            "run_no": int(run_no),
            "mode": mode,
            "rc_box0": rc0,
            "rc_box1": rc1,
            "namd_box0_dir": str(namd_box0_dir),
            "namd_box1_dir": (
                str(namd_box1_dir) if namd_box1_dir is not None else None
            ),
        }

    def _ensure_dry_run_restart_files(self, run_dir: Path, dims_xyz) -> None:
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "namdOut.restart.coor").touch(exist_ok=True)
        (run_dir / "namdOut.restart.vel").touch(exist_ok=True)

        xsc = run_dir / "namdOut.restart.xsc"
        if not xsc.exists():
            x, y, z = [float(v) for v in dims_xyz]
            # xsc parser expects last line tokens with indices 1,5,9 = Lx,Ly,Lz
            xsc.write_text(f"0 {x} 0 0 0 {y} 0 0 0 {z}\n", encoding="utf-8")

    def _ensure_pme_dims_for_dry_run(self, state) -> None:
        """Ensure PME dims exist in dry_run so namd_writer can compute PME grid."""
        if not self.dry_run:
            return

        # If PME dims are missing, use a deterministic default.
        # Values should be reasonable multiples of small primes.
        if (
            state.pme_box0.x is None
            or state.pme_box0.y is None
            or state.pme_box0.z is None
        ):
            state.pme_box0.x, state.pme_box0.y, state.pme_box0.z = 48, 48, 48

        if self.cfg.simulation_type == "GEMC" and (
            self.cfg.only_use_box_0_for_namd_for_gemc is False
        ):
            if (
                state.pme_box1.x is None
                or state.pme_box1.y is None
                or state.pme_box1.z is None
            ):
                state.pme_box1.x, state.pme_box1.y, state.pme_box1.z = (
                    48,
                    48,
                    48,
                )

    # FIFO helpers

    def _runtime_namd_root(self, fifo_resources) -> Path:
        if fifo_resources is None:
            return Path(self.cfg.path_namd_runs)
        return fifo_resources.managed_root / "NAMD"

    def _disk_namd_dir(
        self, fifo_resources, box_number: int, run_no: int
    ) -> Path:
        step_id = format_cycle_id(run_no, 10)
        suffix = "a" if int(box_number) == 0 else "b"
        if fifo_resources is None:
            return Path(self.cfg.path_namd_runs) / f"{step_id}_{suffix}"
        return fifo_resources.disk_dir(box_number)

    # def _stdout_command_kwargs(
    #     self,
    #     *,
    #     runtime_dir: Optional[Path] = None,
    #     disk_dir: Optional[Path] = None,
    #     run_dir: Optional[Path] = None,
    #     fifo_resources=None,
    #     fifo_basename: str = "box0.out.dat",
    # ) -> dict:
    #     if runtime_dir is not None and disk_dir is not None:
    #         return {
    #             "stdout_path": runtime_dir / "out.dat",
    #             "stdout_disk_path": disk_dir / "out.dat",
    #         }

    #     if run_dir is not None:
    #         return {
    #             "stdout_path": persisted_output_path("NAMD", run_dir, "out.dat"),
    #         }

    #     raise TypeError("Unsupported stdout routing arguments for NamdEngine")

    def _stdout_command_kwargs(
        self,
        *,
        runtime_dir: Optional[Path] = None,
        disk_dir: Optional[Path] = None,
        run_dir: Optional[Path] = None,
        fifo_resources=None,
        fifo_basename: str = "box0.out.dat",
    ) -> dict:
        if runtime_dir is not None and disk_dir is not None:
            # Keep managed engine stdout in runtime storage only.
            # Disk mirroring remains available to callers that explicitly
            # request stdout_disk_path through SubprocessRunner.
            return {
                "stdout_path": runtime_dir / "out.dat",
            }

        if run_dir is not None:
            return {
                "stdout_path": persisted_output_path(
                    "NAMD", run_dir, "out.dat"
                ),
            }

        raise TypeError("Unsupported stdout routing arguments for NamdEngine")

    def _get_run0_fft_filename_compat(
        self,
        box_number: int,
        run_root: Optional[Path] = None,
    ):
        try:
            return self.get_run0_fft_filename(box_number, run_root=run_root)
        except TypeError:
            return self.get_run0_fft_filename(box_number)
