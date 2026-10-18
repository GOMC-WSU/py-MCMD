"""Offline PyMBAR analysis: python -m py_mcmd_refactored.cli.analyze --help."""

from __future__ import annotations

import argparse
import json
import sys
from importlib.metadata import version
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from py_mcmd_refactored.analysis.correlation import analyze
from py_mcmd_refactored.analysis.readers import read_csv, read_hybrid, read_mc
from py_mcmd_refactored.analysis.reporting import (
    compare_reports,
    write_csv,
    write_report,
)


def parser():
    p = argparse.ArgumentParser(
        description="Calculate observable-specific ACF/ESS with PyMBAR, without running simulation engines."
    )
    p.add_argument(
        "input",
        type=Path,
        help="Hybrid run directory, standalone GOMC directory, or CSV file",
    )
    p.add_argument(
        "--mode", choices=["auto", "hybrid", "mc", "csv"], default="auto"
    )
    p.add_argument(
        "--output",
        type=Path,
        required=True,
        help="New analysis directory (raw input files are never edited)",
    )
    p.add_argument("--species", default="CH4")
    p.add_argument(
        "--kind-index",
        type=int,
        help="Zero-based histogram species column; overrides automatic species mapping",
    )
    p.add_argument(
        "--histogram", help="MC histogram filename relative to input directory"
    )
    p.add_argument(
        "--console",
        action="store_true",
        help="Use instantaneous console records for standalone MC",
    )
    p.add_argument(
        "--column",
        default="guest_count",
        help="Observable column for CSV input",
    )
    p.add_argument(
        "--observable",
        action="append",
        help="Select observable(s); default analyzes loading and available nonbonded energy",
    )
    p.add_argument(
        "--discard",
        type=int,
        help="Explicit number of saved records to discard; default is PyMBAR detection",
    )
    p.add_argument(
        "--nskip",
        type=int,
        default=10,
        help="Stride of candidate equilibration cutoffs, not data thinning",
    )
    p.add_argument("--mintime", type=int, default=3)
    p.add_argument("--max-lag", type=int, default=200)
    p.add_argument(
        "--min-samples",
        type=int,
        default=20,
        help="Minimum raw and production records for estimates (>=4); not a convergence criterion",
    )
    p.add_argument(
        "--runtime-seconds",
        type=float,
        help="Measured total acquisition runtime for exactly the supplied series",
    )
    p.add_argument(
        "--production-seconds",
        type=float,
        help="Measured acquisition runtime for the selected retained region",
    )
    p.add_argument(
        "--uniform-cost",
        action="store_true",
        help="Estimate production runtime from total runtime proportional to retained record count",
    )
    p.add_argument(
        "--compare",
        type=Path,
        help="Reference report.json or analysis directory",
    )
    p.add_argument(
        "--matched-model",
        action="store_true",
        help="Assert that the reference has the same physical model, state and hardware allocation",
    )
    p.add_argument("--no-plots", action="store_true")
    return p


