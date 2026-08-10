# py-MCMD
# Author: Haydar Mehryar
# Copyright (c) 2025
# SPDX-License-Identifier: MIT
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple

log = logging.getLogger(__name__)
starting_ff_file_list_namd = []
check_for_pdb_dims_and_override = None
simulation_type = "NVT"
log_template_file = None


# --- Step 1. validate_box_number ------------------------------------------------
def _validate_box_number(box_number: int) -> None:
    """Ensure box_number is an int in {0,1}."""
    if not isinstance(box_number, int) or box_number not in (0, 1):
        raise ValueError("box_number must be integer 0 or 1")


# --- Step 2. zeros prefix + run dir path ----------------------------------------
from utils.path import format_cycle_id  # zero-prefix helper from your utils


def _compute_namd_box_dir(
    python_file_directory: Path,
    path_namd_runs: Path | str,
    run_no: int,
    box_number: int,
    *,
    width: int = 10,  # match utils.path default
) -> Path:
    """
    Returns .../<path_namd_runs>/<cycle_id>_a  (for box 0)
            or .../<path_namd_runs>/<cycle_id>_b  (for box 1)
    where cycle_id = format_cycle_id(run_no, width)
    """
    _validate_box_number(box_number)
    suffix = "a" if box_number == 0 else "b"
    cycle_id = format_cycle_id(run_no, width)
    return (
        Path(python_file_directory)
        / Path(path_namd_runs)
        / f"{cycle_id}_{suffix}"
    )


# --- Step 3. load template safely (resolve + read) ------------------------------
from pathlib import Path


def _resolve_under(base: Path, maybe_relative: Path | str) -> Path:
    """
    If `maybe_relative` is absolute, return as Path.
    Otherwise, return `base / maybe_relative`.
    """
    p = Path(maybe_relative)
    return p if p.is_absolute() else (Path(base) / p)


def _load_template_text(
    python_file_directory: Path | str,
    path_namd_template: Path | str,
    *,
    encoding: str = "utf-8",
) -> str:
    """
    Resolve the template path relative to `python_file_directory` (if needed)
    and return its non-empty text. Raises if missing or empty.
    """
    tpl_path = _resolve_under(Path(python_file_directory), path_namd_template)
    if not tpl_path.is_file():
        raise FileNotFoundError(f"NAMD template not found: {tpl_path}")
    data = tpl_path.read_text(encoding=encoding)
    if not data.strip():
        raise ValueError(f"NAMD template is empty: {tpl_path}")
    return data


import os

# --- Step 4. parameter files block (relative to run/box dir) --------------------
from pathlib import Path
from typing import Iterable


def _build_parameter_files_block(
    ff_files: Iterable[Path | str] | None,
    rel_to_dir: Path,
) -> str:
    """
    Build the NAMD 'parameters' lines, each path relative to `rel_to_dir`.

    Example line:
        parameters \t path/to/file.prm

    Returns a single string with trailing newlines preserved. If `ff_files`
    is None or empty, returns "".
    """
    if not ff_files:
        return ""

    lines: list[str] = []
    for f in ff_files:
        # compute relative path to the target run/box directory
        rel = os.path.relpath(str(f), str(rel_to_dir))
        rel_posix = Path(rel).as_posix()  # normalize separators
        lines.append(f"parameters \t {rel_posix}\n")
    return "".join(lines)


import os
import struct

# --- Step 5. compute run paths + read PDB lines (fresh vs restart) --------------
from pathlib import Path
from typing import Dict, Iterable, Tuple


def _read_cryst1_lines(pdb_path: Path) -> list:
    """Read PDB file only until the CRYST1 line, then stop.

    _parse_cryst1() only needs the CRYST1 record -- for large systems
    (N=1000+) reading the entire PDB file on every cycle adds measurable
    overhead. Stopping at CRYST1 cuts the read to typically the first
    1-2 lines of the file.
    """
    lines = []
    with open(pdb_path, "r") as f:
        for line in f:
            lines.append(line)
            if line.startswith("CRYST1"):
                break
    return lines


