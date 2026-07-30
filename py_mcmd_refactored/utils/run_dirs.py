from __future__ import annotations

from pathlib import Path
from typing import Union

from utils.path import format_cycle_id


PathLike = Union[str, Path]


def namd_run_dir(namd_root: PathLike, run_no: int, box_number: int, *, id_width: int = 8) -> Path:
    """Return NAMD run directory for a given run_no and box.

    Legacy naming: <NAMD_ROOT>/<zero_padded_run_no>_a or _b
    """
    if box_number not in (0, 1):
        raise ValueError("box_number must be 0 or 1")
    suffix = "a" if box_number == 0 else "b"
    run_id = format_cycle_id(run_no, id_width)
    return Path(namd_root) / f"{run_id}_{suffix}"


def gomc_run_dir(gomc_root: PathLike, run_no: int, *, id_width: int = 8) -> Path:
    """Return GOMC run directory for a given run_no.

    Legacy naming: <GOMC_ROOT>/<zero_padded_run_no>
    """
    run_id = format_cycle_id(run_no, id_width)
    return Path(gomc_root) / run_id