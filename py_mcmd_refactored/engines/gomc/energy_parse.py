from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple, Optional
import logging

import pandas as pd

from py_mcmd_refactored.config.models import SimulationConfig
from utils.units import K_TO_KCAL_PER_MOL

log = logging.getLogger(__name__)

def _normalize_etitle_titles(titles: List[str]) -> Tuple[List[str], bool]:
    """If titles start with ['ETITLE:', 'ETITLE:', ...], drop the 2nd token."""
    had_dup = len(titles) >= 2 and titles[0] == "ETITLE:" and titles[1] == "ETITLE:"
    if had_dup:
        return [titles[0]] + titles[2:], True
    return titles, False


def _normalize_energy_tokens(row_tokens: List[str], had_dup_etitle: bool) -> List[str]:
    """If header had duplicate 'ETITLE:', drop the 2nd token from ENERGY rows too."""
    if had_dup_etitle and len(row_tokens) >= 2:
        return [row_tokens[0]] + row_tokens[2:]
    return row_tokens

def _validate_box_number(box_number: int) -> None:
    if box_number not in (0, 1):
        raise ValueError(f"box_number must be 0 or 1, got {box_number}")


def _as_lines(lines: Iterable[str]) -> List[str]:
    """Normalize any iterable of strings to a concrete list (preserve content)."""
    return list(lines)


def _extract_first_titles(all_lines: Sequence[str], prefix: str) -> Optional[List[str]]:
    """Return the first header line split into tokens, or None if not found."""
    for line in all_lines:
        if line.startswith(prefix):
            return line.split()
    return None


def _iter_rows_with_prefix(all_lines: Sequence[str], prefix: str) -> Iterable[List[str]]:
    """Yield tokenized rows starting with the given prefix."""
    for line in all_lines:
        if line.startswith(prefix):
            yield line.split()


def _convert_energy_row_tokens(
    row_tokens: List[str],
    titles: List[str],
    *,
    step_offset: int,
    scale_k_to_kcalmol: float,
) -> List[object]:
    """
    Convert one ENERGY row to typed values following legacy rules:
      - if title == 'ETITLE:'  -> keep token as string
      - if title == 'STEP'     -> int(token) + step_offset
      - otherwise              -> float(token) * scale_k_to_kcalmol
    Only the first len(titles) tokens are considered (legacy aligns by position).
    """
    n = min(len(row_tokens), len(titles))
    out: List[object] = []
    for j in range(n):
        title = titles[j]
        tok = row_tokens[j]
        if title == "ETITLE:":
            out.append(tok)
        elif title == "STEP":
            # tolerate non-integer tokens by raising a clear error
            try:
                out.append(int(int(tok) + int(step_offset)))
            except ValueError as e:
                raise ValueError(f"Malformed STEP token: {tok!r}") from e
        else:
            try:
                out.append(float(tok) * float(scale_k_to_kcalmol))
            except ValueError as e:
                raise ValueError(f"Malformed numeric token for '{title}': {tok!r}") from e
    return out



def get_gomc_energy_data(
    cfg: SimulationConfig,
    lines: Iterable[str],
    box_number: int,
) -> pd.DataFrame:
    """
    Parse GOMC energy data for a given box from log lines and return a DataFrame.

    Parameters
    ----------
    cfg : SimulationConfig
        Provides run-time parameters, notably:
          - current_step (int): STEP offset to add
          - K_to_kcal_mol (float): scaling factor for energies
    lines : Iterable[str]
        The GOMC log file content as lines.
    box_number : int
        0 or 1 (box index).

    Returns
    -------
    pandas.DataFrame
        DataFrame with columns matching the 'ETITLE:' header and rows from 'ENER_<box_number>:' lines.
    """
    _validate_box_number(box_number)
    all_lines = _as_lines(lines)

    # Headers
    e_titles_raw = _extract_first_titles(all_lines, "ETITLE:")
    if not e_titles_raw:
        raise ValueError("Missing ETITLE header before ENERGY lines.")

    # Normalize duplicate ETITLE: token in header (and remember if we did)
    e_titles, had_dup_etitle = _normalize_etitle_titles(e_titles_raw)

    # Collect ENERGY rows for the specified box
    energy_prefix = f"ENER_{box_number}:"
    rows_converted: List[List[object]] = []

    step_offset = getattr(cfg, "current_step", 0)
    # Regression test: if cfg.K_to_kcal_mol is missing, the parser must use
    # utils.units.K_TO_KCAL_PER_MOL instead of falling back to 1.0.
    
    # scal  e = getattr(cfg, "K_to_kcal_mol", 1.0)
    scale = getattr(cfg, "K_to_kcal_mol", K_TO_KCAL_PER_MOL)
    for row in _iter_rows_with_prefix(all_lines, energy_prefix):
        row = _normalize_energy_tokens(row, had_dup_etitle)
        rows_converted.append(
            _convert_energy_row_tokens(
                row,
                e_titles,
                step_offset=int(step_offset),
                scale_k_to_kcalmol=float(scale),
            )
        )

    # Build DataFrame; if no rows, return empty with the normalized columns
    df = pd.DataFrame(rows_converted, columns=e_titles)
    return df
