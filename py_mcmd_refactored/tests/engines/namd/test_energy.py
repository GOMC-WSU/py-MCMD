import sys

sys.path.insert(0, "/home/arsalan/wsu-gomc/py-MCMD-hm/py_mcmd_refactored")
from engines.namd.energy import NamdEnergyData


def test_dataclass_instantiation_and_fields():
    d = NamdEnergyData(
        titles=("ETITLE:", "TS", "VDW", "ELECT", "POTENTIAL"),
        raw_rows=((float("nan"), 0.0, -10.0, 20.0, 15.0),),
        elect=[20.0],
        potential=[15.0],
        vdw=[-10.0],
        vdw_plus_elec=[10.0],
        elect_first=20.0,
        elect_last=20.0,
        potential_first=15.0,
        potential_last=15.0,
        vdw_plus_elec_first=10.0,
        vdw_plus_elec_last=10.0,
    )
    assert d.elect_last == 20.0
    assert d.vdw_plus_elec_first == d.vdw[0] + d.elect[0]


import math

from engines.namd.energy import _extract_titles_and_rows

ETITLE = "ETITLE: TS BOND ANGLE DIHED VDW ELECT POTENTIAL\n"
E1 = "ENERGY:  0   0.0   0.0   0.0  -10.0  20.0  15.0\n"
E2 = "ENERGY:  100 0.0   0.0   0.0  -12.5  22.5  18.0\n"
DEFAULTS = ["TS", "BOND", "ANGLE", "DIHED", "VDW", "ELECT", "POTENTIAL"]


def test_extract_titles_and_rows_with_etitle():
    titles, rows = _extract_titles_and_rows([ETITLE, E1, E2], DEFAULTS)
    assert titles[0] == "ETITLE:"
    assert "ELECT" in titles and "POTENTIAL" in titles and "VDW" in titles
    assert len(rows) == 2 and math.isnan(rows[0][0])


def test_extract_titles_and_rows_without_etitle_defaults():
    titles, rows = _extract_titles_and_rows([E1, E2], DEFAULTS)
    assert titles[0] == "ETITLE:" and titles[-1] == "POTENTIAL"
    assert len(rows) == 2


def test_extract_titles_and_rows_no_energy_raises():
    import pytest

    with pytest.raises(ValueError):
        _extract_titles_and_rows([ETITLE], DEFAULTS)


from engines.namd.energy import _column_indices


def test_column_indices_ok():
    titles = ["ETITLE:", "TS", "VDW", "ELECT", "POTENTIAL"]
    idx = _column_indices(titles)
    assert idx["ELECT"] == 3
    assert idx["POTENTIAL"] == 4
    assert idx["VDW"] == 2


def test_column_indices_missing_raises():
    import pytest

    titles = ["ETITLE:", "TS", "VDW"]  # ELECT and POTENTIAL missing
    with pytest.raises(KeyError):
        _column_indices(titles)


from engines.namd.energy import _col


def test_col_extracts_values_from_rows():
    rows = [
        [float("nan"), 0.0, -10.0, 20.0, 15.0],
        [float("nan"), 100.0, -12.5, 22.5, 18.0],
    ]
    # ELECT at index 3, VDW at index 2, POTENTIAL at index 4
    assert _col(rows, 3) == [20.0, 22.5]
    assert _col(rows, 2) == [-10.0, -12.5]
    assert _col(rows, 4) == [15.0, 18.0]


from engines.namd.energy import parse_namd_energy_lines


def test_parse_end_to_end_with_etitle():
    data = parse_namd_energy_lines([ETITLE, E1, E2], DEFAULTS)
    assert data.elect == [20.0, 22.5]
    assert data.potential == [15.0, 18.0]
    assert data.vdw == [-10.0, -12.5]
    assert data.vdw_plus_elec == [10.0, 10.0]
    assert data.elect_first == 20.0 and data.elect_last == 22.5


def test_parse_without_etitle_uses_defaults():
    data = parse_namd_energy_lines([E1, E2], DEFAULTS)
    assert data.titles[0] == "ETITLE:"
    assert data.potential_last == 18.0


def test_parse_whitespace_variant():
    et = "ETITLE:   TS   BOND  ANGLE   DIHED   VDW    ELECT   POTENTIAL\n"
    e = "ENERGY:    10  0.0   0.0    0.0    -5.0   6.0     4.0\n"
    d = parse_namd_energy_lines([et, e], DEFAULTS)
    assert d.vdw_plus_elec_first == 1.0


from engines.namd.energy import get_namd_energy_data


def test_legacy_facade_tuple_shape_and_values():
    out = get_namd_energy_data([ETITLE, E1, E2], DEFAULTS)
    assert isinstance(out, tuple) and len(out) == 9
    elect, e0, eN, pot, p0, pN, vpe, v0, vN = out
    assert elect == [20.0, 22.5]
    assert (e0, eN) == (20.0, 22.5)
    assert pot == [15.0, 18.0]
    assert (p0, pN) == (15.0, 18.0)
    assert vpe == [10.0, 10.0]
    assert (v0, vN) == (10.0, 10.0)


import pytest
from engines.namd.energy import get_namd_energy_data, parse_namd_energy_lines


def test_parse_missing_required_column_raises_keyerror():
    # Missing ELECT in ETITLE (order matters)
    bad_etitle = "ETITLE: TS BOND ANGLE DIHED VDW POTENTIAL\n"
    e1 = "ENERGY:  0  0.0 0.0 0.0  -10.0  15.0\n"  # aligns with titles above
    with pytest.raises(KeyError):
        parse_namd_energy_lines(
            [bad_etitle, e1],
            ["TS", "BOND", "ANGLE", "DIHED", "VDW", "ELECT", "POTENTIAL"],
        )


def test_parse_no_energy_lines_raises_valueerror():
    et = "ETITLE: TS BOND ANGLE DIHED VDW ELECT POTENTIAL\n"
    with pytest.raises(ValueError):
        parse_namd_energy_lines(
            [et], ["TS", "BOND", "ANGLE", "DIHED", "VDW", "ELECT", "POTENTIAL"]
        )


def test_legacy_facade_propagates_errors():
    # No ENERGY lines → ValueError should bubble up through the facade
    et = "ETITLE: TS BOND ANGLE DIHED VDW ELECT POTENTIAL\n"
    with pytest.raises(ValueError):
        get_namd_energy_data(
            [et], ["TS", "BOND", "ANGLE", "DIHED", "VDW", "ELECT", "POTENTIAL"]
        )