def _vel_atom_count_matches_psf(vel_path: Path, psf_path: Path) -> bool:
    """Return True only if both files exist AND have the same atom count.

    For GEMC simulations, swap moves change the molecule count in each box
    every cycle. If the .vel file atom count doesn't match the restart PSF,
    using it would cause:
        FATAL ERROR: Incorrect atom count in binary file
    This check prevents that crash by falling back to Bool_restart=false
    (NAMD regenerates velocities from temperature) whenever the counts differ.
    """
    if not vel_path.exists() or not psf_path.exists():
        return False
    try:
        with open(vel_path, "rb") as vf:
            vel_natom = struct.unpack("<i", vf.read(4))[0]
        with open(psf_path) as pf:
            for line in pf:
                if "!NATOM" in line:
                    psf_natom = int(line.split()[0])
                    break
            else:
                return False
        return vel_natom == psf_natom
    except Exception:
        return False


def _compute_run_paths_and_read_pdb_lines(
    python_file_directory: Path | str,
    gomc_newdir: Path | str,
    namd_box_x_newdir: Path,
    run_no: int,
    box_number: int,
    starting_pdb_box_x_file: Path | str,
    starting_psf_box_x_file: Path | str,
) -> Tuple[Dict[str, str], Iterable[str]]:
    """
    Build placeholder replacements and load the PDB lines used to parse CRYST1.

    Returns:
      (replacements: dict[str,str], pdb_lines: list[str])

    Keys in replacements:
      - pdb_box_file, psf_box_file, coor_file, xsc_file, vel_file, Bool_restart
    """
    python_file_directory = Path(python_file_directory)
    gomc_newdir = Path(gomc_newdir)

    if run_no != 0:
        # Restart from GOMC. Use the full binary restart only when GOMC
        # produced a velocity restart file AND its atom count matches the
        # restart PSF. For GEMC, swap moves can change the molecule count
        # each cycle, making the .vel atom count stale -- using a mismatched
        # .vel causes "FATAL ERROR: Incorrect atom count in binary file".
        gomc_rel = os.path.relpath(
            str(gomc_newdir),
            str(namd_box_x_newdir),
        )
        pdb_abs = gomc_newdir / f"Output_data_BOX_{box_number}_restart.pdb"
        psf_abs = gomc_newdir / f"Output_data_BOX_{box_number}_restart.psf"
        vel_abs = gomc_newdir / f"Output_data_BOX_{box_number}_restart.vel"

        if _vel_atom_count_matches_psf(vel_abs, psf_abs):
            # Full binary restart: positions, box dims, and velocities all
            # come from GOMC. Atom count validated -- safe to use .vel.
            replacements = {
                "pdb_box_file": (
                    f"{gomc_rel}/" f"Output_data_BOX_{box_number}_restart.pdb"
                ),
                "psf_box_file": (
                    f"{gomc_rel}/" f"Output_data_BOX_{box_number}_restart.psf"
                ),
                "coor_file": (
                    f"{gomc_rel}/" f"Output_data_BOX_{box_number}_restart.coor"
                ),
                "xsc_file": (
                    f"{gomc_rel}/" f"Output_data_BOX_{box_number}_restart.xsc"
                ),
                "vel_file": (
                    f"{gomc_rel}/" f"Output_data_BOX_{box_number}_restart.vel"
                ),
                "Bool_restart": "true",
            }
        else:
            # .vel missing, or atom count changed (GEMC swap moved molecules).
            # Use restart PDB/PSF for coordinates and topology; let NAMD
            # regenerate velocities from the configured temperature.
            pdb_rel = os.path.relpath(
                str(pdb_abs),
                str(namd_box_x_newdir),
            )
            psf_rel = os.path.relpath(
                str(psf_abs),
                str(namd_box_x_newdir),
            )

            replacements = {
                "pdb_box_file": pdb_rel,
                "psf_box_file": psf_rel,
                "coor_file": "NA",
                "xsc_file": "NA",
                "vel_file": "NA",
                "Bool_restart": "false",
            }

        pdb_lines = _read_cryst1_lines(pdb_abs)

    else:
        # Fresh run: use starting pdb/psf (resolved under python_file_directory)
        pdb_abs = python_file_directory / starting_pdb_box_x_file
        psf_abs = python_file_directory / starting_psf_box_x_file
        pdb_rel = os.path.relpath(
            str(pdb_abs),
            str(namd_box_x_newdir),
        )
        psf_rel = os.path.relpath(
            str(psf_abs),
            str(namd_box_x_newdir),
        )
        replacements = {
            "pdb_box_file": pdb_rel,
            "psf_box_file": psf_rel,
            "coor_file": "NA",
            "xsc_file": "NA",
            "vel_file": "NA",
            "Bool_restart": "false",
        }
        pdb_lines = _read_cryst1_lines(pdb_abs)

    return replacements, pdb_lines


