"""Coordinate and topology transfer for a fixed-framework, one-site GCMC stage.

The NAMD framework stays bonded and charged. GOMC receives a separate,
fixed, zero-bond topology and its own force field. Neither engine's
validated parameter file is generated or edited here.
"""
from __future__ import annotations

import os
import re
import struct
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree


def _psf(path: Path):
    lines = path.read_text().splitlines(keepends=True)
    at = next(i for i, line in enumerate(lines) if "!NATOM" in line)
    count = int(lines[at].split()[0])
    atoms = [line.split() for line in lines[at + 1 : at + 1 + count]]
    if len(atoms) != count or any(len(atom) < 8 for atom in atoms):
        raise ValueError(f"Invalid PSF atom section: {path}")
    return lines, at, atoms


def _pdb(path: Path):
    lines = path.read_text().splitlines(keepends=True)
    atoms = [line for line in lines if line.startswith(("ATOM  ", "HETATM"))]
    coords = np.asarray(
        [[float(line[i : i + 8]) for i in (30, 38, 46)] for line in atoms],
        dtype=float,
    ).reshape((-1, 3))
    return lines, atoms, coords


def _box_from_xsc(path: Path) -> np.ndarray:
    rows = [
        line.split()
        for line in path.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]
    if not rows or len(rows[-1]) < 10:
        raise ValueError(f"Invalid XSC file: {path}")
    box = np.asarray([float(rows[-1][i]) for i in (1, 5, 9)])
    if not np.all(np.isfinite(box)) or np.any(box <= 0):
        raise ValueError(f"Invalid box lengths in {path}")
    return box


def _namd_coor(path: Path) -> np.ndarray:
    with path.open("rb") as stream:
        raw = stream.read()
    if len(raw) < 4:
        raise ValueError(f"Empty NAMD coordinate restart: {path}")
    for endian in ("<", ">"):
        n = struct.unpack(f"{endian}i", raw[:4])[0]
        if n > 0 and len(raw) == 4 + 24 * n:
            return np.frombuffer(
                raw, dtype=f"{endian}f8", offset=4
            ).reshape(n, 3).copy()
    raise ValueError(f"Invalid NAMD coordinate restart: {path}")


def _write_psf(reference: Path, output: Path, framework: str, guest: str, n_guest: int):
    lines, at, atoms = _psf(reference)
    n_framework = sum(atom[3] == framework for atom in atoms)
    if atoms[:n_framework] != [atom for atom in atoms if atom[3] == framework]:
        raise ValueError("Reference PSF framework atoms must be contiguous")
    guest_atoms = [atom for atom in atoms if atom[3] == guest]
    if not guest_atoms or len(atoms) != n_framework + len(guest_atoms):
        raise ValueError("Reference PSF must contain one-site guest atoms after framework")
    if n_guest < 0:
        raise ValueError("Negative guest count")
    template = guest_atoms[0]
    new_atoms = lines[at + 1 : at + 1 + n_framework]
    for k in range(n_guest):
        idx = n_framework + k + 1
        residue = int(atoms[0][2]) + k + 1
        new_atoms.append(
            f"{idx:8d} {template[1]:<4s} {residue:<4d} "
            f"{guest:<4s} {template[4]:<4s} {template[5]:<4s} "
            f"{float(template[6]):12.6f} {float(template[7]):13.4f}\n"
        )
    output.write_text(
        "".join(
            lines[:at]
            + [f"{n_framework + n_guest:8d} !NATOM\n"]
            + new_atoms
            + lines[at + 1 + len(atoms) :]
        )
    )
    return n_framework


def _atom_line(template: str, index: int, residue: int, xyz: np.ndarray) -> str:
    if not np.all(np.isfinite(xyz)) or np.any(np.abs(xyz) >= 9999):
        raise ValueError(f"Coordinate cannot be represented in PDB: {xyz}")
    return (
        template[:6]
        + f"{index:5d}"
        + template[11:22]
        + f"{residue:4d}"
        + template[26:30]
        + "".join(f"{value:8.3f}" for value in xyz)
        + template[54:]
    )


