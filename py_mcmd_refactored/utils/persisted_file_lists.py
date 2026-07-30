from __future__ import annotations

from pathlib import Path
from typing import Final


# Default-mode disk persistence allow-lists
# Everything else is FIFO-only unless developer_mode enables dual-write.
# NAMD_PERSISTED_BASENAMES: Final[list[str]] = ["out.dat"]
# GOMC_PERSISTED_BASENAMES: Final[list[str]] = ["out.dat"]
NAMD_PERSISTED_BASENAMES: Final[list[str]] = []
GOMC_PERSISTED_BASENAMES: Final[list[str]] = []

_ENGINE_ALLOW_LISTS: Final[dict[str, frozenset[str]]] = {
    "NAMD": frozenset(NAMD_PERSISTED_BASENAMES),
    "GOMC": frozenset(GOMC_PERSISTED_BASENAMES),
}


def _normalize_engine(engine: str) -> str:
    key = str(engine).strip().upper()
    if key not in _ENGINE_ALLOW_LISTS:
        raise ValueError(
            f"Unsupported engine '{engine}'. Expected one of: {sorted(_ENGINE_ALLOW_LISTS)}"
        )
    return key


def get_persisted_basenames(engine: str) -> frozenset[str]:
    """Return the persisted basename allow-list for the requested engine."""
    return _ENGINE_ALLOW_LISTS[_normalize_engine(engine)]


def should_persist(engine: str, basename: str) -> bool:
    """Return True when `basename` is allow-listed for disk persistence."""
    normalized_basename = Path(basename).name
    return normalized_basename in get_persisted_basenames(engine)


def persisted_output_path(engine: str, run_dir: str | Path, basename: str) -> Path:
    """Return the persisted output path for an allow-listed file.

    Raises:
        ValueError: if `basename` is not allow-listed for the given engine.
    """
    normalized_basename = Path(basename).name
    if not should_persist(engine, normalized_basename):
        raise ValueError(
            f"File '{normalized_basename}' is not allow-listed for disk persistence "
            f"for engine '{_normalize_engine(engine)}'."
        )
    return Path(run_dir) / normalized_basename