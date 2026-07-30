import logging
import os
from pathlib import Path

from config.models import SimulationConfig

logger = logging.getLogger(__name__)


class Engine:
    """Abstract base for NAMD and GOMC engines."""

    """Shared base for NAMD and GOMC engine wrappers."""

    def __init__(
        self, cfg: SimulationConfig, engine_type: str, dry_run: bool = False
    ):
        """
        Initialize common engine state.

        Subclasses resolve executable and template paths because NAMD and GOMC
        use different binary naming conventions and dry-run behavior.

        Parameters
        ----------
        cfg : SimulationConfig
            The simulation configuration object.
        engine_type : str
            Either "NAMD" or "GOMC".
        """
        self.cfg = cfg
        self.engine_type = engine_type.upper()
        self.dry_run: bool = dry_run
        # Paths for this engine’s runs
        self.run_dir: Path = Path(self.engine_type)
        os.makedirs(self.run_dir, exist_ok=True)

        # Emit warnings if folders already exist
        if self.run_dir.exists() and any(self.run_dir.iterdir()):
            logger.warning(
                f"[{self.engine_type}] Directory {self.run_dir} already exists. "
                "If startup/restart fails, try deleting it or its last subfolders."
            )

        self.bin_dir: Path | None = None
        self.exec_path: Path | None = None
        self.path_template: Path | None = None

        if self.engine_type not in ("NAMD", "GOMC"):
            raise ValueError(f"Unknown engine_type {self.engine_type}")

        logger.info(
            f"\n\t[{self.engine_type}] initialized with\n"
            "\t\trun_dir={self.run_dir},\n"
            "\t\tbin_dir={self.bin_dir},\n"
            "\t\tpath_template={self.path_template}"
        )

    def run(self):
        raise NotImplementedError("Subclasses must implement run()")