def main(argv=None):
    p = parser()
    args = p.parse_args(argv)
    try:
        if (
            args.output.resolve() == args.input.resolve()
            or args.output.exists()
            and any(args.output.iterdir())
        ):
            raise ValueError(
                "Output must be a separate empty/new directory; choose a new analysis directory"
            )
        if args.matched_model and args.compare is None:
            raise ValueError("--matched-model requires --compare")
        if args.production_seconds is not None and args.discard is None:
            raise ValueError(
                "--production-seconds requires an explicit --discard so the measured time has a defined production region"
            )
        mode = args.mode
        if mode == "auto":
            mode = (
                "csv"
                if args.input.is_file()
                else "hybrid" if (args.input / "GOMC").is_dir() else "mc"
            )
        if mode == "csv":
            dataset = read_csv(args.input, args.column)
        elif mode == "hybrid":
            if args.console or args.histogram or args.kind_index is not None:
                raise ValueError(
                    "Hybrid analysis uses completed console endpoints; histogram options apply to standalone MC"
                )
            dataset = read_hybrid(args.input, args.species)
        else:
            dataset = read_mc(
                args.input,
                args.species,
                args.kind_index,
                args.histogram,
                args.console,
            )
        observables = args.observable or (
            [args.column]
            if mode == "csv"
            else ["guest_count"]
            + (
                ["nonbonded_energy_kcal_mol"]
                if dataset.rows
                and all("nonbonded_energy_kcal_mol" in r for r in dataset.rows)
                else []
            )
        )
        if not observables:
            raise ValueError("No observables selected")
        observables = list(dict.fromkeys(observables))
        for observable in observables:
            if dataset.rows and not all(
                observable in row for row in dataset.rows
            ):
                raise ValueError(
                    f"Observable {observable} is missing from some records"
                )
        costs = [r.get("acquisition_seconds") for r in dataset.rows]
        costs = costs if costs and all(c is not None for c in costs) else None
        # Explicit global timing supersedes historical cycle timings. Never combine
        # full-job total with incomplete cycle-only production cost implicitly.
        if (
            args.runtime_seconds is not None
            or args.production_seconds is not None
        ):
            costs = None
        results, acfs = [], {}
        for observable in observables:
            result, acf = analyze(
                [r[observable] for r in dataset.rows],
                discard=args.discard,
                nskip=args.nskip,
                mintime=args.mintime,
                max_lag=args.max_lag,
                min_samples=args.min_samples,
                acquisition_seconds=costs,
                runtime_seconds=args.runtime_seconds,
                production_seconds=args.production_seconds,
                uniform_cost=args.uniform_cost,
            )
            result["observable"] = observable
            result["unit"] = (
                "molecules"
                if observable == "guest_count"
                else (
                    "kcal/mol"
                    if observable == "nonbonded_energy_kcal_mol"
                    else "user_defined"
                )
            )
            result["tau_index_units"] = (
                None
                if result["g"] is None
                else result["tau_pymbar_intervals"]
                * dataset.metadata["record_spacing"]
            )
            if (
                mode == "hybrid"
                and result["timing_source"] == "record_acquisition_intervals"
            ):
                result["timing_source"] = (
                    "reconstructed_cycle_timings_incomplete_job_coverage"
                )
            results.append(result)
            acfs[observable] = acf
        dataset.metadata.update(
            input=str(args.input.resolve()),
            pymbar_version=version("pymbar"),
            numpy_version=version("numpy"),
            algorithm="pymbar.timeseries",
            options={
                k: str(v) if isinstance(v, Path) else v
                for k, v in vars(args).items()
            },
            comparison_model_match="not_verified",
            analysis_version=1,
        )
        report = {
            "metadata": dataset.metadata,
            "warnings": dataset.warnings,
            "results": results,
        }
        comparisons = None
        if args.compare:
            reference_path = (
                args.compare / "report.json"
                if args.compare.is_dir()
                else args.compare
            )
            reference = json.loads(reference_path.read_text())
            comparisons = compare_reports(
                report, reference, matched_model=args.matched_model
            )
        write_report(
            args.output, dataset, results, acfs, plot=not args.no_plots
        )
        if comparisons is not None:
            (args.output / "comparison.json").write_text(
                json.dumps(comparisons, indent=2, allow_nan=False) + "\n"
            )
            write_csv(
                args.output / "efficiency_comparison.csv",
                comparisons,
                [
                    "observable",
                    "efficiency_ratio",
                    "interpretation",
                    "current_timing_source",
                    "reference_timing_source",
                ],
            )
        for warning in dataset.warnings:
            print(f"Warning: {warning}", file=sys.stderr)
        for result in results:
            print(
                f"{result['observable']}: status={result['status']}, production records={result['n_production']}, "
                f"g={result['g']}, ESS={result['ess']}, effective samples/hour={result['effective_samples_per_hour']}"
            )
            for warning in result["warnings"]:
                print(
                    f'Warning ({result["observable"]}): {warning}',
                    file=sys.stderr,
                )
        print(f'Report: {args.output / "report.json"}')
        return 0
    except (ValueError, KeyError, IndexError, OSError, ImportError) as exc:
        p.error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
