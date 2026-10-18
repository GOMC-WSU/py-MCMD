"""Detect boxes that cannot safely use NAMD's LJ tail correction."""
from pathlib import Path


SKIPPED_MARKER = "NAMD_SKIPPED.txt"


def molecule_count(psf: Path) -> int:
    """Count connected molecules from PSF bonds, including zero-atom boxes."""
    with psf.open() as stream:
        for line in stream:
            if "!NATOM" in line:
                atoms = int(line.split()[0])
                break
        else:
            raise ValueError(f"Missing NATOM section in {psf}")
        if atoms == 0:
            return 0
        indices = []
        for _ in range(atoms):
            row = next(stream, "").split()
            if len(row) < 8:
                raise ValueError(f"Incomplete atom section in {psf}")
            indices.append(int(row[0]))
        if len(set(indices)) != atoms:
            raise ValueError(f"Duplicate atom indices in {psf}")
        for line in stream:
            if "!NBOND" in line:
                bonds = int(line.split()[0])
                break
        else:
            raise ValueError(f"Missing NBOND section in {psf}")

        parent = {i: i for i in indices}

        def find(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        endpoints = []
        while len(endpoints) < 2 * bonds:
            line = next(stream, None)
            if line is None:
                raise ValueError(f"Incomplete bond section in {psf}")
            row = line.split()
            if not row:
                continue
            if any(not token.isdigit() for token in row):
                raise ValueError(f"Incomplete bond section in {psf}")
            endpoints.extend(map(int, row))
        if len(endpoints) != 2 * bonds:
            raise ValueError(f"Invalid bond count in {psf}")
        molecules = atoms
        for a, b in zip(endpoints[::2], endpoints[1::2]):
            if a not in parent or b not in parent:
                raise ValueError(f"Bond references an unknown atom in {psf}")
            a, b = find(a), find(b)
            if a != b:
                parent[b] = a
                molecules -= 1
        return molecules