# --- Step 6. parse CRYST1 line (robust to fixed-width or whitespace) -----------
from typing import Iterable, Optional, Tuple


def _parse_cryst1(lines: Iterable[str]) -> Tuple[
    Optional[float],
    Optional[float],
    Optional[float],
    Optional[float],
    Optional[float],
    Optional[float],
]:
    """
    Parse a PDB CRYST1 record for (a, b, c, alpha, beta, gamma).
    Supports both fixed-width PDB columns and whitespace-separated variants.
    Returns (None, ... ) if no CRYST1 record is found.
    """
    for line in lines:
        if line.startswith("CRYST1") or "CRYST1" in line:
            # Try fixed-width per PDB format first
            try:
                # Columns (1-based PDB):
                # a:  7-15, b: 16-24, c: 25-33, alpha: 34-40, beta: 41-47, gamma: 48-54
                a = float(line[6:15])
                b = float(line[15:24])
                c = float(line[24:33])
                alpha = float(line[33:40])
                beta = float(line[40:47])
                gamma = float(line[47:54])
                return a, b, c, alpha, beta, gamma
            except Exception:
                # Fallback to whitespace-split
                parts = line.split()
                if len(parts) >= 7 and parts[0] == "CRYST1":
                    a = float(parts[1])
                    b = float(parts[2])
                    c = float(parts[3])
                    alpha = float(parts[4])
                    beta = float(parts[5])
                    gamma = float(parts[6])
                    return a, b, c, alpha, beta, gamma
    return None, None, None, None, None, None


# --- Step 7. dimension override wrapper -----------------------------------------
from typing import Callable, Optional


def _override_dim(
    checker: Optional[Callable[..., float]],
    axis: str,
    run_no: int,
    read_dim: Optional[float],
    set_dim: Optional[float],
) -> float:
    """
    Choose the dimension to use:
      1) If `checker` provided, defer to it:
         checker(axis, run_no, read_dim, set_dim=set_dim, only_on_run_no=0)
      2) Else prefer `set_dim`, else `read_dim`.
      3) Raise if neither is available.
    """
    if callable(checker):
        return float(
            checker(axis, run_no, read_dim, set_dim=set_dim, only_on_run_no=0)
        )
    if set_dim is not None:
        return float(set_dim)
    if read_dim is not None:
        return float(read_dim)
    raise ValueError(
        f"Unable to determine {axis}-dimension (no PDB value and no override)."
    )


# --- Step 8. angles validation (orthogonality on run 0) -------------------------
from typing import Optional


