# tests/test_namd_dimensions.py
import pytest
from engines.namd.dimensions import check_for_pdb_dims_and_override

def test_override_when_read_none_and_set_dim_numeric_on_run0():
    used = check_for_pdb_dims_and_override(
        dim_axis="x",
        run_no=0,
        read_dim=None,
        set_dim=25.0,
        only_on_run_no=0,
        logger=None,
    )
    assert used == 25.0

def test_error_when_read_none_and_set_dim_invalid_on_run0():
    with pytest.raises(TypeError) as ei:
        check_for_pdb_dims_and_override(
            dim_axis="y",
            run_no=0,
            read_dim=None,
            set_dim=None,
            only_on_run_no=0,
            logger=None,
        )
    assert "ERROR: The user defined y-dimension is None" in str(ei.value)

def test_warn_and_override_when_set_diff_from_read_on_run0():
    with pytest.warns(UserWarning):
        used = check_for_pdb_dims_and_override(
            dim_axis="z",
            run_no=0,
            read_dim=30,
            set_dim=32,
            only_on_run_no=0,
            logger=None,
        )
    assert used == 32

def test_use_read_dim_when_set_same_or_none_on_run0():
    assert check_for_pdb_dims_and_override("x", 0, read_dim=20, set_dim=None, only_on_run_no=0) == 20
    assert check_for_pdb_dims_and_override("x", 0, read_dim=20, set_dim=20,  only_on_run_no=0) == 20

def test_no_override_on_other_runs_even_if_set_diff():
    # Override should not apply when run_no != only_on_run_no
    used = check_for_pdb_dims_and_override(
        dim_axis="x",
        run_no=1,
        read_dim=10,
        set_dim=15,
        only_on_run_no=0,
        logger=None,
    )
    assert used == 10
