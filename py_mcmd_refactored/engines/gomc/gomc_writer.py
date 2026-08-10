from __future__ import annotations

import logging
import os
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Tuple

from py_mcmd_refactored.config.models import SimulationConfig
from py_mcmd_refactored.utils.path import format_cycle_id


def _update_pdb_with_namd_coor(
    pdb_in_path: Path, coor_bin_path: Path, pdb_out_path: Path
) -> bool:
    """Read big-endian NAMD .coor file and overwrite coordinates of ATOM/HETATM lines in a new PDB."""
    try:
        with open(coor_bin_path, "rb") as f:
            header = f.read(4)
            if not header:
                raise ValueError(f"Empty NAMD coor file: {coor_bin_path}")
            num_atoms = struct.unpack(">i", header)[0]
            coors = []
            for _ in range(num_atoms):
                data = f.read(24)
                if len(data) < 24:
                    raise ValueError("Unexpected EOF in NAMD coor file")
                x, y, z = struct.unpack(">ddd", data)
                coors.append((x, y, z))
    except Exception as e:
        log.warning(
            "[GOMC] Could not parse NAMD binary coordinates: %s. "
            "Falling back to starting PDB coordinates.",
            e,
        )
        return False

    atom_idx = 0
    with open(pdb_in_path, "r") as f_in, open(pdb_out_path, "w") as f_out:
        for line in f_in:
            if line.startswith("ATOM  ") or line.startswith("HETATM"):
                if atom_idx < len(coors):
                    x, y, z = coors[atom_idx]
                    x_str = f"{x:8.3f}"
                    y_str = f"{y:8.3f}"
                    z_str = f"{z:8.3f}"
                    line = line[:30] + x_str + y_str + z_str + line[54:]
                    atom_idx += 1
            f_out.write(line)

    return True


log = logging.getLogger(__name__)

# ----------------------------- DTOs -----------------------------


@dataclass(frozen=True)
class GOMCStartFiles:
    starting_pdb_box_0_file: Path
    starting_pdb_box_1_file: Path
    starting_psf_box_0_file: Path
    starting_psf_box_1_file: Path


@dataclass(frozen=True)
class GOMCSimParams:
    gomc_run_steps: int
    gomc_rst_coor_ckpoint_steps: int
    gomc_console_blkavg_hist_steps: int
    gomc_hist_sample_steps: int
    simulation_temp_k: float
    simulation_pressure_bar: float


@dataclass(frozen=True)
class GOMCIOPaths:
    python_file_directory: Path
    path_gomc_runs: Path
    path_gomc_template: Path
    namd_box_0_dir: Path
    namd_box_1_dir: Optional[Path]
    previous_gomc_dir: Optional[Path]


# ----------------------------- Helpers -----------------------------


def _load_text(p: Path) -> str:
    return p.read_text()


def _save_text(p: Path, s: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s)


def _rel(p: Path, base: Path) -> str:
    """Return POSIX relative path from base to p (works across siblings)."""
    return os.path.relpath(str(p), start=str(base)).replace("\\", "/")


def _build_parameters_block(
    params_files: Iterable[Path],
    relative_to: Path,
    project_root: Path,
) -> str:
    """
    Legacy-compatible behavior:
    every parameter file path written into in.conf must be relative
    to the GOMC run directory, not left as the original JSON string.
    """
    lines = []
    for p in params_files:
        p = Path(p)

        # Legacy semantics:
        # - absolute input path -> keep absolute target, then relativize to run dir
        # - relative input path -> interpret relative to project root, then relativize
        full_path = p if p.is_absolute() else (project_root / p)

        rel = _rel(full_path.resolve(), relative_to.resolve())
        lines.append(f"Parameters \t {rel}\n")

    return "".join(lines)


