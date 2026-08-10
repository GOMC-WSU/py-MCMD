from __future__ import annotations

import warnings
from logging import Logger
from typing import Optional, Union

Number = Union[int, float]


def check_for_pdb_dims_and_override(
    dim_axis: str,
    run_no: int,
    read_dim: Optional[Number],
    set_dim: Optional[Number] = None,
    only_on_run_no: int = 0,
    logger: Optional[Logger] = None,
) -> Optional[Number]:
    """
    Decide which dimension to use for a given axis based on PDB-read value vs user override.

    Parameters
    ----------
    dim_axis : str
        The dimension axis label ("x", "y", or "z").
    run_no : int
        Simulation run number.
    read_dim : int | float | None
        Dimension read from PDB (or prior step).
    set_dim : int | float | None, default None
        User override. If numeric and run_no == only_on_run_no, may take precedence.
    only_on_run_no : int, default 0
        Only apply the override on this run number (default legacy behavior is run 0).
    logger : logging.Logger | None
        Optional logger for info-level messages (legacy log_template_file replacement).

    Returns
    -------
    used_dim : int | float | None
        Chosen dimension.
    """

    def _log(msg: str) -> None:
        if logger is not None:
            logger.info(msg)

    if run_no == only_on_run_no:
        if read_dim is None:
            if set_dim is not None and isinstance(set_dim, (float, int)):
                used_dim = set_dim
            else:
                write_log_data = (
                    "ERROR: The user defined {}-dimension is None "
                    "or not an integer or a float, and the PDB file has no dimension information "
                    " \n".format(str(dim_axis))
                )
                _log(write_log_data)
                raise TypeError(write_log_data)
        elif (
            read_dim is not None
            and set_dim is not None
            and set_dim != read_dim
            and isinstance(set_dim, (float, int))
        ):
            write_log_data = (
                "WARNING: The user defined {}-dimension is different "
                "than the one read from the starting PDB file {}-dim_PDB = {}, "
                "{}-dim_user_set = {}. The code is setting the user defined {}-dimension."
                " \n".format(
                    str(dim_axis),
                    str(dim_axis),
                    str(read_dim),
                    str(dim_axis),
                    str(set_dim),
                    str(dim_axis),
                )
            )
            _log(write_log_data)
            warnings.warn(write_log_data)
            used_dim = set_dim
        else:
            used_dim = read_dim
    else:
        used_dim = read_dim

    return used_dim