def _validate_angles(
    run_no: int,
    read_alpha: Optional[float],
    read_beta: Optional[float],
    read_gamma: Optional[float],
    set_alpha: Optional[float],
    set_beta: Optional[float],
    set_gamma: Optional[float],
) -> None:
    """
    Enforce orthogonal box angles (== 90°) on the initial run (run_no == 0).
    If any provided or read angle is not 90 on run 0, raise ValueError.
    On restart runs (run_no != 0) no validation is enforced (legacy behavior).
    """
    if run_no != 0:
        return

    violations = []
    if (read_alpha is not None) and (read_alpha != 90):
        violations.append(f"read_angle_alpha_PDB={read_alpha}")
    if (read_beta is not None) and (read_beta != 90):
        violations.append(f"read_angle_beta_PDB={read_beta}")
    if (read_gamma is not None) and (read_gamma != 90):
        violations.append(f"read_angle_gamma_PDB={read_gamma}")

    if (set_alpha is not None) and (set_alpha != 90):
        violations.append(f"set_angle_alpha={set_alpha}")
    if (set_beta is not None) and (set_beta != 90):
        violations.append(f"set_angle_beta={set_beta}")
    if (set_gamma is not None) and (set_gamma != 90):
        violations.append(f"set_angle_gamma={set_gamma}")

    if violations:
        raise ValueError(
            "Non-orthogonal box angles are not allowed on run 0: "
            + ", ".join(violations)
        )


# --- Step 9. PME grid dimension computation ------------------------------------
from typing import Optional, Tuple


def _compute_pme_grid_dims(
    run_no: int,
    used_x: float,
    used_y: float,
    used_z: float,
    given_x: int,
    given_y: int,
    given_z: int,
    fft_add_namd_ang_to_box_dim: int,
    simulation_type: Optional[str],
) -> Tuple[int, int, int]:
    """
    For restart runs (run_no != 0): use the provided PME grid sizes (given_*).

    For initial runs (run_no == 0):
      - Start from the used box dims (used_*) plus fft_add_namd_ang_to_box_dim.
      - Scale by 1.3 for 'GEMC' or 'NPT', else 1.0.
      - Convert to int with +1 (legacy behavior): int(value + 1).
    """
    if run_no != 0:
        return int(given_x), int(given_y), int(given_z)

    mult = 1.3 if (simulation_type in {"GEMC", "NPT"}) else 1.0
    x = int((used_x + fft_add_namd_ang_to_box_dim) * mult + 1)
    y = int((used_y + fft_add_namd_ang_to_box_dim) * mult + 1)
    z = int((used_z + fft_add_namd_ang_to_box_dim) * mult + 1)
    return x, y, z


# --- Step 10. render template with placeholder mapping --------------------------
from typing import Any, Dict, Iterable, Optional


def _apply_replacements(
    template: str,
    mapping: Dict[str, Any],
    *,
    strict: bool = False,
    must_replace: Optional[Iterable[str]] = None,
) -> str:
    """
    Replace all placeholder tokens in `template` using `mapping`.
    - Replaces *all* occurrences of each key.
    - Keys are applied longest-first to avoid substring collisions.
    - If `strict` and `must_replace` are provided, raises if any of those
      tokens remain unreplaced in the result.
    """
    out = template
    for key in sorted(mapping.keys(), key=len, reverse=True):
        out = out.replace(key, str(mapping[key]))

    if strict and must_replace:
        leftovers = [tok for tok in must_replace if tok in out]
        if leftovers:
            raise ValueError(f"Unreplaced tokens: {leftovers}")
    return out


log = logging.getLogger(__name__)