# def _strip_box1_binary_restart_lines(template_text: str) -> str:
#     out = []
#     for line in template_text.splitlines(keepends=True):
#         toks = line.split()
#         if len(toks) >= 2 and toks[0] in {"binCoordinates", "extendedSystem", "binVelocities"} and toks[1] == "1":
#             continue
#         out.append(line)
#     return "".join(out)
def _strip_box1_binary_restart_lines(template_text: str) -> str:
    """Remove all box-1 directives when box 1 is not used."""
    out = []
    for line in template_text.splitlines(keepends=True):
        toks = line.split()
        if not toks:
            out.append(line)
            continue

        if (
            len(toks) >= 2
            and toks[0]
            in {
                "binCoordinates",
                "extendedSystem",
                "binVelocities",
            }
            and toks[1] == "1"
        ):
            continue

        if (
            len(toks) >= 2
            and toks[0] in {"Coordinates", "Structure"}
            and toks[1] == "1"
        ):
            continue

        if (
            len(toks) >= 2
            and toks[0]
            in {
                "CellBasisVector1",
                "CellBasisVector2",
                "CellBasisVector3",
            }
            and toks[1] == "1"
        ):
            continue

        out.append(line)

    return "".join(out)


def _strip_box0_binary_restart_lines(template_text: str) -> str:
    """Remove box-0 binary restart directives while retaining PDB/PSF lines."""
    out = []
    for line in template_text.splitlines(keepends=True):
        toks = line.split()
        if (
            len(toks) >= 2
            and toks[0]
            in {
                "binCoordinates",
                "extendedSystem",
                "binVelocities",
            }
            and toks[1] == "0"
        ):
            continue

        out.append(line)

    return "".join(out)


def _strip_all_binary_restart_lines(template_text: str) -> str:
    """Remove binary restart directives for both boxes while keeping PDB/PSF lines."""
    out = _strip_box0_binary_restart_lines(template_text)
    kept_lines = []

    for line in out.splitlines(keepends=True):
        toks = line.split()
        if (
            len(toks) >= 2
            and toks[0]
            in {
                "binCoordinates",
                "extendedSystem",
                "binVelocities",
            }
            and toks[1] == "1"
        ):
            continue

        kept_lines.append(line)

    return "".join(kept_lines)


def _strip_box1_velocity_restart_line(template_text: str) -> str:
    """Remove the box-1 binary velocity directive while retaining other restart data."""
    out = []
    for line in template_text.splitlines(keepends=True):
        toks = line.split()
        if len(toks) >= 2 and toks[0] == "binVelocities" and toks[1] == "1":
            continue

        out.append(line)

    return "".join(out)


def _read_last_xsc_dims(xsc_path: Path) -> Tuple[float, float, float]:
    """
    Read last line of XSC. Support both layouts:
      primary: [1]=Lx, [5]=Ly, [9]=Lz
      fallback: [1]=Lx, [4]=Ly, [7]=Lz
    """
    lines = xsc_path.read_text().splitlines()
    if not lines:
        raise ValueError(f"Empty XSC: {xsc_path}")
    toks = lines[-1].split()

    def _try(idx):
        try:
            return float(toks[idx])
        except (IndexError, ValueError):
            return None

    lx = _try(1)
    ly = _try(5)
    lz = _try(9)
    if (
        lx is not None
        and ly is not None
        and lz is not None
        and (ly != 0.0 or lz != 0.0)
    ):
        return lx, ly, lz

    ly_fb = _try(4)
    lz_fb = _try(7)
    if lx is not None and ly_fb is not None and lz_fb is not None:
        return lx, ly_fb, lz_fb

    raise ValueError(f"Malformed XSC line in {xsc_path}: {lines[-1]!r}")


def _read_pdb_cryst1_dims(pdb_path: Path) -> Tuple[float, float, float]:
    for line in pdb_path.read_text().splitlines():
        if line.startswith("CRYST1"):
            toks = line.split()
            try:
                a = float(toks[1])
                b = float(toks[2])
                c = float(toks[3])
            except (IndexError, ValueError) as e:
                raise ValueError(
                    f"Malformed CRYST1 in {pdb_path}: {line!r}"
                ) from e
            return a, b, c
    raise ValueError(f"No CRYST1 record in {pdb_path}")


