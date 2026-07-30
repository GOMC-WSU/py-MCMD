# py-MCMD
# Author: Haydar Mehryar 
# Copyright (c) 2025
# SPDX-License-Identifier: MIT

from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, List, Tuple

@dataclass(frozen=True)
class NamdEnergyData:
    titles: Tuple[str, ...]                      # column names (includes 'ETITLE:' first)
    raw_rows: Tuple[Tuple[float, ...], ...]      # numeric rows; index 0 is NaN placeholder
    elect: List[float]
    potential: List[float]
    vdw: List[float]
    vdw_plus_elec: List[float]
    elect_first: float
    elect_last: float
    potential_first: float
    potential_last: float
    vdw_plus_elec_first: float
    vdw_plus_elec_last: float


from typing import List, Iterable, Tuple
import math

def _normalize_titles(titles: List[str], default_titles: Iterable[str]) -> List[str]:
    """Use defaults if missing and ensure first token slot aligns with ENERGY."""
    if not titles:
        titles = list(default_titles)
    if titles and titles[0] != "ETITLE:":
        titles = ["ETITLE:"] + titles
    return titles

def _extract_titles_and_rows(
    lines: Iterable[str],
    default_titles: Iterable[str],
) -> Tuple[List[str], List[List[float]]]:
    """
    Parse ETITLE/ENERGY sections:
      - First ETITLE line → titles (kept as tokens, including 'ETITLE:')
      - All ENERGY lines → numeric rows; insert NaN at col0 to align with titles
    Parse ETITLE/ENERGY sections into aligned title and numeric rows.
    Backward-compatible façade returning the legacy 9-tuple.
    Raises:
      ValueError if no ENERGY lines found.
    """
    titles: List[str] = []
    rows: List[List[float]] = []

    for line in lines:
        if line.startswith("ETITLE:"):
            titles = line.split()
        elif line.startswith("ENERGY:"):
            parts = line.split()
            numeric = [math.nan] + [float(x) for x in parts[1:]]
            rows.append(numeric)

    titles = _normalize_titles(titles, default_titles)

    if not rows:
        raise ValueError("No ENERGY lines found in NAMD energy output")

    width = len(titles)
    norm_rows: List[List[float]] = []
    for r in rows:
        if len(r) < width:
            r = r + [math.nan] * (width - len(r))
        elif len(r) > width:
            r = r[:width]
        norm_rows.append(r)

    return titles, norm_rows

from typing import Dict, List

def _column_indices(
    titles: List[str],
    required: tuple[str, ...] = ("ELECT", "POTENTIAL", "VDW"),
) -> Dict[str, int]:
    """
    Map required column names to their indices in `titles`.
    Raises KeyError if any required name is missing.
    """
    idx: Dict[str, int] = {}
    for name in required:
        try:
            idx[name] = titles.index(name)
        except ValueError as e:
            raise KeyError(f"Required column '{name}' not found in titles: {titles}") from e
    return idx


from typing import List

def _col(rows: List[List[float]], idx: int) -> List[float]:
    """
    Return the column at index `idx` as a list[float] from `rows`.
    """
    return [float(r[idx]) for r in rows]

def parse_namd_energy_lines(
    lines: Iterable[str],
    default_titles: Iterable[str],
) -> NamdEnergyData:
    """
    Pure parser for NAMD energy output.

    - Accepts an iterable of lines from a NAMD .log/.out containing ETITLE/ENERGY blocks.
    - Falls back to `default_titles` if ETITLE is missing.
    - Returns typed series and convenience first/last scalars.
    - Requires columns: ELECT, POTENTIAL, VDW.
    """
    titles, rows = _extract_titles_and_rows(lines, default_titles)
    idx = _column_indices(titles, required=("ELECT", "POTENTIAL", "VDW"))

    elect = _col(rows, idx["ELECT"])
    potential = _col(rows, idx["POTENTIAL"])
    vdw = _col(rows, idx["VDW"])
    vdw_plus_elec = [vdw[i] + elect[i] for i in range(len(rows))]

    return NamdEnergyData(
        titles=tuple(titles),
        raw_rows=tuple(tuple(x for x in r) for r in rows),
        elect=elect,
        potential=potential,
        vdw=vdw,
        vdw_plus_elec=vdw_plus_elec,
        elect_first=elect[0],
        elect_last=elect[-1],
        potential_first=potential[0],
        potential_last=potential[-1],
        vdw_plus_elec_first=vdw_plus_elec[0],
        vdw_plus_elec_last=vdw_plus_elec[-1],
    )

from typing import Iterable

def get_namd_energy_data(
    read_namd_box_x_energy_file: Iterable[str],
    e_default_namd_titles: Iterable[str],
):
    """
    Backward-compatible façade returning the legacy 9-tuple:
      (elect_series, elect_first, elect_last,
       potential_series, potential_first, potential_last,
       vdw_plus_elec_series, vdw_plus_elec_first, vdw_plus_elec_last)
    Series are lists of floats (pandas-free).
    """
    data = parse_namd_energy_lines(read_namd_box_x_energy_file, e_default_namd_titles)
    return (
        data.elect,
        data.elect_first,
        data.elect_last,
        data.potential,
        data.potential_first,
        data.potential_last,
        data.vdw_plus_elec,
        data.vdw_plus_elec_first,
        data.vdw_plus_elec_last,
    )

