from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from config.models import SimulationConfig
from orchestrator.state import RunState
from utils.run_dirs import gomc_run_dir, namd_run_dir


@dataclass(frozen=True)
class StartContext:
    """Computed context at the beginning of orchestrator.run()."""
    current_step: int
    previous_namd_box0_dir: Optional[Path]
    previous_namd_box1_dir: Optional[Path]
    previous_gomc_dir: Optional[Path]


def compute_start_context(cfg: SimulationConfig, *, id_width: int = 8) -> StartContext:
    """Compute restart-related values for the first iteration of the run_no loop.

    Mirrors legacy behavior:
      - If starting_sims==0: current_step=0 and no previous dirs
      - Else:
          prev NAMD dirs from (starting_sims-2)
          prev GOMC dir  from (starting_sims-1)
          current_step = (namd_steps + gomc_steps)*start_cycle + namd_minimize_steps
    """
    starting_sims = int(cfg.starting_sims_namd_gomc)
    start_cycle = int(cfg.starting_at_cycle_namd_gomc_sims)

    if starting_sims <= 0 or start_cycle <= 0:
        return StartContext(
            current_step=0,
            previous_namd_box0_dir=None,
            previous_namd_box1_dir=None,
            previous_gomc_dir=None,
        )

    prev_namd_run_no = starting_sims - 2
    prev_gomc_run_no = starting_sims - 1

    prev_namd_box0 = namd_run_dir(cfg.path_namd_runs, prev_namd_run_no, 0, id_width=id_width)
    prev_gomc = gomc_run_dir(cfg.path_gomc_runs, prev_gomc_run_no, id_width=id_width)

    prev_namd_box1 = None
    if cfg.simulation_type == "GEMC" and (cfg.only_use_box_0_for_namd_for_gemc is False):
        prev_namd_box1 = namd_run_dir(cfg.path_namd_runs, prev_namd_run_no, 1, id_width=id_width)

    current_step = (int(cfg.namd_run_steps) + int(cfg.gomc_run_steps)) * start_cycle + int(cfg.namd_minimize_steps)

    return StartContext(
        current_step=current_step,
        previous_namd_box0_dir=prev_namd_box0,
        previous_namd_box1_dir=prev_namd_box1,
        previous_gomc_dir=prev_gomc,
    )


def apply_start_context(state: RunState, ctx: StartContext) -> None:
    """Apply computed start context to the mutable RunState.

    We seed 'latest dirs' to the last completed segment dirs in a restart case,
    so engines can reference them before the first new segment executes.
    """
    state.current_step = int(ctx.current_step)
    state.namd_box0_dir = ctx.previous_namd_box0_dir
    state.namd_box1_dir = ctx.previous_namd_box1_dir
    state.gomc_dir = ctx.previous_gomc_dir