def _override_dim(read_val: float, override: Optional[float]) -> float:
    return float(override) if override is not None else float(read_val)


def _compute_adjustment_blocks(run_steps: int) -> Tuple[int, int]:
    set_max_steps_equib_adj = 10 * (10**6)
    if run_steps >= set_max_steps_equib_adj:
        adj_steps = 1000 if (run_steps / 10) >= 1000 else int(run_steps / 10)
        equil_steps = 0
        return equil_steps, adj_steps
    elif int(run_steps / 10) > 0:
        equil_steps = int(run_steps / 10)
        adj_steps = int(run_steps / 10)
        if (run_steps / 10) >= 1000:
            adj_steps = 1000
        return equil_steps, adj_steps
    else:
        return 1, 1


# ----------------------------- Public API -----------------------------


def write_gomc_conf_file(
    cfg: SimulationConfig,
    io: GOMCIOPaths,
    run_no: int,
    sim: GOMCSimParams,
    starts: GOMCStartFiles,
    dry_run: bool = False,
) -> Path:
    python_dir = Path(io.python_file_directory)
    run_id = format_cycle_id(run_no, width=10)
    gomc_newdir = python_dir / io.path_gomc_runs / run_id
    gomc_newdir.mkdir(parents=True, exist_ok=True)

    tpl_path = python_dir / io.path_gomc_template
    template = _load_text(tpl_path)

    params_files = getattr(cfg, "starting_ff_file_list_gomc", []) or []
    # params_block = _build_parameters_block(params_files, relative_to=gomc_newdir)
    params_block = _build_parameters_block(
        params_files,
        relative_to=gomc_newdir,
        project_root=python_dir,
    )
    out = template.replace("all_parameter_files", params_block)

    # Box 0: always from NAMD previous step
    prev_namd0_rel = _rel(io.namd_box_0_dir, gomc_newdir)
    out = out.replace(
        "coor_box_0_file", f"{prev_namd0_rel}/namdOut.restart.coor"
    )
    out = out.replace("xsc_box_0_file", f"{prev_namd0_rel}/namdOut.restart.xsc")
    out = out.replace("vel_box_0_file", f"{prev_namd0_rel}/namdOut.restart.vel")

    # PDB/PSF for box 0: fresh vs restart
    if io.previous_gomc_dir is None:
        pdb0_path = python_dir / starts.starting_pdb_box_0_file
        if io.namd_box_0_dir is not None:
            namd_coor = io.namd_box_0_dir / "namdOut.restart.coor"
            if namd_coor.exists():
                min_pdb_path = gomc_newdir / "NAMD_minimized_box_0.pdb"
                success = _update_pdb_with_namd_coor(
                    pdb0_path, namd_coor, min_pdb_path
                )
                if success:
                    pdb0_path = min_pdb_path

        pdb0_rel = _rel(pdb0_path, gomc_newdir)
        psf0_rel = _rel(
            python_dir / starts.starting_psf_box_0_file, gomc_newdir
        )
        out = out.replace("pdb_file_box_0_file", pdb0_rel)
        out = out.replace("psf_file_box_0_file", psf0_rel)
        out = out.replace(
            "Restart_Checkpoint_file", f"false {'Output_data_restart.chk'}"
        )
    else:
        prev_gomc_rel = _rel(io.previous_gomc_dir, gomc_newdir)
        out = out.replace(
            "pdb_file_box_0_file",
            f"{prev_gomc_rel}/Output_data_BOX_0_restart.pdb",
        )
        out = out.replace(
            "psf_file_box_0_file",
            f"{prev_gomc_rel}/Output_data_BOX_0_restart.psf",
        )

    # Box 0 dims from xsc
    xsc0 = io.namd_box_0_dir / "namdOut.restart.xsc"
    lx0, ly0, lz0 = _read_last_xsc_dims(xsc0)
    out = out.replace("x_dim_box_0", str(lx0))
    out = out.replace("y_dim_box_0", str(ly0))
    out = out.replace("z_dim_box_0", str(lz0))

    # # Box 1 branches
    # if cfg.simulation_type in {"GEMC", "GCMC"}:
    #     if (cfg.simulation_type == "GCMC") or (cfg.simulation_type == "GEMC" and cfg.only_use_box_0_for_namd_for_gemc):
    #         if io.previous_gomc_dir is None:
    #             out = _strip_box1_binary_restart_lines(out)
    #             pdb1_rel = _rel(python_dir / starts.starting_pdb_box_1_file, gomc_newdir)
    #             psf1_rel = _rel(python_dir / starts.starting_psf_box_1_file, gomc_newdir)
    #             out = out.replace("pdb_file_box_1_file", pdb1_rel)
    #             out = out.replace("psf_file_box_1_file", psf1_rel)

    #             a1, b1, c1 = _read_pdb_cryst1_dims(python_dir / starts.starting_pdb_box_1_file)
    #             set_dims = getattr(cfg, "set_dims_box_1_list", [None, None, None]) or [None, None, None]
    #             x1 = _override_dim(a1, set_dims[0])
    #             y1 = _override_dim(b1, set_dims[1])
    #             z1 = _override_dim(c1, set_dims[2])
    #             out = out.replace("x_dim_box_1", str(x1))
    #             out = out.replace("y_dim_box_1", str(y1))
    #             out = out.replace("z_dim_box_1", str(z1))
    #         else:
    #             prev_gomc_rel = _rel(io.previous_gomc_dir, gomc_newdir)
    #             out = out.replace("coor_box_1_file", f"{prev_gomc_rel}/Output_data_BOX_1_restart.coor")
    #             out = out.replace("xsc_box_1_file",  f"{prev_gomc_rel}/Output_data_BOX_1_restart.xsc")
    #             out = out.replace("vel_box_1_file",  f"{prev_gomc_rel}/Output_data_BOX_1_restart.vel")

    #             xsc1_prev = io.previous_gomc_dir / "Output_data_BOX_1_restart.xsc"
    #             lx1, ly1, lz1 = _read_last_xsc_dims(xsc1_prev)
    #             out = out.replace("x_dim_box_1", str(lx1))
    #             out = out.replace("y_dim_box_1", str(ly1))
    #             out = out.replace("z_dim_box_1", str(lz1))
    #     else:
    #         assert io.namd_box_1_dir is not None, "namd_box_1_dir is required for GEMC with both boxes."
    #         prev_namd1_rel = _rel(io.namd_box_1_dir, gomc_newdir)
    #         out = out.replace("coor_box_1_file", f"{prev_namd1_rel}/namdOut.restart.coor")
    #         out = out.replace("xsc_box_1_file",  f"{prev_namd1_rel}/namdOut.restart.xsc")
    #         out = out.replace("vel_box_1_file",  f"{prev_namd1_rel}/namdOut.restart.vel")
    #         xsc1 = io.namd_box_1_dir / "namdOut.restart.xsc"
    #         lx1, ly1, lz1 = _read_last_xsc_dims(xsc1)
    #         out = out.replace("x_dim_box_1", str(lx1))
    #         out = out.replace("y_dim_box_1", str(ly1))
    #         out = out.replace("z_dim_box_1", str(lz1))

    # Box 1 branches
    if cfg.simulation_type in {"GEMC", "GCMC"}:
        if (cfg.simulation_type == "GCMC") or (
            cfg.simulation_type == "GEMC"
            and cfg.only_use_box_0_for_namd_for_gemc
        ):
            if io.previous_gomc_dir is None:
                # First-cycle GCMC and one-box GEMC use PDB/PSF inputs and
                # Restart=false, so no binary restart directives are valid.
                out = _strip_all_binary_restart_lines(out)

                pdb1_rel = _rel(
                    python_dir / starts.starting_pdb_box_1_file,
                    gomc_newdir,
                )
                psf1_rel = _rel(
                    python_dir / starts.starting_psf_box_1_file,
                    gomc_newdir,
                )
                out = out.replace(
                    "pdb_file_box_1_file",
                    pdb1_rel,
                )
                out = out.replace(
                    "psf_file_box_1_file",
                    psf1_rel,
                )

                a1, b1, c1 = _read_pdb_cryst1_dims(
                    python_dir / starts.starting_pdb_box_1_file
                )
                set_dims = getattr(
                    cfg,
                    "set_dims_box_1_list",
                    [None, None, None],
                ) or [None, None, None]
                x1 = _override_dim(a1, set_dims[0])
                y1 = _override_dim(b1, set_dims[1])
                z1 = _override_dim(c1, set_dims[2])
                out = out.replace("x_dim_box_1", str(x1))
                out = out.replace("y_dim_box_1", str(y1))
                out = out.replace("z_dim_box_1", str(z1))

            else:
                # GCMC and one-box GEMC do not provide box-1 velocity
                # restart data. Reuse the previous GOMC coordinate,
                # extended-system, PDB, and PSF restart files instead.
                prev_gomc_rel = _rel(
                    io.previous_gomc_dir,
                    gomc_newdir,
                )
                out = out.replace(
                    "coor_box_1_file",
                    (f"{prev_gomc_rel}/" "Output_data_BOX_1_restart.coor"),
                )
                out = out.replace(
                    "xsc_box_1_file",
                    (f"{prev_gomc_rel}/" "Output_data_BOX_1_restart.xsc"),
                )

                out = _strip_box1_velocity_restart_line(out)

                out = out.replace(
                    "pdb_file_box_1_file",
                    (f"{prev_gomc_rel}/" "Output_data_BOX_1_restart.pdb"),
                )
                out = out.replace(
                    "psf_file_box_1_file",
                    (f"{prev_gomc_rel}/" "Output_data_BOX_1_restart.psf"),
                )

                xsc1_prev = (
                    io.previous_gomc_dir / "Output_data_BOX_1_restart.xsc"
                )
                lx1, ly1, lz1 = _read_last_xsc_dims(xsc1_prev)
                out = out.replace("x_dim_box_1", str(lx1))
                out = out.replace("y_dim_box_1", str(ly1))
                out = out.replace("z_dim_box_1", str(lz1))

        else:
            # Two-box GEMC receives binary restart data from both NAMD boxes.
            assert (
                io.namd_box_1_dir is not None
            ), "namd_box_1_dir is required for GEMC with both boxes."

            prev_namd1_rel = _rel(
                io.namd_box_1_dir,
                gomc_newdir,
            )
            out = out.replace(
                "coor_box_1_file",
                f"{prev_namd1_rel}/namdOut.restart.coor",
            )
            out = out.replace(
                "xsc_box_1_file",
                f"{prev_namd1_rel}/namdOut.restart.xsc",
            )
            out = out.replace(
                "vel_box_1_file",
                f"{prev_namd1_rel}/namdOut.restart.vel",
            )

            xsc1 = io.namd_box_1_dir / "namdOut.restart.xsc"
            lx1, ly1, lz1 = _read_last_xsc_dims(xsc1)
            out = out.replace("x_dim_box_1", str(lx1))
            out = out.replace("y_dim_box_1", str(ly1))
            out = out.replace("z_dim_box_1", str(lz1))

            if io.previous_gomc_dir is None:
                pdb1_rel = _rel(
                    python_dir / starts.starting_pdb_box_1_file,
                    gomc_newdir,
                )
                psf1_rel = _rel(
                    python_dir / starts.starting_psf_box_1_file,
                    gomc_newdir,
                )
                out = out.replace(
                    "pdb_file_box_1_file",
                    pdb1_rel,
                )
                out = out.replace(
                    "psf_file_box_1_file",
                    psf1_rel,
                )

            else:
                prev_gomc_rel = _rel(
                    io.previous_gomc_dir,
                    gomc_newdir,
                )
                out = out.replace(
                    "pdb_file_box_1_file",
                    (f"{prev_gomc_rel}/" "Output_data_BOX_1_restart.pdb"),
                )
                out = out.replace(
                    "psf_file_box_1_file",
                    (f"{prev_gomc_rel}/" "Output_data_BOX_1_restart.psf"),
                )

    else:
        out = _strip_box1_binary_restart_lines(out)
    # restart_true_or_false
    if cfg.simulation_type in {"GEMC", "GCMC"}:
        if (cfg.simulation_type == "GCMC" and io.previous_gomc_dir is None) or (
            cfg.simulation_type == "GEMC"
            and cfg.only_use_box_0_for_namd_for_gemc
            and io.previous_gomc_dir is None
        ):
            out = out.replace("restart_true_or_false", "false")
        else:
            out = out.replace("restart_true_or_false", "true")
    else:
        out = out.replace("restart_true_or_false", "true")

    # Steps and thermo
    out = out.replace("GOMC_Run_Steps", str(int(sim.gomc_run_steps)))
    out = out.replace(
        "GOMC_RST_Coor_CKpoint_Steps", str(int(sim.gomc_rst_coor_ckpoint_steps))
    )
    out = out.replace(
        "GOMC_console_BLKavg_Hist_Steps",
        str(int(sim.gomc_console_blkavg_hist_steps)),
    )
    out = out.replace(
        "GOMC_Hist_sample_Steps", str(int(sim.gomc_hist_sample_steps))
    )
    out = out.replace("System_temp_set", str(sim.simulation_temp_k))
    out = out.replace("System_press_set", str(sim.simulation_pressure_bar))

    equil_steps, adj_steps = _compute_adjustment_blocks(sim.gomc_run_steps)
    if "GOMC_Equilb_Steps" in out:
        out = out.replace("GOMC_Equilb_Steps", str(int(equil_steps)))
    if "GOMC_Adj_Steps" in out:
        out = out.replace("GOMC_Adj_Steps", str(int(adj_steps)))

    # GCMC ChemPot/Fugacity
    if cfg.simulation_type == "GCMC":
        mode = getattr(cfg, "GCMC_ChemPot_or_Fugacity", None)
        mapping = getattr(cfg, "GCMC_ChemPot_or_Fugacity_dict", None)
        keys = getattr(cfg, "GCMC_ChemPot_or_Fugacity_dict_keys", None)
        if not mode:
            out = out.replace("mu_ChemPot_K_or_P_Fugacitiy_bar_all", "")
        elif mode in {"ChemPot", "Fugacity"}:
            items = keys if keys else (mapping.keys() if mapping else [])
            lines = []
            for k in items:
                v = mapping[k]
                lines.append(f"{mode} \t {k} \t {v}\n")
            out = out.replace(
                "mu_ChemPot_K_or_P_Fugacitiy_bar_all", "".join(lines)
            )
            log.info(f"GCMC using {mode}: {mapping}")
        else:
            log.warning(
                "Warning: There is in error in the chemical potential settings for GCMC simulation."
            )

    if io.previous_gomc_dir is not None:
        prev_chk = io.previous_gomc_dir / "Output_data_restart.chk"

        if prev_chk.exists():
            prev_chk_rel = _rel(prev_chk, gomc_newdir)
            out = out.replace(
                "Restart_Checkpoint_file",
                f"true {prev_chk_rel}",
            )
        elif dry_run:
            log.warning(
                "[GOMC] Missing restart checkpoint in dry_run; "
                "writing checkpoint-disabled config instead: %s",
                prev_chk,
            )
            out = out.replace(
                "Restart_Checkpoint_file",
                "false Output_data_restart.chk",
            )
        else:
            raise FileNotFoundError(
                f"Missing GOMC restart checkpoint: {prev_chk}"
            )
    else:
        if "Restart_Checkpoint_file" in out:
            out = out.replace(
                "Restart_Checkpoint_file",
                "false Output_data_restart.chk",
            )

    out_path = gomc_newdir / "in.conf"
    _save_text(out_path, out)
    log.info(f"[GOMC] Wrote config: {out_path}")
    return gomc_newdir
