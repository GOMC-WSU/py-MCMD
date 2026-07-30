import sys
sys.path.insert(0, "/home/arsalan/wsu-gomc/py-MCMD-hm/py_mcmd_refactored")

from pathlib import Path
from config.models import SimulationConfig
from engines.namd_engine import NamdEngine

def make_cfg(tmp_path: Path, **kw):
    base = dict(
        # minimal, valid config fields...
        total_cycles_namd_gomc_sims=1,
        starting_at_cycle_namd_gomc_sims=0,
        simulation_type="NPT",
        gomc_use_CPU_or_GPU="CPU",
        only_use_box_0_for_namd_for_gemc=True,
        no_core_box_0=1, no_core_box_1=0,
        simulation_temp_k=298.15, simulation_pressure_bar=1.0,
        namd_minimize_mult_scalar=1, namd_run_steps=10, gomc_run_steps=10,
        set_dims_box_0_list=[25,25,25], set_angle_box_0_list=[90,90,90],
        set_dims_box_1_list=[25,25,25], set_angle_box_1_list=[90,90,90],
        starting_ff_file_list_gomc=["a.inp"], starting_ff_file_list_namd=["b.inp"],
        starting_pdb_box_0_file="box0.pdb", starting_psf_box_0_file="box0.psf",
        starting_pdb_box_1_file="box1.pdb", starting_psf_box_1_file="box1.psf",
        namd2_bin_directory=str(tmp_path/"bin_namd"),
        gomc_bin_directory=str(tmp_path/"bin_gomc"),
        path_namd_runs=str(tmp_path/"NAMD"),
        path_gomc_runs=str(tmp_path/"GOMC"),
        log_dir=str(tmp_path/"logs"),
    )
    base.update(kw)
    return SimulationConfig(**base)

def test_get_run0_pme_dims(tmp_path: Path):
    cfg = make_cfg(tmp_path)
    # prepare run0 out.dat
    run0 = (tmp_path / "NAMD" / "0000000000_a")
    run0.mkdir(parents=True, exist_ok=True)
    (run0 / "out.dat").write_text("Info: PME GRID DIMENSIONS 48 50 52\n")

    eng = NamdEngine(cfg, dry_run=True)
    nx, ny, nz, run0_dir = eng.get_run0_pme_dims(0)
    assert (nx, ny, nz) == (48, 50, 52)
    assert run0_dir.endswith("NAMD/0000000000_a")


def test_namd_managed_stdout_routes_only_to_runtime_dir(tmp_path: Path):
    cfg = make_cfg(tmp_path)
    eng = NamdEngine(cfg, dry_run=True)
    runtime_dir = tmp_path / "managed" / "NAMD" / "0000000000_a"
    disk_dir = tmp_path / "NAMD" / "0000000000_a"

    kwargs = eng._stdout_command_kwargs(
        runtime_dir=runtime_dir,
        disk_dir=disk_dir,
    )

    assert kwargs == {"stdout_path": runtime_dir / "out.dat"}
    assert "stdout_disk_path" not in kwargs

