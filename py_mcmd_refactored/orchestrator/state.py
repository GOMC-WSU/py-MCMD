from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from config.models import SimulationConfig


@dataclass
class PmeDims:
    """PME grid dimensions for a single box."""

    x: Optional[int] = None
    y: Optional[int] = None
    z: Optional[int] = None

    def as_tuple(self) -> tuple[Optional[int], Optional[int], Optional[int]]:
        return (self.x, self.y, self.z)


@dataclass
class RunTimings:
    """Timing values accumulated within a cycle."""

    cycle_start_time: Optional[datetime] = None
    max_namd_cycle_time_s: Optional[float] = None
    gomc_cycle_time_s: Optional[float] = None
    cycle_run_time_s: Optional[float] = None
    python_only_time_s: Optional[float] = None


@dataclass
class EnergyContinuity:
    """Minimal scalar energy values required for NAMD↔GOMC continuity checks."""

    namd_potential_initial: Optional[float] = None
    namd_potential_final: Optional[float] = None
    namd_vdw_plus_elec_initial: Optional[float] = None
    namd_vdw_plus_elec_final: Optional[float] = None

    gomc_potential_initial: Optional[float] = None
    gomc_potential_final: Optional[float] = None
    gomc_vdw_plus_elec_initial: Optional[float] = None
    gomc_vdw_plus_elec_final: Optional[float] = None


@dataclass
class RunState:
    """All mutable state required by the legacy `run_no` loop."""

    current_step: int = 0

    # Latest run directories
    namd_box0_dir: Optional[Path] = None
    namd_box1_dir: Optional[Path] = None
    gomc_dir: Optional[Path] = None

    # PME dimensions
    pme_box0: PmeDims = field(default_factory=PmeDims)
    pme_box1: PmeDims = field(default_factory=PmeDims)

    # Run-0 FFT metadata (used to link FFT grid file into later NAMD dirs)
    run0_fft_name_box0: Optional[str] = None
    run0_fft_name_box1: Optional[str] = None
    run0_dir_box0: Optional[Path] = None
    run0_dir_box1: Optional[Path] = None

    # Energy continuity cache (only scalars needed for comparisons)
    energy_box0: EnergyContinuity = field(default_factory=EnergyContinuity)
    energy_box1: EnergyContinuity = field(default_factory=EnergyContinuity)

    # Timing stats
    timings: RunTimings = field(default_factory=RunTimings)

    @classmethod
    def from_config(cls, cfg: SimulationConfig) -> "RunState":
        """Construct a default state for a new orchestrator instance.

        This method must not perform filesystem I/O. Restart-specific initialization
        (e.g., current_step and prior directories) is handled in Subtask 3.
        """
        _ = cfg
        return cls(current_step=0)

    def snapshot(self) -> Dict[str, Any]:
        """Return a small, JSON-serializable snapshot for logging/tests."""

        def _p(p: Optional[Path]) -> Optional[str]:
            return str(p) if p is not None else None

        return {
            "current_step": self.current_step,
            "namd_box0_dir": _p(self.namd_box0_dir),
            "namd_box1_dir": _p(self.namd_box1_dir),
            "gomc_dir": _p(self.gomc_dir),
            "pme_box0": self.pme_box0.as_tuple(),
            "pme_box1": self.pme_box1.as_tuple(),
            "run0_dir_box0": _p(self.run0_dir_box0),
            "run0_dir_box1": _p(self.run0_dir_box1),
            "run0_fft_name_box0": self.run0_fft_name_box0,
            "run0_fft_name_box1": self.run0_fft_name_box1,
        }
