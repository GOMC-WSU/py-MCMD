"""Compare NAMD gas meshes at identical coordinates in an isolated directory."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
from config.models import load_simulation_config
from engines.namd import namd_writer as nw


def read_forces(path: Path) -> np.ndarray:
    data = path.read_bytes()
    for endian in ("<", ">"):
        n = int(np.frombuffer(data[:4], dtype=endian + "i4")[0])
        if n > 0 and len(data) == 4 + 24 * n:
            return np.frombuffer(data[4:], dtype=endian + "f8").reshape(n, 3)
    raise ValueError(f"Unrecognized NAMD binary force file: {path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-f", "--file", default="user_input_NAMD_GOMC.json")
    parser.add_argument("--namd-binary", type=Path)
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="New directory for inputs, logs, forces and report.json",
    )
    parser.add_argument("--cores", type=int, default=4)
    parser.add_argument("--steps", type=int, default=200)
    parser.add_argument("--reference-spacing", type=float, default=0.75)
    args = parser.parse_args()
    if args.cores < 1 or args.steps < 10 or args.steps % 10:
        parser.error("Use positive cores and steps >=10 divisible by 10")
    if args.reference_spacing <= 0:
        parser.error("Reference spacing must be positive")
    cfg = load_simulation_config(args.file)
    if cfg.simulation_type != "GEMC":
        parser.error("This comparison requires GEMC box-1 starting files")
    binary = (
        args.namd_binary or Path(cfg.namd2_bin_directory) / "namd2"
    ).resolve()
    root = Path.cwd()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    nw.starting_ff_file_list_namd = [
        str((root / f).resolve()) for f in cfg.starting_ff_file_list_namd
    ]
    nw.simulation_type = cfg.simulation_type
    template = cfg.path_namd_template_box_1 or cfg.path_namd_template
    reports = {}
    forces = {}
    # Keep cutoff, topology and coordinates fixed; vary only the mesh.
    for name, spacing, order in (
        ("reference", args.reference_spacing, 8),
        ("baseline", 1.0, 4),
        ("candidate", None, None),
    ):
        run_dir = Path(
            nw.write_namd_conf_file(
                root,
                template,
                output / name,
                "NA",
                0,
                1,
                args.steps,
                0,
                args.steps,
                args.steps,
                cfg.simulation_temp_k,
                cfg.simulation_pressure_bar,
                cfg.starting_pdb_box_1_file,
                cfg.starting_psf_box_1_file,
                None,
                None,
                None,
                set_x_dim=cfg.set_dims_box_1_list[0],
                set_y_dim=cfg.set_dims_box_1_list[1],
                set_z_dim=cfg.set_dims_box_1_list[2],
            )
        )
        conf = (run_dir / "in.conf").read_text()
        if re.search(r"(?im)^\s*PMEGridSize[XYZ]\s", conf):
            parser.error(
                "Automatic sizing required; comment out PMEGridSizeX/Y/Z"
            )
        if not re.search(r"(?im)^\s*PME\s+(yes|on|true|1)\b", conf):
            parser.error("Benchmark requires PME enabled")
        if spacing is not None:
            conf = re.sub(
                r"(?im)^\s*PMEGridSpacing\s+[^\n]+",
                f"PMEGridSpacing {spacing}",
                conf,
            )
            conf = re.sub(r"(?im)^\s*PMEInterpOrder\s+[^\n]+", "", conf)
            # Insert before the first force evaluation.
            conf = conf.replace(
                "# Minimization\n",
                f"PMEInterpOrder {order}\n# Minimization\n",
            )
        conf = conf.replace(
            "run \t$NAMD_RUN_STEPS",
            "run 0\noutput onlyforces mesh_check\nrun $NAMD_RUN_STEPS",
        )
        # A zero-step minimization resets velocities; skip it for this MD check.
        conf = re.sub(r"(?m)^\s*minimize\s+\$NAMD_MINIMIZE\s*$", "", conf)
        conf = conf.replace("# Input\n", "# Input\nseed 12345\n")
        (run_dir / "in.conf").write_text(conf)
        print(f"Running {name}: {run_dir}", flush=True)
        start = time.perf_counter()
        with (run_dir / "out.dat").open("w") as out:
            subprocess.run(
                [str(binary), f"+p{args.cores}", "in.conf"],
                cwd=run_dir,
                stdout=out,
                stderr=subprocess.STDOUT,
                check=True,
                timeout=600,
            )
        elapsed = time.perf_counter() - start
        lines = (run_dir / "out.dat").read_text().splitlines()
        titles = next(
            line.split()[1:] for line in lines if line.startswith("ETITLE:")
        )
        energy = next(
            line.split()[1:] for line in lines if line.startswith("ENERGY:")
        )
        values = dict(zip(titles, map(float, energy)))
        forces[name] = read_forces(run_dir / "mesh_check.force")
        reports[name] = {
            "wall_seconds_including_startup": elapsed,
            "electrostatic_kcal_per_mol": values["ELECT"],
            "potential_kcal_per_mol": values["POTENTIAL"],
            "grid": next(
                (
                    line.strip()
                    for line in lines
                    if "PME GRID DIMENSIONS" in line
                ),
                None,
            ),
        }
    reference_rms = float(
        np.sqrt(np.mean(np.sum(forces["reference"] ** 2, axis=1)))
    )
    for name in ("baseline", "candidate"):
        delta = forces[name] - forces["reference"]
        rms = float(np.sqrt(np.mean(np.sum(delta**2, axis=1))))
        reports[name].update(
            force_vector_rms_error_kcal_per_mol_angstrom=rms,
            force_vector_max_error_kcal_per_mol_angstrom=float(
                np.max(np.linalg.norm(delta, axis=1))
            ),
            force_relative_rms_error=(
                rms / reference_rms if reference_rms else None
            ),
            electrostatic_error_kcal_per_mol=(
                reports[name]["electrostatic_kcal_per_mol"]
                - reports["reference"]["electrostatic_kcal_per_mol"]
            ),
        )
    report = {
        "input": str(Path(args.file).resolve()),
        "binary": str(binary),
        "cores": args.cores,
        "steps": args.steps,
        "reference_spacing": args.reference_spacing,
        "note": (
            "One starting gas configuration; timings include startup "
            "and are not production speedups."
        ),
        "results": reports,
    }
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
