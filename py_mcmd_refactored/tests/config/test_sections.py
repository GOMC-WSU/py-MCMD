import json
from pathlib import Path

import pytest
from config.models import SimulationConfig, load_simulation_config
from pydantic import ValidationError
from utils.config_sections import flatten_config_sections


@pytest.mark.parametrize("ensemble", ["GEMC", "GCMC", "NPT", "NVT"])
def test_sectioned_input_matches_flat_input_for_each_ensemble(tmp_path, ensemble):
    repo = Path(__file__).resolve().parents[3]
    sectioned = json.loads((repo / "user_input_NAMD_GOMC.json").read_text())
    sectioned["simulation"]["simulation_type"] = ensemble
    if ensemble == "GCMC":
        sectioned["gcmc"]["GCMC_ChemPot_or_Fugacity"] = "ChemPot"
        sectioned["gcmc"]["GCMC_ChemPot_or_Fugacity_dict"] = {"TIP3": -1000}
    flat = {
        key: value
        for settings in sectioned.values()
        for key, value in settings.items()
    }
    path = tmp_path / "sectioned.json"
    path.write_text(json.dumps(sectioned))
    expected = SimulationConfig(**flat).model_dump()
    assert load_simulation_config(path).model_dump() == expected
    assert SimulationConfig(**sectioned).model_dump() == expected
    assert flatten_config_sections(sectioned) == flat


def test_flat_and_sectioned_fields_can_be_combined_without_mutating_input():
    data = {
        "simulation": {"simulation_type": "GCMC"},
        "gcmc": {"GCMC_ChemPot_or_Fugacity_dict": {"CH4": -1000}},
        "path_gomc_template": "custom/gcmc.conf",
    }
    original = json.loads(json.dumps(data))
    assert flatten_config_sections(data) == {
        "simulation_type": "GCMC",
        "GCMC_ChemPot_or_Fugacity_dict": {"CH4": -1000},
        "path_gomc_template": "custom/gcmc.conf",
    }
    assert data == original


@pytest.mark.parametrize("duplicate_location", ["top_level", "other_section"])
@pytest.mark.parametrize("value", ["GEMC", "NPT"])
def test_duplicate_settings_are_rejected_instead_of_silently_overwritten(
    duplicate_location, value
):
    data = {"simulation": {"simulation_type": "GEMC"}}
    if duplicate_location == "top_level":
        data["simulation_type"] = value
    else:
        data["execution"] = {"simulation_type": value}
    with pytest.raises(ValidationError, match="simulation_type.*appears in both"):
        SimulationConfig(**data)


@pytest.mark.parametrize("section", [None, [], "GEMC"])
def test_section_must_be_a_json_object(section):
    with pytest.raises(ValidationError, match="section 'simulation'.*JSON object"):
        SimulationConfig(simulation=section)


def test_unknown_fields_in_sections_still_fail_validation():
    with pytest.raises(ValidationError) as error:
        SimulationConfig(simulation={"simulation_typ": "GEMC"})
    assert any(
        item["loc"] == ("simulation_typ",) and item["type"] == "extra_forbidden"
        for item in error.value.errors()
    )


def test_nested_sections_are_rejected():
    with pytest.raises(ValidationError, match="cannot be nested"):
        SimulationConfig(simulation={"execution": {"no_core_box_0": 4}})