def write_namd_conf_file(
    python_file_directory,
    path_namd_template,
    path_namd_runs,
    gomc_newdir,
    run_no,
    box_number,
    namd_run_steps,
    namd_minimize_steps,
    namd_rst_dcd_xst_steps,
    namd_console_blkavg_e_and_p_steps,
    simulation_temp_k,
    simulation_pressure_bar,
    starting_pdb_box_x_file,
    starting_psf_box_x_file,
    namd_x_pme_grid_dim,
    namd_y_pme_grid_dim,
    namd_z_pme_grid_dim,
    set_x_dim=None,
    set_y_dim=None,
    set_z_dim=None,
    set_angle_alpha=90,
    set_angle_beta=90,
    set_angle_gamma=90,
    fft_add_namd_ang_to_box_dim=0,
):
    """
    Final, wired version using all helpers. Keeps legacy globals compatibility:
      - starting_ff_file_list_namd : list of parameter files
      - check_for_pdb_dims_and_override : callable
      - simulation_type : str in {"NVT","NPT","GEMC"}
      - log_template_file : file-like .write(str)
    """
    # Normalize
    python_file_directory = Path(python_file_directory)
    path_namd_runs = Path(path_namd_runs)
    gomc_newdir = Path(gomc_newdir)

    # 1) Build run/box dir
    target_dir = _compute_namd_box_dir(
        python_file_directory, path_namd_runs, run_no, box_number
    )
    target_dir.mkdir(parents=True, exist_ok=True)

    # 2) Load template text
    template_text = _load_template_text(
        python_file_directory, path_namd_template
    )

    # 3) Parameter files block (from global if available)
    ff_files = globals().get("starting_ff_file_list_namd", [])
    param_block = _build_parameter_files_block(ff_files, target_dir)

    # 4) Paths + PDB lines
    repl_paths, pdb_lines = _compute_run_paths_and_read_pdb_lines(
        python_file_directory,
        gomc_newdir,
        target_dir,
        run_no,
        box_number,
        starting_pdb_box_x_file,
        starting_psf_box_x_file,
    )

    # 5) Parse CRYST1
    rx, ry, rz, ra, rb, rg = _parse_cryst1(pdb_lines)

    # 6) Validate angles for run 0
    _validate_angles(
        run_no, ra, rb, rg, set_angle_alpha, set_angle_beta, set_angle_gamma
    )

    # 7) Resolve used dims via checker or fallbacks
    checker = globals().get("check_for_pdb_dims_and_override", None)
    used_x = _override_dim(checker, "x", run_no, rx, set_x_dim)
    used_y = _override_dim(checker, "y", run_no, ry, set_y_dim)
    used_z = _override_dim(checker, "z", run_no, rz, set_z_dim)

    # 8) PME grid dims
    sim_type = globals().get("simulation_type", "NVT")
    gx, gy, gz = _compute_pme_grid_dims(
        run_no,
        used_x,
        used_y,
        used_z,
        namd_x_pme_grid_dim,
        namd_y_pme_grid_dim,
        namd_z_pme_grid_dim,
        fft_add_namd_ang_to_box_dim,
        sim_type,
    )

    # 9) Compose replacements
    mapping: Dict[str, Any] = {
        "all_parameter_files": param_block,
        "pdb_box_file": repl_paths["pdb_box_file"],
        "psf_box_file": repl_paths["psf_box_file"],
        "coor_file": repl_paths["coor_file"],
        "xsc_file": repl_paths["xsc_file"],
        "vel_file": repl_paths["vel_file"],
        "Bool_restart": repl_paths["Bool_restart"],
        "x_dim_box": used_x,
        "y_dim_box": used_y,
        "z_dim_box": used_z,
        "x_origin_box": used_x / 2,
        "y_origin_box": used_y / 2,
        "z_origin_box": used_z / 2,
        "NAMD_Run_Steps": int(namd_run_steps),
        "NAMD_Minimize": int(namd_minimize_steps),
        "NAMD_RST_DCD_XST_Steps": int(namd_rst_dcd_xst_steps),
        "NAMD_console_BLKavg_E_and_P_Steps": int(
            namd_console_blkavg_e_and_p_steps
        ),
        "current_step": 0,
        "System_temp_set": simulation_temp_k,
        "System_press_set": simulation_pressure_bar,
        "X_PME_GRID_DIM": gx,
        "Y_PME_GRID_DIM": gy,
        "Z_PME_GRID_DIM": gz,
    }

    must_replace = list(mapping.keys())
    rendered = _apply_replacements(
        template_text, mapping, strict=True, must_replace=must_replace
    )
    (target_dir / "in.conf").write_text(rendered)

    msg = f"NAMD simulation data for simulation number {run_no} in box {box_number} is completed\n"
    legacy_log = globals().get("log_template_file", None)
    if hasattr(legacy_log, "write"):
        legacy_log.write(msg)
    logging.getLogger(__name__).info(msg.strip())

    return str(target_dir)
