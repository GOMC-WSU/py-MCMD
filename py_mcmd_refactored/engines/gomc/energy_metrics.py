
from __future__ import annotations

from typing import Iterable, List, Tuple
import logging

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

_REQUIRED_COLS = ("TOTAL_ELECT", "TOTAL", "INTRA(NB)", "INTER(LJ)", "LRC")


def _require_columns(df: pd.DataFrame, required: Iterable[str]) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise KeyError(f"Missing required GOMC energy columns: {missing}. "
                       f"Present: {list(df.columns)}")


def _col_as_floats(df: pd.DataFrame, col: str) -> pd.Series:
    s = pd.to_numeric(df[col], errors="coerce")
    if s.isna().any():
        bad_ix = s[s.isna()].index.tolist()
        raise ValueError(f"Non-numeric values in column '{col}' at rows {bad_ix}")
    return s.astype(float)


def get_gomc_energy_data_kcal_per_mol(gomc_energy_data_box_x_df: pd.DataFrame) -> Tuple[
    List[float], float, float,
    List[float], float, float,
    List[float], float, float,
    List[float], float, float
]:
    """
    Compute derived energy series and initial/final scalars in kcal/mol.

    Expects columns:
      TOTAL_ELECT, TOTAL, INTRA(NB), INTER(LJ), LRC

    Returns (legacy order):
      (
        TOTAL_ELECT list,
        TOTAL_ELECT first,
        TOTAL_ELECT last,
        TOTAL list,
        TOTAL first,
        TOTAL last,
        LRC list,
        LRC first,
        LRC last,
        VDW+ELECT list (= INTRA(NB) + INTER(LJ) + TOTAL_ELECT + LRC),
        VDW+ELECT first,
        VDW+ELECT last,
      )
    """
    df = gomc_energy_data_box_x_df
    if df.empty:
        raise ValueError("Empty GOMC energy DataFrame.")

    _require_columns(df, _REQUIRED_COLS)

    # Coerce to numeric floats (robust to object dtypes)
    total_elect = _col_as_floats(df, "TOTAL_ELECT")
    total = _col_as_floats(df, "TOTAL")
    intra_nb = _col_as_floats(df, "INTRA(NB)")
    inter_lj = _col_as_floats(df, "INTER(LJ)")
    lrc = _col_as_floats(df, "LRC")

    # Vectorized VDW + ELECT = INTRA(NB) + INTER(LJ) + TOTAL_ELECT + LRC
    vdw_plus_elec = intra_nb.values + inter_lj.values + total_elect.values + lrc.values

    # Convert to lists for legacy compatibility
    list_total_elect = total_elect.tolist()
    list_total = total.tolist()
    list_lrc = lrc.tolist()
    list_vdw_plus_elec = vdw_plus_elec.astype(float).tolist()

    # Initial / final values
    te_first, te_last = float(list_total_elect[0]), float(list_total_elect[-1])
    t_first, t_last = float(list_total[0]), float(list_total[-1])
    lrc_first, lrc_last = float(list_lrc[0]), float(list_lrc[-1])
    vpe_first, vpe_last = float(list_vdw_plus_elec[0]), float(list_vdw_plus_elec[-1])

    log.debug(
        "Computed GOMC energy metrics: rows=%d, TOTAL_ELECT[0]=%.6g, TOTAL[0]=%.6g, LRC[0]=%.6g, VDW+ELECT[0]=%.6g",
        len(df), te_first, t_first, lrc_first, vpe_first
    )

    return (
        list_total_elect,
        te_first,
        te_last,
        list_total,
        t_first,
        t_last,
        list_lrc,
        lrc_first,
        lrc_last,
        list_vdw_plus_elec,
        vpe_first,
        vpe_last,
    )
