from pathlib import Path

import pytest

from engines.namd.sparse_box import molecule_count


def write_water_psf(path: Path, waters: int):
    atoms, bonds = [], []
    for mol in range(waters):
        for site in range(4):
            atoms.append(f"{4*mol+site+1} A {mol+1} TIP4 O OW0 0 16 0\n")
        for site in (2, 3, 4):
            bonds.extend([4*mol+1, 4*mol+site])
    path.write_text(
        f"PSF\n\n{4*waters} !NATOM\n" + "".join(atoms)
        + f"\n{3*waters} !NBOND: bonds\n\n"
        + " ".join(map(str, bonds)) + "\n"
    )


@pytest.mark.parametrize("waters", [0, 1, 2, 17])
def test_counts_connected_water_molecules(tmp_path, waters):
    psf = tmp_path / "water.psf"
    write_water_psf(psf, waters)
    assert molecule_count(psf) == waters


def test_single_site_molecules_are_counted_without_bonds(tmp_path):
    psf = tmp_path / "gas.psf"
    psf.write_text("2 !NATOM\n1 A 1 CH4 C C 0 16\n"
                   "2 A 2 CH4 C C 0 16\n0 !NBOND\n")
    assert molecule_count(psf) == 2


@pytest.mark.parametrize("text", [
    "PSF\n", "2 !NATOM\n", "1 !NATOM\n1 A 1 CH4 C C 0 16\n",
    "1 !NATOM\n1 A 1 CH4 C C 0 16\n1 !NBOND\n1 2\n",
])
def test_malformed_psf_is_not_classified_as_safe_to_skip(tmp_path, text):
    psf = tmp_path / "bad.psf"
    psf.write_text(text)
    with pytest.raises(ValueError):
        molecule_count(psf)
