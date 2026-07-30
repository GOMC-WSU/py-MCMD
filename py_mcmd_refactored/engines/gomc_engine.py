
import os
import logging
from pathlib import Path
from typing import Optional

from engines.base import Engine as BaseEngine

from engines.gomc.gomc_writer import (
    write_gomc_conf_file,
    GOMCIOPaths,
    GOMCSimParams,
    GOMCStartFiles,
)
from engines.gomc.energy_parse import get_gomc_energy_data
from engines.gomc.energy_metrics import get_gomc_energy_data_kcal_per_mol

from engines.namd.energy_compare import compare_namd_gomc_energies

from py_mcmd_refactored.utils.path import format_cycle_id
from utils.subprocess_runner import Command, SubprocessRunner
from orchestrator.state import RunState
from utils.persisted_file_lists import persisted_output_path

import time

logger = logging.getLogger(__name__)



class GomcEngine(BaseEngine):


    def __init__(self, cfg, engine_type="GOMC", dry_run: bool = False):
        super().__init__(cfg, engine_type, dry_run=dry_run)
        self.dry_run = dry_run

        self.bin_dir = Path(cfg.gomc_bin_directory)
        self.path_template = Path(cfg.path_gomc_template) if cfg.path_gomc_template else None

        cpu_or_gpu = str(cfg.gomc_use_CPU_or_GPU).upper()
        ensemble = str(cfg.simulation_type).upper()

        candidate_names = [
            f"GOMC_{cpu_or_gpu}_{ensemble}",   # legacy-compatible
            f"GOMC_{cpu_or_gpu}",             # fallback, only if your local build uses this name
        ]

        if self.bin_dir.exists():
            found = None
            for name in candidate_names:
                candidate = (self.bin_dir / name).resolve()
                if candidate.exists():
                    found = candidate
                    break

            if found is None:
                raise FileNotFoundError(
                    f"[GOMC] Executable not found in {self.bin_dir}. "
                    f"Tried: {candidate_names}"
                )

            self.exec_path = str(found)
            self.exec_name = found.name
        else:
            if self.dry_run:
                logger.warning("GOMC bin dir %s not found; continuing in dry_run.", self.bin_dir)
                self.exec_path = candidate_names[0]
                self.exec_name = candidate_names[0]
            else:
                raise FileNotFoundError(f"GOMC binary directory {self.bin_dir} does not exist.")

        self.steps_per_run = int(getattr(cfg, "gomc_run_steps", 0))
        self.runner = SubprocessRunner(dry_run=self.dry_run)

    def run(self):
        raise NotImplementedError("Use GomcEngine.run_segment(...) instead.")

    from shutil import which

    def _resolve_gomc_bin_dir(self, cfg) -> Path:
        # 1) explicit config wins
        user_dir = getattr(cfg, "gomc_bin_directory", None)
        if user_dir:
            return Path(user_dir).expanduser().resolve()

        # 2) fallback: sibling GOMC/bin relative to this file, not CWD
        # this file: .../py_mcmd_refactored/engines/gomc_engine.py
        py_root = Path(__file__).resolve().parents[1]     # py_mcmd_refactored/
        repo_root = py_root.parent                        # repo root containing py_mcmd_refactored/
        return (repo_root / "GOMC" / "bin").resolve()
    
    

    def run_steps(self, *, run_dir: Path, cores: int, fifo_resources=None) -> int:
        cmd = Command(
            argv=[str(self.exec_path), f"+p{int(cores)}", "in.conf"],
            cwd=Path(run_dir),
            **self._stdout_command_kwargs(
                run_dir=Path(run_dir),
                fifo_resources=fifo_resources,
            ),
        )
        return self.runner.run_and_wait(cmd)

    
    def _two_box_enabled(self) -> bool:
        # In legacy, box1 energies are parsed for GEMC and GCMC
        return self.cfg.simulation_type in ("GEMC", "GCMC")


    
    def run_segment(self, *, run_no: int, state: RunState, fifo_resources=None) -> dict:
        """Run the full GOMC segment for an odd run_no and update RunState."""

        runtime_gomc_root = self._runtime_gomc_root(fifo_resources)

        if int(run_no) % 2 != 1:
            raise ValueError(f"GOMC segment must be called for odd run_no; got run_no={run_no}")

        box0 = 0
        box1 = 1
        two_box = self._two_box_enabled()

        previous_gomc_dir = str(state.gomc_dir) if state.gomc_dir is not None else "NA"

        python_file_directory = Path.cwd()

        io = GOMCIOPaths(
            python_file_directory=python_file_directory,
            path_gomc_runs=runtime_gomc_root,
            path_gomc_template=Path(self.cfg.path_gomc_template),
            namd_box_0_dir=Path(state.namd_box0_dir),
            namd_box_1_dir=Path(state.namd_box1_dir) if getattr(state, "namd_box1_dir", None) else None,
            previous_gomc_dir=Path(state.gomc_dir) if getattr(state, "gomc_dir", None) else None,
        )

        sim = GOMCSimParams(
            gomc_run_steps=int(self.cfg.gomc_run_steps),
            gomc_rst_coor_ckpoint_steps=int(self.cfg.gomc_rst_coor_ckpoint_steps),
            gomc_console_blkavg_hist_steps=int(self.cfg.gomc_console_blkavg_hist_steps),
            gomc_hist_sample_steps=int(self.cfg.gomc_hist_sample_steps),
            simulation_temp_k=float(self.cfg.simulation_temp_k),
            simulation_pressure_bar=float(self.cfg.simulation_pressure_bar),
        )

        starts = GOMCStartFiles(
            starting_pdb_box_0_file=Path(self.cfg.starting_pdb_box_0_file),
            starting_pdb_box_1_file=Path(self.cfg.starting_pdb_box_1_file),
            starting_psf_box_0_file=Path(self.cfg.starting_psf_box_0_file),
            starting_psf_box_1_file=Path(self.cfg.starting_psf_box_1_file),
        )

        # 1) Write GOMC config
        gomc_newdir = write_gomc_conf_file(
            cfg=self.cfg,
            io=io,
            run_no=int(run_no),
            sim=sim,
            starts=starts,
            dry_run=self.dry_run,
        )

        
 

        state.gomc_dir = Path(gomc_newdir)

        # 2) Execute GOMC (stdout -> out.dat)
        

        disk_gomc_dir = self._disk_gomc_dir(fifo_resources, run_no)
        disk_gomc_dir.mkdir(parents=True, exist_ok=True)

        cmd = Command(
            argv=[str(self.exec_path), f"+p{int(self.cfg.total_no_cores)}", "in.conf"],
            cwd=Path(gomc_newdir),
            **self._stdout_command_kwargs(
                runtime_dir=Path(gomc_newdir),
                disk_dir=disk_gomc_dir,
            ),
        )


        t0 = time.perf_counter()
        h = self.runner.start(cmd)
        rc = self.runner.wait(h)

        gomc_cycle_time_s = time.perf_counter() - t0

        state.timings.gomc_cycle_time_s = round(gomc_cycle_time_s, 6)
        if self.dry_run:
            # Create restart files that the next NAMD segment expects from the previous GOMC run.
            self._ensure_dry_run_gomc_restart_files(Path(gomc_newdir), box_number=0)

            # If the workflow uses two boxes, also create BOX_1 restart files.
            if self._two_box_enabled():
                self._ensure_dry_run_gomc_restart_files(Path(gomc_newdir), box_number=1)
                
        if rc != 0 and not self.dry_run:
            raise RuntimeError(f"GOMC failed (rc={rc}) for run_no={run_no} in {gomc_newdir}")

        # 3) Parse energies -> cache in state
        try:
            lines = (Path(gomc_newdir) / "out.dat").read_text(errors="ignore").splitlines(True)

            df0 = get_gomc_energy_data(self.cfg, lines, box0)
            (
                _e_elect0,
                _e_elect0_i,
                _e_elect0_f,
                _e_pot0,
                pot0_i,
                pot0_f,
                _e_lrc0,
                _e_lrc0_i,
                _e_lrc0_f,
                _e_vpe0,
                vpe0_i,
                vpe0_f,
            ) = get_gomc_energy_data_kcal_per_mol(df0)

            state.energy_box0.gomc_potential_initial = pot0_i
            state.energy_box0.gomc_potential_final = pot0_f
            state.energy_box0.gomc_vdw_plus_elec_initial = vpe0_i
            state.energy_box0.gomc_vdw_plus_elec_final = vpe0_f

            if two_box:
                df1 = get_gomc_energy_data(self.cfg,lines, box1)
                (
                    _e_elect1,
                    _e_elect1_i,
                    _e_elect1_f,
                    _e_pot1,
                    pot1_i,
                    pot1_f,
                    _e_lrc1,
                    _e_lrc1_i,
                    _e_lrc1_f,
                    _e_vpe1,
                    vpe1_i,
                    vpe1_f,
                ) = get_gomc_energy_data_kcal_per_mol(df1)

                state.energy_box1.gomc_potential_initial = pot1_i
                state.energy_box1.gomc_potential_final = pot1_f
                state.energy_box1.gomc_vdw_plus_elec_initial = vpe1_i
                state.energy_box1.gomc_vdw_plus_elec_final = vpe1_f

        except Exception as e:
            if self.dry_run:
                logger.warning("[GOMC] Energy parse failed (dry_run): %s", e)
            else:
                raise

        # 4) Continuity check (NAMD -> GOMC) when values exist
        e0 = state.energy_box0
        if (
            (e0.namd_potential_final is not None)
            and (e0.gomc_potential_initial is not None)
            and (e0.namd_vdw_plus_elec_final is not None)
            and (e0.gomc_vdw_plus_elec_initial is not None)
        ):
            compare_namd_gomc_energies(
                self.cfg,
                e0.namd_potential_final,
                e0.gomc_potential_initial,
                e0.namd_vdw_plus_elec_final,
                e0.gomc_vdw_plus_elec_initial,
                run_no,
                0,
            )

        if two_box:
            e1 = state.energy_box1
            if (
                (e1.namd_potential_final is not None)
                and (e1.gomc_potential_initial is not None)
                and (e1.namd_vdw_plus_elec_final is not None)
                and (e1.gomc_vdw_plus_elec_initial is not None)
            ):
                compare_namd_gomc_energies(
                    self.cfg,
                    e1.namd_potential_final,
                    e1.gomc_potential_initial,
                    e1.namd_vdw_plus_elec_final,
                    e1.gomc_vdw_plus_elec_initial,
                    run_no,
                    1,
                )

        # 5) Update step counter
        state.current_step += int(self.cfg.gomc_run_steps)

        return {
            "run_no": int(run_no),
            "rc": int(rc),
            "gomc_dir": str(gomc_newdir),
            "previous_gomc_dir": previous_gomc_dir,
        }
    
    def _ensure_dry_run_gomc_restart_files(self, gomc_dir: Path, box_number: int) -> None:
        """Create minimal GOMC restart files required by the next NAMD segment in dry_run."""
        gomc_dir = Path(gomc_dir)
        gomc_dir.mkdir(parents=True, exist_ok=True)

        pdb_name = f"Output_data_BOX_{box_number}_restart.pdb"
        psf_name = f"Output_data_BOX_{box_number}_restart.psf"

        pdb_path = gomc_dir / pdb_name
        psf_path = gomc_dir / psf_name

        # Prefer copying real starting files if they exist (more realistic), else create minimal placeholders.
        if box_number == 0:
            start_pdb = Path(self.cfg.starting_pdb_box_0_file)
            start_psf = Path(self.cfg.starting_psf_box_0_file)
            dims = self.cfg.set_dims_box_0_list
            angs = self.cfg.set_angle_box_0_list
        else:
            start_pdb = Path(self.cfg.starting_pdb_box_1_file)
            start_psf = Path(self.cfg.starting_psf_box_1_file)
            dims = self.cfg.set_dims_box_1_list
            angs = self.cfg.set_angle_box_1_list

        if not pdb_path.exists():
            if start_pdb.exists():
                pdb_path.write_text(start_pdb.read_text(), encoding="utf-8")
            else:
                # Minimal PDB with CRYST1 so downstream code can read box dimensions if needed
                x, y, z = [float(v) for v in dims]
                a, b, c = [float(v) for v in angs]
                pdb_path.write_text(
                    f"CRYST1{x:9.3f}{y:9.3f}{z:9.3f}{a:7.2f}{b:7.2f}{c:7.2f} P 1           1\nEND\n",
                    encoding="utf-8",
                )

        if not psf_path.exists():
            if start_psf.exists():
                psf_path.write_text(start_psf.read_text(), encoding="utf-8")
            else:
                # Minimal placeholder; typically the writer just references this path
                psf_path.write_text("PSF\n", encoding="utf-8")

    #FIFO helper


    def _runtime_gomc_root(self, fifo_resources) -> Path:
        if fifo_resources is None:
            return Path(self.cfg.path_gomc_runs)
        return fifo_resources.managed_root / "GOMC"

    def _disk_gomc_dir(self, fifo_resources, run_no: int) -> Path:
        step_id = format_cycle_id(run_no, 10)
        if fifo_resources is None:
            return Path(self.cfg.path_gomc_runs) / step_id
        return fifo_resources.disk_dir()

    
    # def _stdout_command_kwargs(
    #     self,
    #     *,
    #     runtime_dir: Optional[Path] = None,
    #     disk_dir: Optional[Path] = None,
    #     run_dir: Optional[Path] = None,
    #     fifo_resources=None,
    # ) -> dict:
    #     if runtime_dir is not None and disk_dir is not None:
    #         return {
    #             "stdout_path": runtime_dir / "out.dat",
    #             "stdout_disk_path": disk_dir / "out.dat",
    #         }

    #     if run_dir is not None:
    #         return {
    #             "stdout_path": persisted_output_path("GOMC", run_dir, "out.dat"),
    #         }

    #     raise TypeError("Unsupported stdout routing arguments for GomcEngine")

    def _stdout_command_kwargs(
        self,
        *,
        runtime_dir: Optional[Path] = None,
        disk_dir: Optional[Path] = None,
        run_dir: Optional[Path] = None,
        fifo_resources=None,
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
                "stdout_path": persisted_output_path("GOMC", run_dir, "out.dat"),
            }

        raise TypeError("Unsupported stdout routing arguments for GomcEngine")