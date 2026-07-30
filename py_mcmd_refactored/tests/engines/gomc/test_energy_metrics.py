from __future__ import annotations

import pandas as pd
import pytest

from py_mcmd_refactored.engines.gomc.energy_metrics import (
    get_gomc_energy_data_kcal_per_mol,
)


def _df(rows):
    cols = ["TOTAL_ELECT", "TOTAL", "INTRA(NB)", "INTER(LJ)", "LRC"]
    return pd.DataFrame(rows, columns=cols)


def test_metrics_happy_path_multiple_rows():
    df = _df(
        [
            [1.0, 10.0, 0.2, 0.3, 0.4],
            [2.0, 20.0, 0.5, 0.6, 0.7],
            [3.0, 30.0, 0.8, 0.9, 1.0],
        ]
    )

    result = get_gomc_energy_data_kcal_per_mol(df)
    assert len(result) == 12

    (
        te_list,
        te_first,
        te_last,
        t_list,
        t_first,
        t_last,
        lrc_list,
        lrc_first,
        lrc_last,
        vpe_list,
        vpe_first,
        vpe_last,
    ) = result

    # Lists
    assert te_list == [1.0, 2.0, 3.0]
    assert t_list == [10.0, 20.0, 30.0]
    assert lrc_list == [0.4, 0.7, 1.0]

    # Initial/Final
    assert te_first == pytest.approx(1.0)
    assert te_last == pytest.approx(3.0)
    assert t_first == pytest.approx(10.0)
    assert t_last == pytest.approx(30.0)
    assert lrc_first == pytest.approx(0.4)
    assert lrc_last == pytest.approx(1.0)

    # VDW+ELECT = INTRA(NB) + INTER(LJ) + TOTAL_ELECT + LRC
    expected_vpe = [
        0.2 + 0.3 + 1.0 + 0.4,  # 1.9
        0.5 + 0.6 + 2.0 + 0.7,  # 3.8
        0.8 + 0.9 + 3.0 + 1.0,  # 5.7
    ]
    assert vpe_list == pytest.approx(expected_vpe)
    assert vpe_first == pytest.approx(expected_vpe[0])
    assert vpe_last == pytest.approx(expected_vpe[-1])


def test_metrics_accepts_object_dtype_strings():
    # String numbers should be coerced to floats internally
    df = pd.DataFrame(
        {
            "TOTAL_ELECT": ["1", "2"],
            "TOTAL": ["10", "20"],
            "INTRA(NB)": ["0.1", "0.2"],
            "INTER(LJ)": ["0.3", "0.4"],
            "LRC": ["0.5", "0.6"],
            # extra columns should be ignored
            "EXTRA": ["x", "y"],
        }
    )
    (
        _,
        te_first,
        te_last,
        _,
        t_first,
        t_last,
        _,
        lrc_first,
        lrc_last,
        vpe_list,
        vpe_first,
        vpe_last,
    ) = get_gomc_energy_data_kcal_per_mol(df)

    assert te_first == 1.0 and te_last == 2.0
    assert t_first == 10.0 and t_last == 20.0
    assert lrc_first == 0.5 and lrc_last == 0.6
    assert vpe_list == pytest.approx(
        [
            0.1 + 0.3 + 1.0 + 0.5,  # 1.9
            0.2 + 0.4 + 2.0 + 0.6,  # 3.2
        ]
    )
    assert vpe_first == pytest.approx(1.9)
    assert vpe_last == pytest.approx(3.2)


def test_metrics_single_row_edge_case():
    df = _df([[2.5, 15.0, 0.2, 0.4, 0.6]])
    res = get_gomc_energy_data_kcal_per_mol(df)

    (
        te_list,
        te_first,
        te_last,
        t_list,
        t_first,
        t_last,
        lrc_list,
        lrc_first,
        lrc_last,
        vpe_list,
        vpe_first,
        vpe_last,
    ) = res

    assert te_list == [2.5]
    assert te_first == te_last == 2.5
    assert t_list == [15.0]
    assert t_first == t_last == 15.0
    assert lrc_list == [0.6]
    assert lrc_first == lrc_last == 0.6
    assert vpe_list == pytest.approx([0.2 + 0.4 + 2.5 + 0.6])


def test_metrics_missing_required_column_raises():
    df = pd.DataFrame(
        {
            "TOTAL_ELECT": [1.0],
            "TOTAL": [10.0],
            "INTRA(NB)": [0.2],
            # "INTER(LJ)" missing
            "LRC": [0.4],
        }
    )
    with pytest.raises(KeyError, match="Missing required GOMC energy columns"):
        _ = get_gomc_energy_data_kcal_per_mol(df)


def test_metrics_non_numeric_raises():
    df = _df(
        [
            [1.0, "not-a-number", 0.2, 0.3, 0.4],
        ]
    )
    with pytest.raises(
        ValueError, match="Non-numeric values in column 'TOTAL'"
    ):
        _ = get_gomc_energy_data_kcal_per_mol(df)


def test_metrics_empty_df_raises():
    df = _df([])  # empty
    with pytest.raises(ValueError, match="Empty GOMC energy DataFrame"):
        _ = get_gomc_energy_data_kcal_per_mol(df)
