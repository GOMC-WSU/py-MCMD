# py-MCMD
# Author: Haydar Mehryar 
# Copyright (c) 2025
# SPDX-License-Identifier: MIT

from __future__ import annotations


import logging
from typing import Optional
from py_mcmd_refactored.config.models import SimulationConfig

log = logging.getLogger(__name__)

# ---------- math helpers ----------
def _fraction_error(final_val: float, initial_val: float) -> Optional[float]:
    """
    Return |(final - initial) / final|.
    - If final==0 and initial==0 -> 0.0
    - If final==0 and initial!=0 -> None (undefined => 'NA' in logs)
    """
    final_val = float(final_val)
    initial_val = float(initial_val)
    if final_val == 0.0:
        return 0.0 if initial_val == 0.0 else None
    return abs((final_val - initial_val) / final_val)

def _abs_diff(final_val: float, initial_val: float) -> float:
    return abs(float(final_val) - float(initial_val))

def _fmt_fraction(fr: Optional[float]) -> str:
    return "NA" if fr is None else f"{fr}"

# ---------- message helpers (legacy phrasing preserved) ----------
def _msg_potential_pass(box_number: int, run_no: int, frac: Optional[float]) -> str:
    return (
        "PASSED: Box {}: Potential energies error fraction between the check "
        "between the last point in run {} and the first point in run {}, "
        "error fraction = {}\n"
    ).format(box_number, int(run_no - 1), int(run_no), _fmt_fraction(frac))

def _msg_potential_fail(box_number: int, run_no: int, frac: Optional[float]) -> str:
    return (
        "FAILED: Box {}: Potential energies error fraction between the last "
        "point in run {} and the first point in run {}, error fraction =  {}\n"
    ).format(box_number, int(run_no - 1), int(run_no), _fmt_fraction(frac))

def _msg_vdw_frac_pass(box_number: int, run_no: int, frac: Optional[float]) -> str:
    return (
        "PASSED: Box {}: VDW + electrostatic fraction between the last point in run {} "
        "and the first point in run {}, error fraction = {}\n"
    ).format(box_number, int(run_no - 1), int(run_no), _fmt_fraction(frac))

def _msg_vdw_abs_pass(box_number: int, run_no: int, absd: float) -> str:
    return (
        "PASSED: Box {}: The VDW + electrostatic energy error fraction between the last point in run {} "
        "and the first point in run {}, absolute difference is = {} kcal/mol.\n"
    ).format(box_number, int(run_no - 1), int(run_no), absd)

def _msg_vdw_fail(box_number: int, run_no: int, frac: Optional[float], absd: float) -> str:
    return (
        "FAILED: Box {}: vdw_plus_elec energy  error fraction between the last point in run {} "
        "and the first point in run {}, error fraction = {} or the absolute difference is = {} kcal/mol.\n"
    ).format(box_number, int(run_no - 1), int(run_no), _fmt_fraction(frac), absd)

# ---------- thresholds from config ----------
def _resolve_thresholds_from_cfg(cfg: SimulationConfig) -> tuple[float, float, float]:
    return (
        float(cfg.allowable_error_fraction_potential),
        float(cfg.allowable_error_fraction_vdw_plus_elec),
        float(cfg.max_absolute_allowable_kcal_fraction_vdw_plus_elec),
    )

# ---------- public API (config-aware) ----------
def compare_namd_gomc_energies(  # config-aware entrypoint
    cfg: SimulationConfig,
    e_potential_box_x_final_value,
    e_potential_box_x_initial_value,
    e_vdw_plus_elec_box_x_final_value,
    e_vdw_plus_elec_box_x_initial_value,
    run_no: int,
    box_number: int,
) -> None:
    """
    Compare NAMD↔GOMC energies using thresholds from SimulationConfig and centralized logging.
    Returns None (side-effect: logs PASS/FAIL messages).
    """
    tol_potential_frac, tol_vdw_frac, tol_vdw_abs_kcal = _resolve_thresholds_from_cfg(cfg)

    # --- Potential (fractional only)
    pot_frac = _fraction_error(e_potential_box_x_final_value, e_potential_box_x_initial_value)
    if (pot_frac is not None) and (pot_frac <= tol_potential_frac):
        log.info(_msg_potential_pass(box_number, run_no, pot_frac).strip())
    else:
        log.warning(_msg_potential_fail(box_number, run_no, pot_frac).strip())

    # --- VDW+ELECT (fractional OR absolute fallback)
    vpe_frac = _fraction_error(e_vdw_plus_elec_box_x_final_value, e_vdw_plus_elec_box_x_initial_value)
    vpe_absd = _abs_diff(e_vdw_plus_elec_box_x_final_value, e_vdw_plus_elec_box_x_initial_value)

    if (vpe_frac is not None) and (vpe_frac <= tol_vdw_frac):
        log.info(_msg_vdw_frac_pass(box_number, run_no, vpe_frac).strip())
    elif vpe_absd <= tol_vdw_abs_kcal:
        log.info(_msg_vdw_abs_pass(box_number, run_no, vpe_absd).strip())
    else:
        log.warning(_msg_vdw_fail(box_number, run_no, vpe_frac, vpe_absd).strip())

    return None





