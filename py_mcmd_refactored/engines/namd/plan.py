# py-MCMD
# Author: Haydar Mehryar
# Copyright (c) 2025
# SPDX-License-Identifier: MIT

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Literal, Optional

from config.models import SimulationConfig
from utils.subprocess_runner import Command

# from utils.persisted_file_lists import persisted_output_path


@dataclass(frozen=True)
class NamdExecutionPlan:
    """Plan describing how NAMD should be launched for this segment."""

    mode: Literal["series", "parallel"]
    box0: Command
    box1: Optional[Command] = None

    def commands(self) -> List[Command]:
        cmds = [self.box0]
        if self.box1 is not None:
            cmds.append(self.box1)
        return cmds


def build_namd_execution_plan(
    cfg: SimulationConfig,
    *,
    exec_path: str,
    box0_dir: Path,
    box1_dir: Optional[Path],
) -> NamdExecutionPlan:
    """Build the NAMD execution plan for the current run segment.

    Legacy parity:
    - Single-box cases always run box0 with +p{total_no_cores}.
    - Two-box GEMC:
        - series: run box0 then box1, both with +p{total_no_cores}
        - parallel: start both, box0 uses +p{no_core_box_0}, box1 uses +p{no_core_box_1}
    """
    two_box = (cfg.simulation_type == "GEMC") and (
        cfg.only_use_box_0_for_namd_for_gemc is False
    )

    if not two_box:
        cores0 = int(cfg.total_no_cores)

        # cmd0 = Command(
        #     argv=[exec_path, f"+p{cores0}", "in.conf"],
        #     cwd=Path(box0_dir),
        #     stdout_path=persisted_output_path("NAMD", box0_dir, "out.dat"),
        # )
        cmd0 = Command(
            argv=[exec_path, f"+p{cores0}", "in.conf"],
            cwd=Path(box0_dir),
            stdout_path=Path(box0_dir) / "out.dat",
        )
        return NamdExecutionPlan(mode="series", box0=cmd0, box1=None)

    # two-box GEMC
    mode: Literal["series", "parallel"] = cfg.namd_simulation_order
    if box1_dir is None:
        raise ValueError(
            "Two-box GEMC requires box1_dir, but box1_dir is None."
        )

    if mode == "series":
        cores0 = int(cfg.total_no_cores)
        cores1 = int(cfg.total_no_cores)
    else:
        # parallel
        cores0 = int(cfg.no_core_box_0)
        cores1 = int(cfg.no_core_box_1)

    # cmd0 = Command(
    #     argv=[exec_path, f"+p{cores0}", "in.conf"],
    #     cwd=Path(box0_dir),
    #     stdout_path=persisted_output_path("NAMD", box0_dir, "out.dat"),
    # )
    cmd0 = Command(
        argv=[exec_path, f"+p{cores0}", "in.conf"],
        cwd=Path(box0_dir),
        stdout_path=Path(box0_dir) / "out.dat",
    )

    # cmd1 = Command(
    #     argv=[exec_path, f"+p{cores1}", "in.conf"],
    #     cwd=Path(box1_dir),
    #     stdout_path=persisted_output_path("NAMD", box1_dir, "out.dat"),
    # )
    cmd1 = Command(
        argv=[exec_path, f"+p{cores1}", "in.conf"],
        cwd=Path(box1_dir),
        stdout_path=Path(box1_dir) / "out.dat",
    )
    return NamdExecutionPlan(mode=mode, box0=cmd0, box1=cmd1)
