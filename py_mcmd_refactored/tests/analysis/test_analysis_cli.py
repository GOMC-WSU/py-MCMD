import csv
import json

import numpy as np
import pytest

pytest.importorskip("pymbar")

from py_mcmd_refactored.analysis.reporting import compare_reports
from py_mcmd_refactored.cli.analyze import main


def test_csv_cli_artifacts_and_reference(tmp_path):
    source = tmp_path / "input.csv"
    x = np.random.default_rng(618).normal(size=300)
    with source.open("w") as handle:
        handle.write("sample_index,value\n")
        for i, value in enumerate(x):
            handle.write(f"{i},{value}\n")
    reference = tmp_path / "reference"
    assert (
        main(
            [
                str(source),
                "--column",
                "value",
                "--output",
                str(reference),
                "--discard",
                "0",
                "--runtime-seconds",
                "600",
                "--production-seconds",
                "600",
                "--no-plots",
            ]
        )
        == 0
    )
    report = json.loads((reference / "report.json").read_text())
    assert report["metadata"]["pymbar_version"] == "4.0.3"
    assert report["results"][0]["g"] >= 1
    current = tmp_path / "current"
    assert (
        main(
            [
                str(source),
                "--column",
                "value",
                "--output",
                str(current),
                "--discard",
                "0",
                "--runtime-seconds",
                "300",
                "--production-seconds",
                "300",
                "--compare",
                str(reference),
                "--no-plots",
            ]
        )
        == 0
    )
    ratio = json.loads((current / "comparison.json").read_text())[0]
    assert ratio["efficiency_ratio"] == pytest.approx(2)
    assert ratio["interpretation"] == "descriptive_only_model_match_unverified"
    with (current / "acf.csv").open() as handle:
        rows = list(csv.DictReader(handle))
    assert float(rows[0]["correlation"]) == pytest.approx(1)
    assert int(rows[0]["available_pairs"]) == 300
    assert len(list(csv.DictReader((current / "samples.csv").open()))) == 300
    # A repeated command must not overwrite reviewable analysis artifacts.
    with pytest.raises(SystemExit):
        main(
            [
                str(source),
                "--output",
                str(current),
                "--column",
                "value",
                "--no-plots",
            ]
        )


def test_insufficient_input_cli_has_no_fake_ess(tmp_path):
    source = tmp_path / "input.csv"
    source.write_text("guest_count\n7\n8\n7\n")
    output = tmp_path / "analysis"
    assert main([str(source), "--output", str(output), "--no-plots"]) == 0
    result = json.loads((output / "report.json").read_text())["results"][0]
    assert result["status"] == "insufficient_samples" and result["ess"] is None


def test_production_runtime_needs_explicit_cutoff(tmp_path):
    with pytest.raises(SystemExit):
        main(
            [
                str(tmp_path / "input.csv"),
                "--output",
                str(tmp_path / "analysis"),
                "--production-seconds",
                "100",
            ]
        )


def test_missing_runtime_comparison_does_not_invent_speedup():
    result = {
        "observable": "guest_count",
        "status": "ok",
        "effective_samples_per_hour": None,
        "timing_source": "unavailable",
    }
    ratio = compare_reports(
        {"results": [result]}, {"results": [result]}, matched_model=True
    )[0]
    assert ratio["efficiency_ratio"] is None


def test_comparison_rejects_different_species_and_units():
    result = {
        "observable": "guest_count",
        "unit": "molecules",
        "status": "ok",
        "effective_samples_per_hour": 10,
        "timing_source": "user_measured_production",
    }
    a = {"metadata": {"species": "CH4"}, "results": [result]}
    b = {"metadata": {"species": "CO2"}, "results": [result]}
    with pytest.raises(ValueError, match="species"):
        compare_reports(a, b)
    b = {"results": [{**result, "unit": "mmol/g"}]}
    with pytest.raises(ValueError, match="units"):
        compare_reports(a, b)