def _write_pdb(
    reference: Path,
    output: Path,
    framework: str,
    guest: str,
    coords: np.ndarray,
    box: np.ndarray,
    n_framework: int,
):
    lines, atoms, _ = _pdb(reference)
    if len(atoms) < n_framework + 1:
        raise ValueError("PDB reference is missing a guest template")
    if any(line[17:21].strip() != framework for line in atoms[:n_framework]):
        raise ValueError("PDB reference framework order differs from PSF")
    template_guest = next(
        (line for line in atoms[n_framework:] if line[17:21].strip() == guest),
        None,
    )
    if template_guest is None:
        raise ValueError("PDB reference is missing the guest residue")
    if len(coords) < n_framework:
        raise ValueError("Missing framework coordinates")
    preamble = [
        line for line in lines[: lines.index(atoms[0])]
        if not line.startswith("CRYST1")
    ]
    preamble.insert(
        0,
        f"CRYST1{box[0]:9.3f}{box[1]:9.3f}{box[2]:9.3f}"
        "  90.00  90.00  90.00 P 1          \n",
    )
    output_lines = preamble
    for i in range(n_framework):
        output_lines.append(_atom_line(atoms[i], i + 1, 1, coords[i]))
    for k, xyz in enumerate(coords[n_framework:]):
        output_lines.append(
            _atom_line(template_guest, n_framework + k + 1, k + 2, xyz)
        )
    output_lines.append("END\n")
    output.write_text("".join(output_lines))


def _add_gomc_restart_remark(source: Path, output: Path, displacement: float = 0.5):
    """Supply GOMC's fixed-width move scale and remove unrelated REMARKs."""
    if displacement <= 0:
        raise ValueError("GOMC displacement scale must be positive")
    lines = [
        line for line in source.read_text().splitlines(keepends=True)
        if not line.startswith("REMARK")
    ]
    if not any(line.startswith("CRYST1") for line in lines):
        raise ValueError(f"GOMC restart PDB needs CRYST1: {source}")
    remark = (
        f"REMARK     GOMC{displacement:10.3f}{0.78540:10.5f}"
        f"{0.0:12.3f}   {0:15d}\n"
    )
    output.write_text(remark + "".join(lines))


def unwrap_shared_box0_restart(
    gomc_dir: Path,
    namd_dir: Path,
    previous_psf: Path,
    framework: str,
    guest: str,
):
    """Put fixed framework atoms in NAMD's periodic images in the shared PDB.

    GOMC writes its restart PDB with wrapped coordinates. NAMD cannot safely
    start a bonded framework from those images. The PSF is kept unchanged, and
    the PDB path remains the same for the next NAMD and GOMC stages.
    """
    gomc_dir = Path(gomc_dir)
    _, _, before = _psf(Path(previous_psf))
    _, _, after = _psf(gomc_dir / "Output_data_BOX_0_restart.psf")
    n_framework = sum(atom[3] == framework for atom in before)
    if n_framework == 0 or any(atom[3] != framework for atom in before[:n_framework]):
        raise ValueError("Shared box-0 PSF needs contiguous framework atoms")
    if len(after) < n_framework or any(atom[3] != framework for atom in after[:n_framework]):
        raise ValueError("GOMC changed the framework atom count or order")
    if any(a[4:8] != b[4:8] for a, b in zip(before[:n_framework], after[:n_framework])):
        raise ValueError("GOMC changed framework names, types, charges, or masses")
    if any(atom[3] != guest for atom in after[n_framework:]):
        raise ValueError("Unexpected guest residue in GOMC box 0")
    namd_xyz = _namd_coor(Path(namd_dir) / "namdOut.restart.coor")
    restart_pdb = gomc_dir / "Output_data_BOX_0_restart.pdb"
    lines, pdb_atoms, gomc_xyz = _pdb(restart_pdb)
    if len(namd_xyz) != len(before) or len(gomc_xyz) != len(after):
        raise ValueError("Shared box-0 PSF and coordinate counts differ")
    if any(line[17:21].strip() != framework for line in pdb_atoms[:n_framework]):
        raise ValueError("GOMC restart PDB framework order differs from PSF")
    if any(abs(float(line[60:66]) - 1.0) > 1e-6 for line in pdb_atoms[:n_framework]):
        raise ValueError("GOMC framework is not fixed in its restart PDB")
    box = _box_from_xsc(gomc_dir / "Output_data_BOX_0_restart.xsc")
    difference = gomc_xyz[:n_framework] - namd_xyz[:n_framework]
    difference -= box * np.rint(difference / box)
    if np.max(np.abs(difference)) > 0.005:
        raise ValueError("GOMC framework positions differ from preceding NAMD")
    unwrapped = gomc_xyz[:n_framework] + box * np.rint(
        (namd_xyz[:n_framework] - gomc_xyz[:n_framework]) / box
    )
    new_lines = []
    atom_index = 0
    for line in lines:
        if line.startswith(("ATOM  ", "HETATM")):
            if atom_index < n_framework:
                line = line[:30] + "".join(f"{v:8.3f}" for v in unwrapped[atom_index]) + line[54:]
            atom_index += 1
        new_lines.append(line)
    temp = restart_pdb.with_suffix(".pdb.tmp")
    temp.write_text("".join(new_lines))
    temp.replace(restart_pdb)


