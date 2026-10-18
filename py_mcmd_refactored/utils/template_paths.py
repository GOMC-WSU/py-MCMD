"""Locations of distributed engine templates and legacy path compatibility."""
from pathlib import Path

DEFAULT_NAMD_TEMPLATE = "required_data/config_files/namd/nvt.conf"


def default_namd_template(ensemble: str, box_number: int = 0) -> str:
    """Select the distributed MD template for an ensemble and box."""
    if ensemble == "GEMC":
        phase = "gas" if box_number == 1 else "liquid"
        return f"required_data/config_files/namd/gemc_{phase}.conf"
    if ensemble in ("NPT", "GCMC"):
        return f"required_data/config_files/namd/{ensemble.lower()}.conf"
    return DEFAULT_NAMD_TEMPLATE


def select_namd_template(
    ensemble: str,
    box_number: int,
    shared_template: str | None = None,
    box_template: str | None = None,
) -> str:
    """Honor GEMC box overrides, then a shared override, then the defaults."""
    if ensemble == "GEMC" and box_template:
        return box_template
    return shared_template or default_namd_template(ensemble, box_number)


def default_gomc_template(ensemble: str) -> str:
    return f"required_data/config_files/gomc/{ensemble.lower()}.conf"


_LEGACY_TEMPLATE_LOCATIONS = {
    "NAMD.conf": "namd/nvt.conf",
    "NAMD_liquid.conf": "namd/gemc_liquid.conf",
    "NAMD_gas.conf": "namd/gemc_gas.conf",
    "NAMD_2.conf": "archive/namd/NAMD_2.conf",
    "GOMC_NPT_v1.conf": "archive/gomc/GOMC_NPT_v1.conf",
    **{
        f"GOMC_{sim}.conf": f"gomc/{sim.lower()}.conf"
        for sim in ("NVT", "NPT", "GCMC", "GEMC")
    },
}


def resolve_template_path(path: str | Path) -> Path:
    """Honor existing files; redirect missing old distributed template paths."""
    path = Path(path)
    if path.is_file():
        return path
    if (
        path.parent.name == "config_files"
        and path.parent.parent.name == "required_data"
    ):
        destination = _LEGACY_TEMPLATE_LOCATIONS.get(path.name)
        if destination is not None:
            relocated = path.parent / destination
            if relocated.is_file():
                return relocated
    return path
