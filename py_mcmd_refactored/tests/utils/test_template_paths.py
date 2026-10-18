from pathlib import Path

import pytest
from utils.template_paths import resolve_template_path


@pytest.mark.parametrize(
    "old,new",
    [
        ("NAMD.conf", "namd/nvt.conf"),
        ("NAMD_liquid.conf", "namd/gemc_liquid.conf"),
        ("NAMD_gas.conf", "namd/gemc_gas.conf"),
        ("NAMD_2.conf", "archive/namd/NAMD_2.conf"),
        ("GOMC_NPT_v1.conf", "archive/gomc/GOMC_NPT_v1.conf"),
        *[
            (f"GOMC_{sim}.conf", f"gomc/{sim.lower()}.conf")
            for sim in ("NVT", "NPT", "GCMC", "GEMC")
        ],
    ],
)
def test_legacy_distributed_paths_resolve_after_move(
    tmp_path, monkeypatch, old, new
):
    monkeypatch.chdir(tmp_path)
    directory = Path("required_data/config_files")
    relocated = directory / new
    relocated.parent.mkdir(parents=True)
    relocated.write_text("# template\n")
    assert resolve_template_path(directory / old) == relocated
    assert (
        resolve_template_path((directory / old).absolute())
        == relocated.absolute()
    )


def test_existing_custom_template_takes_precedence(tmp_path):
    directory = tmp_path / "required_data/config_files"
    directory.mkdir(parents=True)
    old = directory / "NAMD.conf"
    old.write_text("# user's customized template\n")
    newer = directory / "namd/nvt.conf"
    newer.parent.mkdir()
    newer.write_text("# distributed template\n")
    assert resolve_template_path(old) == old


def test_missing_custom_file_is_not_redirected(tmp_path):
    old = tmp_path / "custom/NAMD.conf"
    assert resolve_template_path(old) == old