class RigidFrameworkGCMCTransfer:
    def __init__(self, cfg):
        root = Path.cwd()
        self.namd_psf = (root / cfg.starting_psf_box_0_file).resolve()
        self.namd_pdb = (root / cfg.starting_pdb_box_0_file).resolve()
        self.gomc_psf = (root / cfg.rigid_gomc_reference_psf).resolve()
        self.gomc_pdb = (root / cfg.rigid_gomc_reference_pdb).resolve()
        self.box1_pdb = (root / cfg.starting_pdb_box_1_file).resolve()
        self.framework = cfg.framework_residue
        self.guest = cfg.single_site_guest_residue
        _, _, n_atoms = _psf(self.namd_psf)
        _, _, g_atoms = _psf(self.gomc_psf)
        n_host = [a for a in n_atoms if a[3] == self.framework]
        g_host = [a for a in g_atoms if a[3] == self.framework]
        if not n_host or len(n_host) != len(g_host):
            raise ValueError("NAMD and GOMC framework atom counts differ")
        if [a[4:6] for a in n_host] != [a[4:6] for a in g_host]:
            raise ValueError("NAMD and GOMC framework atom order or types differ")
        self.n_framework = len(n_host)
        if len(n_atoms) <= self.n_framework or len(g_atoms) <= self.n_framework:
            raise ValueError("Both references need a one-site guest template")

    def prepare_gomc(self, run_dir: Path, namd_dir: Path, previous_gomc: Path | None, dry_run: bool):
        run_dir = Path(run_dir)
        coords_path = Path(namd_dir) / "namdOut.restart.coor"
        if dry_run:
            fallback = (
                Path(previous_gomc) / "namd_ready_box_0.pdb"
                if previous_gomc is not None
                else self.namd_pdb
            )
            _, _, coords = _pdb(fallback)
        else:
            coords = _namd_coor(coords_path)
        box = _box_from_xsc(Path(namd_dir) / "namdOut.restart.xsc")
        n_guest = len(coords) - self.n_framework
        psf = run_dir / "rigid_box_0.psf"
        pdb = run_dir / "rigid_box_0.pdb"
        _write_psf(self.gomc_psf, psf, self.framework, self.guest, n_guest)
        _write_pdb(
            self.namd_pdb, run_dir / "namd_reference_box_0.pdb",
            self.framework, self.guest, coords, box, self.n_framework,
        )
        _write_pdb(
            self.gomc_pdb, pdb, self.framework, self.guest,
            coords % box, box, self.n_framework,
        )
        _add_gomc_restart_remark(pdb, pdb)
        box1_source = (
            Path(previous_gomc) / "Output_data_BOX_1_restart.pdb"
            if previous_gomc is not None else self.box1_pdb
        )
        box1_pdb = run_dir / "restart_box_1.pdb"
        _add_gomc_restart_remark(box1_source, box1_pdb)
        return pdb, psf, box1_pdb

    def prepare_namd(self, run_dir: Path):
        run_dir = Path(run_dir)
        pre_pdb = run_dir / "rigid_box_0.pdb"
        pre_psf = run_dir / "rigid_box_0.psf"
        restart_pdb = run_dir / "Output_data_BOX_0_restart.pdb"
        restart_psf = run_dir / "Output_data_BOX_0_restart.psf"
        box = _box_from_xsc(run_dir / "Output_data_BOX_0_restart.xsc")
        _, _, pre_atoms = _psf(pre_psf)
        _, _, restart_atoms = _psf(restart_psf)
        _, _, pre_xyz = _pdb(pre_pdb)
        _, _, restart_xyz = _pdb(restart_pdb)
        if len(pre_atoms) != len(pre_xyz) or len(restart_atoms) != len(restart_xyz):
            raise ValueError("GOMC PSF/PDB atom counts differ")
        pre_host = [i for i, atom in enumerate(pre_atoms) if atom[3] == self.framework]
        restart_host = [i for i, atom in enumerate(restart_atoms) if atom[3] == self.framework]
        if len(pre_host) != self.n_framework or len(restart_host) != self.n_framework:
            raise ValueError("Framework atom count changed in GOMC")
        if Counter(pre_atoms[i][5] for i in pre_host) != Counter(
            restart_atoms[i][5] for i in restart_host
        ):
            raise ValueError("GOMC framework atom types changed")
        mapped = np.empty((self.n_framework, 3))
        for atom_type in set(pre_atoms[i][5] for i in pre_host):
            targets = [i for i in pre_host if pre_atoms[i][5] == atom_type]
            candidates = [i for i in restart_host if restart_atoms[i][5] == atom_type]
            tree = cKDTree(restart_xyz[candidates] % box, boxsize=box)
            distance, nearest = tree.query(pre_xyz[targets] % box, k=1)
            if len(set(nearest.tolist())) != len(nearest) or np.max(distance) > 0.005:
                raise ValueError(
                    f"Cannot uniquely map fixed framework type {atom_type}; "
                    f"maximum distance {np.max(distance):.6f} A"
                )
            for target, candidate in zip(targets, nearest):
                mapped[target] = restart_xyz[candidates[candidate]]
        guests = [
            restart_xyz[i] for i, atom in enumerate(restart_atoms)
            if atom[3] == self.guest
        ]
        if len(restart_atoms) != self.n_framework + len(guests):
            raise ValueError("Unexpected GOMC residue in box 0")
        _, _, namd_reference_xyz = _pdb(run_dir / "namd_reference_box_0.pdb")
        if len(namd_reference_xyz) < self.n_framework:
            raise ValueError("NAMD reference is missing framework atoms")
        mapped += box * np.rint(
            (namd_reference_xyz[: self.n_framework] - mapped) / box
        )
        coords = np.vstack([mapped, np.asarray(guests).reshape((-1, 3))])
        psf = run_dir / "namd_ready_box_0.psf"
        pdb = run_dir / "namd_ready_box_0.pdb"
        _write_psf(self.namd_psf, psf, self.framework, self.guest, len(guests))
        _write_pdb(self.namd_pdb, pdb, self.framework, self.guest, coords, box, self.n_framework)
        return pdb, psf

    @staticmethod
    def rewrite_gomc_conf(conf: Path, pdb: Path, psf: Path, box1_pdb: Path):
        lines = []
        for line in conf.read_text().splitlines():
            fields = line.split()
            key = fields[0].lower() if fields else ""
            if key in {"bincoordinates", "extendedsystem", "binvelocities"}:
                continue
            if key == "coordinates" and len(fields) > 1 and fields[1] == "0":
                line = f"Coordinates 0 {pdb.name}"
            elif key == "coordinates" and len(fields) > 1 and fields[1] == "1":
                line = f"Coordinates 1 {box1_pdb.name}"
            elif key == "structure" and len(fields) > 1 and fields[1] == "0":
                line = f"Structure 0 {psf.name}"
            elif key == "restart":
                line = "Restart true"
            elif key == "checkpoint":
                line = "Checkpoint false Output_data_restart.chk"
            lines.append(line)
        conf.write_text("\n".join(lines) + "\n")

    @staticmethod
    def rewrite_namd_conf(conf: Path, pdb: Path, psf: Path):
        text = conf.read_text()
        rel_pdb = os.path.relpath(pdb, conf.parent)
        rel_psf = os.path.relpath(psf, conf.parent)
        text, n_pdb = re.subn(r"(?m)^coordinates\s+\S+\s*$", f"coordinates {rel_pdb}", text)
        text, n_psf = re.subn(r"(?m)^structure\s+\S+\s*$", f"structure {rel_psf}", text)
        text, n_restart = re.subn(
            r"(?m)^set RESTART_STATUS\s+\S+\s*$", "set RESTART_STATUS false", text
        )
        if (n_pdb, n_psf, n_restart) != (1, 1, 1):
            raise ValueError("Unexpected NAMD template structure")
        conf.write_text(text)
