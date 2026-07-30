# config/models.py
import json
import re
from pathlib import Path
from typing import List, Dict, Optional, Literal

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict, StrictBool


class SimulationConfig(BaseModel):
    """
    Pydantic model for hybrid NAMD↔GOMC simulation configuration.
    Enforces type checks, ranges, and cross-field constraints.
    """
    total_cycles_namd_gomc_sims: int = Field(
        ..., alias="total_cycles_namd_gomc_sims", ge=1,
        description="Total number of coupled cycles (>=1)"
    )
    starting_at_cycle_namd_gomc_sims: int = Field(
        ..., ge=0,
        description="Starting cycle index (>=0)"
    )

    # Derived values
    total_sims_namd_gomc: int = 0
    starting_sims_namd_gomc: int = 0

    gomc_use_CPU_or_GPU: Literal["CPU", "GPU"]
    simulation_type: Literal["GEMC", "GCMC", "NPT", "NVT"]
    only_use_box_0_for_namd_for_gemc: bool


    # Execution strategy
    # NOTE: This is only meaningful for GEMC when running two NAMD boxes
    # (only_use_box_0_for_namd_for_gemc=False). For other ensembles, the
    # orchestrator/engines may effectively treat execution as series.
    namd_simulation_order: Literal["series", "parallel"] = Field(
        default="series",
        description=(
            "NAMD execution order for two-box GEMC runs: 'series' or 'parallel'. "
            "Defaults to 'series'."
        ),
    )

    developer_mode: StrictBool = Field(
        default=False,
        description=(
            "Enable developer-mode dual-write behavior for FIFO-managed outputs. "
            "Defaults to false when omitted."
        ),
    )

    # Runtime cleanup and on-the-fly processing
    disk_cleanup_mode: str = Field(
        default="compact",
        description=(
            "Controls rolling disk-space cleanup. Options: 'compact' "
            "(default), 'minimal', or 'off'."
        ),
    )

    process_on_the_fly: StrictBool = Field(
        default=False,
        description=(
            "Enable on-the-fly data processing after every completed "
            "NAMD/GOMC cycle."
        ),
    )

    combined_data_dir: str = Field(
        default="combined_data",
        description="Output directory for on-the-fly combined data files.",
    )

    rel_path_to_combine_binary_catdcd: str = Field(
        default="required_data/bin/catdcd-4.0b/LINUXAMD64/bin/catdcd4.0/catdcd",
        description="Path to the catdcd binary used to combine DCD trajectory files.",
    )

    catdcd_core: Optional[int] = Field(
        default=None,
        description=(
            "CPU core ID to pin catdcd to (via taskset), so the per-cycle "
            "DCD combine does not steal CPU from NAMD's compute threads. "
            "Set this to a core OUTSIDE NAMD's range. For example, if NAMD "
            "uses 8 cores (0-7), set catdcd_core to 8 to give catdcd its own "
            "core. If null, catdcd runs without CPU pinning (default)."
        ),
    )

    otf_reserved_cores: Optional[int] = Field(
        default=None,
        description=(
            "Number of CPU cores to reserve for on-the-fly processing "
            "(catdcd + parsing), kept separate from NAMD's cores. If set, "
            "catdcd is pinned to the reserved core(s) just past NAMD's range."
        ),
    )

    enable_cpu_affinity: StrictBool = Field(
        default=False,
        description=(
            "Whether to pin the on-the-fly processing (catdcd) to a "
            "dedicated CPU core so it does not compete with NAMD."
        ),
    )

    combine_namd_dcd_file: StrictBool = Field(
        default=True,
        description="Whether to combine NAMD DCD trajectory files on-the-fly.",
    )

    combine_gomc_dcd_file: StrictBool = Field(
        default=True,
        description="Whether to combine GOMC DCD trajectory files on-the-fly.",
    )

    otf_keep_raw_cycles: int = Field(
        default=2,
        ge=1,
        description="Number of recent raw cycle directories to keep for crash recovery.",
    )

    # Core counts
    no_core_box_0: int = Field(..., ge=1) # must be a positive integer
    no_core_box_1: int = Field(..., ge=0) # can be zero unless ensemble needs box 1
    
    simulation_temp_k: float = Field(..., gt=0)
    simulation_pressure_bar: Optional[float] = None
    GCMC_ChemPot_or_Fugacity:  Optional[Literal["ChemPot", "Fugacity"]] = None
    GCMC_ChemPot_or_Fugacity_dict: Optional[Dict[str, float]] = None
    namd_minimize_mult_scalar: int = Field(..., ge=0)
    namd_run_steps: int = Field(..., ge=0)
    gomc_run_steps: int = Field(..., ge=0)
    set_dims_box_0_list: List[Optional[float]]
    set_dims_box_1_list: List[Optional[float]]
    set_angle_box_0_list: List[Optional[int]]
    set_angle_box_1_list: List[Optional[int]]
    
    # Force-field file lists (must be list[str])    
    starting_ff_file_list_gomc: List[str]
    starting_ff_file_list_namd: List[str]

    starting_pdb_box_0_file: str
    starting_psf_box_0_file: str
    starting_pdb_box_1_file: Optional[str]
    starting_psf_box_1_file: Optional[str]
    namd2_bin_directory: str
    gomc_bin_directory: str

    # run directory roots (overridable from JSON if needed)
    path_namd_runs: str = Field("NAMD")
    path_gomc_runs: str = Field("GOMC")

    # Make these truly optional so we can detect “missing”
    path_namd_template: Optional[str] = Field(default=None)
    path_gomc_template: Optional[str] = Field(default=None)

    
    # Logging
    log_dir: str = Field("logs")  # can override in JSON

    namd_minimize_steps: int = 0

    # derived (used by orchestrator/engines)
    effective_no_core_box_1: int = 0
    total_no_cores: int = 0

    @field_validator("no_core_box_0", mode="before")
    @classmethod
    def _ensure_box0_int_and_nonzero(cls, v):
        if not isinstance(v, int):
            raise TypeError(
                f"Enter no_core_box_0 as an integer; received {v!r} (type {type(v).__name__})."
            )
        if v == 0:
            raise ValueError("Enter no_core_box_0 as a non-zero number (>=1).")
        return v

    @field_validator("no_core_box_1", mode="before")
    @classmethod
    def _ensure_box1_int(cls, v):
        if not isinstance(v, int):
            raise TypeError(
                f"Enter no_core_box_1 as an integer; received {v!r} (type {type(v).__name__})."
            )
        return v

    
    @field_validator("disk_cleanup_mode", mode="before")
    @classmethod
    def _validate_disk_cleanup_mode(cls, v):
        if not isinstance(v, str):
            raise TypeError("disk_cleanup_mode must be a string.")

        mode = v.strip().lower()
        valid_modes = {"compact", "minimal", "off"}
        if mode not in valid_modes:
            raise ValueError(
                "disk_cleanup_mode must be one of: compact, minimal, off."
            )
        return mode
    
    # @model_validator(mode="after")
    # def _require_box1_when_two_box_ensemble(self):
    #     # For ensembles that use a second box, require non-zero cores for box 1
    #     if self.simulation_type in ("GEMC", "GCMC"):
    #         if self.no_core_box_1 <= 0:
    #             raise ValueError("no_core_box_1 must be > 0")
    #     return self
    
    @model_validator(mode="after")
    def _require_box1_when_two_box_ensemble(self):
        # Only two-box GEMC runs require NAMD cores for box 1.
        # GCMC and one-box GEMC still use only NAMD box 0, so no_core_box_1
        # may be zero for those cases.
        if (
            self.simulation_type == "GEMC"
            and not self.only_use_box_0_for_namd_for_gemc
            and self.no_core_box_1 <= 0
        ):
            raise ValueError(
                "no_core_box_1 must be > 0 for GEMC with two NAMD boxes"
            )
        return self

    @field_validator('set_dims_box_0_list', 'set_dims_box_1_list', mode='before')
    def validate_dims_list(cls, v):
        if v is None:
            return [None, None, None]
        if not isinstance(v, list) or len(v) != 3:
            raise ValueError("set_dims_box_X_list must be a list of three floats or None")
        for x in v:
            if x is not None and x <= 0:
                raise ValueError("All dimensions must be > 0 or None")
        return v

    @field_validator('set_angle_box_0_list', 'set_angle_box_1_list', mode='before')
    def validate_angle_list(cls, v):
        if v is None:
            return [None, None, None]
        if not isinstance(v, list) or len(v) != 3:
            raise ValueError("set_angle_box_X_list must be a list of three ints or None")
        for x in v:
            if x is not None and x != 90:
                raise ValueError("All angles must be 90 or None")
        return v

    @field_validator("GCMC_ChemPot_or_Fugacity_dict")
    @classmethod
    def _gcmc_dict_type(cls, v, info):
        field = info.field_name
        # Allow None when not GCMC; deeper checks happen in model-level validator
        if v is None:
            return v
        if not isinstance(v, dict):
            raise TypeError(f"ERROR: {field} must be a dictionary when using GCMC.")
        # keys must be str, values must be int/float
        for k, val in v.items():
            if not isinstance(k, str):
                raise TypeError(f"The {field} keys must be a string.")
            if not isinstance(val, (int, float)):
                raise TypeError(f"The {field} values must be an integer or float.")
        return v
    
    @model_validator(mode='after')
    def cross_field_validations(self):
        # Alias model fields to local variables
        sim = self.simulation_type
        use0 = self.only_use_box_0_for_namd_for_gemc
        nc1 = self.no_core_box_1
        pres = self.simulation_pressure_bar
        chempot = self.GCMC_ChemPot_or_Fugacity
        chempot_dict = self.GCMC_ChemPot_or_Fugacity_dict

        # GEMC: require >0 cores on box 1 if two-box run
        if sim == 'GEMC' and not use0:
            if nc1 <= 0:
                raise ValueError(
                    "no_core_box_1 must be > 0 when running two NAMD boxes in GEMC"
                )

        # NPT: pressure must be non-negative
        if sim == 'NPT' and (pres is None or pres < 0):
            raise ValueError(
                "simulation_pressure_bar must be >= 0 for NPT simulations"
            )

        # GCMC: require chempot and dict, with valid numeric values
        if sim == 'GCMC':
            if chempot is None or chempot_dict is None:
                raise ValueError(
                    "GCMC_ChemPot_or_Fugacity and its dict must be provided for GCMC simulations"
                )
            for key, val in chempot_dict.items():
                if not isinstance(val, (int, float)):
                    raise TypeError(
                        "GCMC_ChemPot_or_Fugacity_dict values must be numeric"
                    )
                if chempot == 'Fugacity' and val < 0:
                    raise ValueError(
                        "Fugacity values must be >= 0"
                    )
        else:
            # clear GCMC fields when not using GCMC
            object.__setattr__(self, 'GCMC_ChemPot_or_Fugacity', None)
            object.__setattr__(
                self, 'GCMC_ChemPot_or_Fugacity_dict', None
            )

        return self

    @model_validator(mode="after")
    def _derive_template_paths_when_missing(self):
        # Only fill in defaults if user did NOT supply a value
        if self.path_namd_template is None:
            self.path_namd_template = "required_data/config_files/NAMD.conf"

        if self.path_gomc_template is None:
            # derive from simulation_type only if not provided
            self.path_gomc_template = (
                f"required_data/config_files/GOMC_{self.simulation_type}.conf"
            )
        return self

    @field_validator("starting_ff_file_list_gomc", "starting_ff_file_list_namd", mode="after")
    @classmethod
    def _ensure_list_of_strings(cls, v: List[str], info):
        field = info.field_name
        if not isinstance(v, list):
            raise TypeError(
                f"ERROR: The {field} must be provided as a list of strings."
            )
        for i, item in enumerate(v):
            if not isinstance(item, str):
                raise TypeError(
                    f"ERROR: The {field} must be a list of strings (item {i} is {type(item).__name__})."
                )
        return v
    @model_validator(mode="after")
    def _ensemble_consistency(self):
        # --- GCMC-only checks ---
        if self.simulation_type == "GCMC":
            if self.GCMC_ChemPot_or_Fugacity_dict is None:
                raise TypeError(
                    "ERROR: enter the chemical potential or fugacity data (GCMC_ChemPot_or_Fugacity_dict) "
                    "as a dictionary when using the GCMC ensemble."
                )
            if self.GCMC_ChemPot_or_Fugacity is None:
                raise ValueError(
                    "The GCMC_ChemPot_or_Fugacity cannot be None when running the GCMC ensemble."
                )
            # If Fugacity, all values must be >= 0
            if self.GCMC_ChemPot_or_Fugacity == "Fugacity":
                for k, val in self.GCMC_ChemPot_or_Fugacity_dict.items():
                    if val < 0:
                        raise ValueError(
                            "When using Fugacity, GCMC_ChemPot_or_Fugacity_dict values must be >= 0."
                        )
        else:
            # Non-GCMC: allow these to be unset
            # (We do not auto-clear them to preserve round-tripping of configs.)
            pass

        # --- Pressure logic ---
        if self.simulation_type == "NPT":
            if not isinstance(self.simulation_pressure_bar, (int, float)):
                raise TypeError(
                    "The simulation pressure needs to be set for the NPT simulation type (int or float)."
                )
            if self.simulation_pressure_bar < 0:
                raise ValueError(
                    "The simulation pressure must be >= 0 bar for the NPT simulation type."
                )
        else:
            # Set to atmospheric (not used but required numerically by some paths)
            if self.simulation_pressure_bar is None:
                self.simulation_pressure_bar = 1.01325

        return self
    def __init__(self, **data):
        super().__init__(**data)

        # Derive the per-engine step parameters from run steps
        gsteps = int(self.gomc_run_steps)
        nsteps = int(self.namd_run_steps)

        # Tolerances
        object.__setattr__(self, "gomc_console_blkavg_hist_steps", gsteps)
        object.__setattr__(self, "gomc_rst_coor_ckpoint_steps", gsteps)
        object.__setattr__(self, "gomc_hist_sample_steps", min(500, int(gsteps / 10)))
        object.__setattr__(self, "namd_rst_dcd_xst_steps", nsteps)
        object.__setattr__(self, "namd_console_blkavg_e_and_p_steps", nsteps)
        object.__setattr__(self,"namd_minimize_steps",
            int(int(self.namd_run_steps) * int(self.namd_minimize_mult_scalar))
        )

        # Derive effective cores and totals (do *not* mutate the input fields)
        if self.simulation_type == "GEMC" and (self.only_use_box_0_for_namd_for_gemc is False):
            eff_box1 = int(self.no_core_box_1)
            total = int(self.no_core_box_0) + eff_box1
        else:
            # Not GEMC, or GEMC but only using box 0 for NAMD
            eff_box1 = 0
            total = int(self.no_core_box_0)

        object.__setattr__(self, "effective_no_core_box_1", eff_box1)
        object.__setattr__(self, "total_no_cores", total)

        spc = 2  # segments per cycle: NAMD + GOMC
        object.__setattr__(self, "total_sims_namd_gomc", spc * int(self.total_cycles_namd_gomc_sims))
        object.__setattr__(self, "starting_sims_namd_gomc", spc * int(self.starting_at_cycle_namd_gomc_sims))
        
     # ---- tolerances (with defaults) ----
    allowable_error_fraction_vdw_plus_elec: float = Field(5e-3, ge=0)
    allowable_error_fraction_potential: float = Field(5e-3, ge=0)
    max_absolute_allowable_kcal_fraction_vdw_plus_elec: float = Field(0.5, ge=0)

    # ---- engine step params (initialized later) ----
    gomc_console_blkavg_hist_steps: int = 0
    gomc_rst_coor_ckpoint_steps: int = 0
    gomc_hist_sample_steps: int = 0
    namd_rst_dcd_xst_steps: int = 0
    namd_console_blkavg_e_and_p_steps: int = 0

    # Pydantic v2 configuration
    model_config = ConfigDict(
        populate_by_name=True,
        extra="forbid"
    )

def load_simulation_config(path: str) -> SimulationConfig:
    """
    Load a JSON config file, stripping out // comments, and parse into SimulationConfig.
    """
    text = Path(path).read_text()
    cleaned = re.sub(r'//.*$', '', text, flags=re.MULTILINE)
    data = json.loads(cleaned)
    return SimulationConfig(**data)


def main():
    cfg = load_simulation_config("../user_input_NAMD_GOMC.json")
    # Pydantic V2: use model_dump_json for formatted output
    print(cfg.model_dump_json(indent=2))

if __name__ == "__main__":
    main()
    
