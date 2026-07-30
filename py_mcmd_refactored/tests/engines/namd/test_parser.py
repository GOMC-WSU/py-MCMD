from pathlib import Path
from py_mcmd_refactored.engines.namd.parser import extract_pme_grid_from_out

def test_extract_pme_grid_from_out_ok(tmp_path: Path):
    p = tmp_path / "out.dat"
    p.write_text(
        "Some header\n"
        "Info: PME GRID DIMENSIONS 60 64 72 other stuff\n"
        "Footer\n"
    )
    assert extract_pme_grid_from_out(p) == (60, 64, 72)

def test_extract_pme_grid_from_out_missing(tmp_path: Path):
    assert extract_pme_grid_from_out(tmp_path / "missing.out") == (None, None, None)

def test_extract_pme_grid_from_out_no_line(tmp_path: Path):
    p = tmp_path / "out.dat"
    p.write_text("no relevant line here\n")
    assert extract_pme_grid_from_out(p) == (None, None, None)
