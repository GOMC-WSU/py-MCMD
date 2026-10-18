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


def test_full_precision_boundaries_preserve_timeline_and_legacy_facade():
    lines = [
        ETITLE,
        "ENERGY: 0 0 0 0 -0.0004 -0.0100 -0.0103\n",
        "MCMD_ENERGY: 0 -0.00996495760282370 -0.0003416617528543481 -0.01030661934798132\n",
        "ENERGY: 50 0 0 0 -0.0004 -0.0100 -0.0104\n",
        "ENERGY: 100 0 0 0 -0.0003 0.0018 0.0015\n",
        "MCMD_ENERGY: 100 0.001799387155511185 -0.0002961437753475718 0.001503243380163613\n",
    ]
    data = parse_namd_energy_lines(iter(lines), DEFAULTS)
    assert len(data.raw_rows) == 3
    assert data.potential_first == -0.01030661934798132
    assert data.potential_last == 0.001503243380163613
    assert data.potential[1] == -0.0104
    assert data.vdw_plus_elec_last == data.elect_last + data.vdw[-1]
    assert get_namd_energy_data(iter(lines), DEFAULTS)[4:6] == (
        data.potential_first, data.potential_last
    )


def test_full_precision_prevents_rounding_induced_gas_failure():
    from engines.namd.energy_compare import _fraction_error

    lines = [ETITLE, "ENERGY: 100 0 0 0 -0.0004 -0.0100 -0.0103\n"]
    gomc = -0.01035757585513675
    rounded = parse_namd_energy_lines(lines, DEFAULTS)
    precise = parse_namd_energy_lines(lines + [
        "MCMD_ENERGY: 100 -0.00996495760282370 -0.0003416617528543481 -0.01030661934798132\n"
    ], DEFAULTS)
    assert _fraction_error(rounded.potential_last, gomc) > 0.005
    assert _fraction_error(precise.potential_last, gomc) <= 0.005


def test_full_precision_does_not_hide_actual_mismatch():
    from engines.namd.energy_compare import _fraction_error

    data = parse_namd_energy_lines([
        ETITLE, "ENERGY: 0 0 0 0 -0.0004 -0.0026 -0.0030\n",
        "MCMD_ENERGY: 0 -0.002619026392721935 -0.000365639463330948 -0.002984665849125233\n",
    ], DEFAULTS)
    assert _fraction_error(data.potential_last, -0.003029539710830279) > 0.005


@pytest.mark.parametrize("record", [
    "MCMD_ENERGY: 0 1 2\n",
    "MCMD_ENERGY: 0 nan 2 3\n",
    "MCMD_ENERGY: 0 1 2 inf\n",
])
def test_invalid_full_precision_record_is_rejected(record):
    with pytest.raises(ValueError):
        parse_namd_energy_lines([ETITLE, E1, record], DEFAULTS)


def test_precision_record_for_another_step_does_not_overwrite_boundaries():
    data = parse_namd_energy_lines([
        ETITLE, E1, E2, "MCMD_ENERGY: 50 99 99 99\n"
    ], DEFAULTS)
    assert data.potential_first == 15.0
    assert data.potential_last == 18.0
