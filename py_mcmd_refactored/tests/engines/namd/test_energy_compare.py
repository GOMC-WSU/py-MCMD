# py-MCMD
# Author: Haydar Mehryar
# Copyright (c) 2025
# SPDX-License-Identifier: MIT

import sys

sys.path.insert(0, "/home/arsalan/wsu-gomc/py-MCMD-hm/py_mcmd_refactored")

import logging
from types import SimpleNamespace

import pytest
from engines.namd.energy_compare import compare_namd_gomc_energies


def cfg(pfrac=0.05, vfrac=0.10, vabs=2.0):
    # Minimal duck-typed config; only the required attributes are used.
    return SimpleNamespace(
        allowable_error_fraction_potential=pfrac,
        allowable_error_fraction_vdw_plus_elec=vfrac,
        max_absolute_allowable_kcal_fraction_vdw_plus_elec=vabs,
    )


# ---------------- Potential energy checks ----------------


def test_potential_pass_fraction(caplog):
    caplog.set_level(logging.INFO)
    c = cfg(pfrac=0.05)
    # |(100 - 99)/100| = 0.01 <= 0.05  -> PASS
    compare_namd_gomc_energies(
        c, 100.0, 99.0, -10.0, -10.0, run_no=2, box_number=0
    )
    msgs = [rec.message for rec in caplog.records]
    assert any(
        "PASSED: Box 0: Potential energies error fraction" in m for m in msgs
    )
    assert not any(
        "FAILED: Box 0: Potential energies error fraction" in m for m in msgs
    )


def test_potential_fail_fraction(caplog):
    caplog.set_level(logging.INFO)
    c = cfg(pfrac=0.01)
    # |(100 - 90)/100| = 0.10 > 0.01 -> FAIL
    compare_namd_gomc_energies(
        c, 100.0, 90.0, -10.0, -10.0, run_no=2, box_number=1
    )
    msgs = [rec.message for rec in caplog.records]
    assert any(
        "FAILED: Box 1: Potential energies error fraction" in m for m in msgs
    )


def test_potential_zero_zero_is_pass(caplog):
    caplog.set_level(logging.INFO)
    c = cfg(pfrac=0.0)
    # final==0, initial==0 -> fraction = 0.0 -> PASS
    compare_namd_gomc_energies(
        c, 0.0, 0.0, -10.0, -10.0, run_no=5, box_number=0
    )
    msgs = [rec.message for rec in caplog.records]
    assert any(
        "PASSED: Box 0: Potential energies error fraction" in m for m in msgs
    )


def test_potential_undefined_fraction_is_fail(caplog):
    caplog.set_level(logging.INFO)
    c = cfg(pfrac=1.0)
    # final==0, initial!=0 -> fraction undefined ('NA') -> FAIL
    compare_namd_gomc_energies(
        c, 0.0, 1.0, -10.0, -10.0, run_no=3, box_number=0
    )
    msgs = [rec.message for rec in caplog.records]
    assert any(
        "FAILED: Box 0: Potential energies error fraction" in m for m in msgs
    )
    # Ensure 'NA' is present
    assert any(
        "error fraction =  NA" in m or "error fraction = NA" in m for m in msgs
    )


# ---------------- VDW + ELECT checks ----------------


def test_vdw_elec_pass_by_fraction(caplog):
    caplog.set_level(logging.INFO)
    c = cfg(vfrac=0.05, vabs=0.01)
    # |( -10 - -9.5)/-10| = |(-0.5)/-10| = 0.05 -> PASS via fraction
    compare_namd_gomc_energies(
        c, 100.0, 100.0, -10.0, -9.5, run_no=7, box_number=1
    )
    msgs = [rec.message for rec in caplog.records]
    assert any("PASSED: Box 1: VDW + electrostatic fraction" in m for m in msgs)
    assert not any("FAILED: Box 1: vdw_plus_elec energy" in m for m in msgs)


def test_vdw_elec_pass_by_abs_diff(caplog):
    caplog.set_level(logging.INFO)
    # Tight fractional threshold so fraction path fails; generous abs threshold so abs path passes
    c = cfg(vfrac=0.001, vabs=2.0)
    # fraction = |(100 - 101)/100| = 0.01 > 0.001 -> fraction FAIL
    # abs diff = 1.0 <= 2.0 -> PASS via abs diff
    compare_namd_gomc_energies(
        c, 0.0, 0.0, 100.0, 101.0, run_no=4, box_number=0
    )
    msgs = [rec.message for rec in caplog.records]
    assert any("absolute difference is = 1.0 kcal/mol." in m for m in msgs)
    assert not any("FAILED: Box 0: vdw_plus_elec energy" in m for m in msgs)


def test_vdw_elec_fail_both_fraction_and_abs(caplog):
    caplog.set_level(logging.INFO)
    c = cfg(vfrac=0.001, vabs=0.5)
    # fraction = 0.02 (> 0.001) and abs diff = 2.0 (> 0.5) -> FAIL
    compare_namd_gomc_energies(c, 0.0, 0.0, 100.0, 98.0, run_no=9, box_number=1)
    msgs = [rec.message for rec in caplog.records]
    assert any("FAILED: Box 1: vdw_plus_elec energy" in m for m in msgs)


# ---------------- Combined behavior ----------------


def test_both_checks_emit_two_messages(caplog):
    caplog.set_level(logging.INFO)
    c = cfg(pfrac=0.05, vfrac=0.05, vabs=0.5)
    # Potential PASS; VDW+ELECT PASS (fraction)
    compare_namd_gomc_energies(
        c, 100.0, 99.0, -10.0, -9.5, run_no=2, box_number=0
    )
    msgs = [rec.message for rec in caplog.records]
    # One potential line and one vdw+elec line
    assert any("Potential energies error fraction" in m for m in msgs)
    assert any("VDW + electrostatic" in m for m in msgs)
