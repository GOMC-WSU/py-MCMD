"""Read instantaneous GOMC observations without mixing MD and MC records."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path

from py_mcmd_refactored.utils.config_sections import flatten_config_sections

K_TO_KCAL_MOL = 0.00198720425864083


@dataclass
class Dataset:
    rows: list[dict]
    metadata: dict
    warnings: list[str] = field(default_factory=list)


def configuration(path: Path) -> dict[str, list[list[str]]]:
    result: dict[str, list[list[str]]] = {}
    for line in path.read_text().splitlines():
        words = line.split("#", 1)[0].split()
        if words:
            result.setdefault(words[0].lower(), []).append(words[1:])
    return result


def _integer(cfg: dict, name: str) -> int:
    try:
        return int(cfg[name.lower()][0][-1])
    except (KeyError, ValueError, IndexError) as exc:
        raise ValueError(
            f"Missing or invalid {name} in GOMC configuration"
        ) from exc


def _protocol(cfg: dict, directory: Path) -> dict:
    # Ignore paths and stochastic seeds; preserve thermodynamics and transition settings.
    keys = {
        "temperature",
        "fugacity",
        "chempot",
        "potential",
        "rswitch",
        "rcut",
        "rcutlow",
        "lrc",
        "exclude",
        "1-4scaling",
        "electrostatic",
        "ewald",
        "tolerance",
        "runsteps",
        "eqsteps",
        "adjsteps",
        "swapfreq",
        "disfreq",
        "rotfreq",
        "regrowthfreq",
        "intraswapfreq",
        "cbmc_first",
        "cbmc_nth",
        "cbmc_ang",
        "cbmc_dih",
        "cellbasisvector1",
        "cellbasisvector2",
        "cellbasisvector3",
    }
    result = {k: v for k, v in sorted(cfg.items()) if k in keys}
    hashes = []
    for values in cfg.get("parameters", []):
        if len(values) != 1:
            raise ValueError(
                "Parameter paths containing spaces are not supported"
            )
        path = directory / values[0]
        hashes.append(
            hashlib.sha256(path.read_bytes()).hexdigest()
            if path.is_file()
            else "unavailable"
        )
    result["parameter_sha256"] = hashes
    return result


def _number(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"Nonfinite GOMC value: {value}")
    return number


def console_records(
    path: Path, species: str = "CH4", box: int = 0
) -> tuple[list[dict], list[str]]:
    """Join energy and statistics by local step; preserve repeated species kinds."""
    headers = {}
    statistics, energies = {}, {}
    kinds: list[str] = []
    for line_no, line in enumerate(path.read_text().splitlines(), 1):
        tokens = line.split()
        if not tokens:
            continue
        label = tokens[0]
        if label in ("ETITLE:", "STITLE:"):
            titles = tokens[1:]
            if label in headers and headers[label] != titles:
                raise ValueError(
                    f"{path}:{line_no}: changed thermodynamic header"
                )
            headers[label] = titles
            if label == "STITLE:":
                kinds = [
                    t[len("MOLFRAC_") :]
                    for t in titles
                    if t.startswith("MOLFRAC_")
                ]
            continue
        if label not in (f"STAT_{box}:", f"ENER_{box}:"):
            continue
        header = "STITLE:" if label.startswith("STAT") else "ETITLE:"
        titles = headers.get(header)
        if not titles or len(tokens) - 1 != len(titles):
            raise ValueError(
                f"{path}:{line_no}: missing header or invalid row width"
            )
        values = [_number(v) for v in tokens[1:]]
        step = values[titles.index("STEP")]
        if step < 0 or step != int(step):
            raise ValueError(f"{path}:{line_no}: invalid STEP")
        step = int(step)
        target = statistics if header == "STITLE:" else energies
        if header == "STITLE:":
            total_name = "TOTALMOL" if "TOTALMOL" in titles else "TOT_MOL"
            total = values[titles.index(total_name)]
            indices = [
                i
                for i, title in enumerate(titles)
                if title == f"MOLFRAC_{species}"
            ]
            if not indices:
                raise ValueError(
                    f"{path}: no MOLFRAC_{species}; use a histogram with --kind-index"
                )
            fraction = sum(values[i] for i in indices)
            count = total * fraction
            nearest = round(count)
            if (
                nearest < 0
                or fraction < 0
                or fraction > 1.000001
                or abs(nearest - count) > 1e-4
            ):
                raise ValueError(
                    f"{path}:{line_no}: species count is not a nonnegative integer"
                )
            record = {"guest_count": nearest}
        else:
            # Histogram uses inter + LRC + total electrostatics, not bonded energy.
            components = ("INTER(LJ)", "LRC", "TOTAL_ELECT")
            record = {}
            if all(t in titles for t in components):
                record["nonbonded_energy_kcal_mol"] = (
                    sum(values[titles.index(t)] for t in components)
                    * K_TO_KCAL_MOL
                )
        if step in target and target[step] != record:
            raise ValueError(
                f"{path}:{line_no}: conflicting duplicate step {step}"
            )
        target[step] = record
    if not statistics:
        raise ValueError(f"{path}: no box-{box} statistics")
    rows = []
    for step, stat in sorted(statistics.items()):
        rows.append({"local_step": step, **stat, **energies.get(step, {})})
    return rows, kinds


def histogram_records(
    path: Path,
    cfg: dict,
    kinds: list[str],
    species: str,
    kind_index: int | None = None,
) -> tuple[list[dict], list[str]]:
    lines = path.read_text().splitlines()
    if not lines:
        raise ValueError(f"{path}: empty histogram")
    header = lines[0].split()
    try:
        n_kinds = int(header[1])
        if n_kinds < 1 or len(header) != n_kinds + 5:
            raise ValueError("invalid header width")
        for value in header:
            _number(value)
    except (IndexError, ValueError) as exc:
        raise ValueError(f"{path}: invalid histogram header") from exc
    if kind_index is None:
        if len(kinds) != n_kinds or species not in kinds:
            raise ValueError(
                "Cannot identify histogram species order; supply --kind-index (zero-based)"
            )
        indices = [i for i, name in enumerate(kinds) if name == species]
    else:
        if kind_index < 0 or kind_index >= n_kinds:
            raise ValueError("Histogram kind index out of range")
        indices = [kind_index]
    if "initstep" in cfg and _integer(cfg, "InitStep") != 0:
        raise ValueError(
            "Histogram reconstruction currently requires InitStep 0; use console data"
        )
    spacing = _integer(cfg, "SampleFreq")
    write_spacing = _integer(cfg, "HistogramFreq")
    eq = _integer(cfg, "EqSteps")
    run_steps = _integer(cfg, "RunSteps")
    if spacing <= 0 or write_spacing <= 0 or write_spacing % spacing:
        raise ValueError(
            "HistogramFreq must be a positive multiple of SampleFreq"
        )
    first = (eq // spacing + 1) * spacing
    # The GOMC histogram writer does not flush samples at an off-frequency final step.
    last_written = run_steps // write_spacing * write_spacing
    steps = range(first, last_written + 1, spacing)
    data_lines = [line for line in lines[1:] if line.strip()]
    if len(data_lines) > len(steps):
        raise ValueError(
            f"{path}: too many samples for the configured observation grid"
        )
    rows = []
    for index, line in enumerate(data_lines):
        fields = line.split()
        if len(fields) != n_kinds + 1:
            raise ValueError(f"{path}: malformed histogram record {index+1}")
        counts = [_number(v) for v in fields[:-1]]
        if any(v < 0 or v != int(v) for v in counts):
            raise ValueError(f"{path}: invalid species counts")
        rows.append(
            {
                "local_step": steps[index],
                "guest_count": sum(int(counts[i]) for i in indices),
                "nonbonded_energy_kcal_mol": _number(fields[-1])
                * K_TO_KCAL_MOL,
            }
        )
    warnings = [
        "Histogram step labels reconstructed from EqSteps/SampleFreq, assuming a contiguous file."
    ]
    if len(rows) != len(steps):
        warnings.append(
            "Incomplete histogram prefix: configured final samples are missing; full-job runtime cannot be assigned to this prefix."
        )
    if not rows:
        raise ValueError(f"{path}: no instantaneous samples")
    return rows, warnings


def _cycle_timings(root: Path) -> dict[int, float]:
    result = {}
    for path in sorted((root / "logs").glob("*.log")):
        for line in path.read_text().splitlines():
            if not line.startswith("TIME_STATS_DATA:"):
                continue
            fields = line.split()
            if len(fields) != 6:
                raise ValueError(f"{path}: malformed TIME_STATS_DATA")
            cycle, seconds = int(fields[1]), _number(fields[-1])
            if seconds <= 0 or cycle in result and result[cycle] != seconds:
                raise ValueError(f"{path}: invalid or conflicting cycle timing")
            result[cycle] = seconds
    return result


def read_hybrid(root: Path, species: str = "CH4") -> Dataset:
    dirs = sorted(
        (
            p
            for p in (root / "GOMC").iterdir()
            if p.is_dir() and p.name.isdigit()
        ),
        key=lambda p: int(p.name),
    )
    if not dirs:
        raise ValueError(f"{root}: no numbered GOMC segment directories")
    timings = _cycle_timings(root)
    rows, warnings, protocols = [], [], []
    for directory in dirs:
        run = int(directory.name)
        if run % 2 != 1:
            raise ValueError(f"{directory}: hybrid GOMC run number must be odd")
        cfg = configuration(directory / "in.conf")
        protocols.append(_protocol(cfg, directory))
        records, _ = console_records(directory / "out.dat", species)
        expected = _integer(cfg, "RunSteps")
        endpoint = next(
            (r for r in records if r["local_step"] == expected), None
        )
        if endpoint is None:
            raise ValueError(
                f"{directory}: missing completed segment endpoint {expected}"
            )
        cycle = run // 2
        rows.append(
            {
                "sample_index": cycle,
                "cycle": cycle,
                "segment_id": run,
                "phase": "post_gomc",
                "source": str(directory / "out.dat"),
                "acquisition_seconds": timings.get(cycle),
                **endpoint,
            }
        )
    if any(b["cycle"] - a["cycle"] != 1 for a, b in zip(rows, rows[1:])):
        raise ValueError(
            "Missing hybrid cycles; analyze contiguous pieces separately"
        )
    if any(p != protocols[0] for p in protocols[1:]):
        raise ValueError(
            "GOMC protocol or force field changed across segments; analyze separate conditions"
        )
    if "unavailable" in protocols[0]["parameter_sha256"]:
        warnings.append(
            "Some parameter files are unavailable locally; their force-field hashes could not be checked."
        )
    if all(row["acquisition_seconds"] is not None for row in rows):
        warnings.append(
            "Runtime reconstructed from cycle timings: excludes initial setup/final worker drain and is not complete job timing."
        )
    else:
        warnings.append(
            "Complete per-cycle timing unavailable; supply measured runtime for throughput."
        )
    warnings.append(
        "Protocol checks cover GOMC controls only; confirm unchanged NAMD settings and framework/move-scale policy across restarts."
    )
    for cfg in root.glob("*.json"):
        try:
            settings = flatten_config_sections(json.loads(cfg.read_text()))
        except (ValueError, OSError):
            continue
        if (
            "starting_at_cycle_namd_gomc_sims" in settings
            and rows[0]["cycle"] < settings["starting_at_cycle_namd_gomc_sims"]
        ):
            warnings.append(
                "Directory contains parent cycles before the configured continuation; copied parents must not be counted as independent replicas."
            )
            break
    return Dataset(
        rows,
        {
            "mode": "hybrid",
            "species": species,
            "index_unit": "hybrid_cycles",
            "record_spacing": 1,
            "protocol": protocols[0],
        },
        warnings,
    )


def read_mc(
    root: Path,
    species: str = "CH4",
    kind_index: int | None = None,
    histogram: str | None = None,
    console: bool = False,
) -> Dataset:
    cfg = configuration(root / "in.conf")
    kinds = []
    if (root / "out.dat").exists():
        for line in (root / "out.dat").read_text().splitlines():
            if line.startswith("STITLE:"):
                kinds = [
                    t[len("MOLFRAC_") :]
                    for t in line.split()[1:]
                    if t.startswith("MOLFRAC_")
                ]
                break
    if console:
        if not (root / "out.dat").exists():
            raise ValueError("Console input requires out.dat")
        console_rows, _ = console_records(root / "out.dat", species)
        rows, warnings, source = console_rows, [], root / "out.dat"
    else:
        paths = (
            [root / histogram] if histogram else sorted(root.glob("his*.dat"))
        )
        if len(paths) != 1:
            raise ValueError(
                "Expected one instantaneous his*.dat file; supply --histogram or --console"
            )
        source = paths[0]
        rows, warnings = histogram_records(
            source, cfg, kinds, species, kind_index
        )
    spacing = (
        rows[1]["local_step"] - rows[0]["local_step"]
        if len(rows) > 1
        else _integer(cfg, "SampleFreq" if not console else "ConsoleFreq")
    )
    if spacing <= 0 or any(
        b["local_step"] - a["local_step"] != spacing
        for a, b in zip(rows, rows[1:])
    ):
        raise ValueError(
            "Irregular MC observation grid; select a regular contiguous series"
        )
    for row in rows:
        row.update(
            sample_index=row["local_step"],
            phase="post_mc_move",
            source=str(source),
        )
    warnings.append(
        "Runtime not inferred from file modification times; supply measured acquisition time for throughput."
    )
    protocol = _protocol(cfg, root)
    if "unavailable" in protocol["parameter_sha256"]:
        warnings.append(
            "Some parameter files are unavailable locally; their force-field hashes could not be checked."
        )
    return Dataset(
        rows,
        {
            "mode": "mc",
            "species": species,
            "index_unit": "attempted_mc_moves",
            "record_spacing": spacing,
            "protocol": protocol,
        },
        warnings,
    )


def read_csv(path: Path, column: str = "guest_count") -> Dataset:
    with path.open(newline="") as handle:
        records = list(csv.DictReader(handle))
    rows = []
    for i, record in enumerate(records):
        row = {
            "sample_index": float(record.get("sample_index", i)),
            column: float(record[column]),
            "source": str(path),
            "phase": "csv",
        }
        if not math.isfinite(row["sample_index"]):
            raise ValueError("CSV sample_index must be finite")
        if record.get("acquisition_seconds"):
            row["acquisition_seconds"] = _number(record["acquisition_seconds"])
            if row["acquisition_seconds"] <= 0:
                raise ValueError("acquisition_seconds must be positive")
        rows.append(row)
    spacing = (
        rows[1]["sample_index"] - rows[0]["sample_index"]
        if len(rows) > 1
        else 1
    )
    if spacing <= 0 or any(
        not math.isclose(
            b["sample_index"] - a["sample_index"],
            spacing,
            rel_tol=1e-9,
            abs_tol=1e-12,
        )
        for a, b in zip(rows, rows[1:])
    ):
        raise ValueError(
            "CSV sample_index must be finite, increasing and regularly spaced"
        )
    return Dataset(
        rows,
        {
            "mode": "csv",
            "index_unit": "sample_index",
            "record_spacing": spacing,
        },
        [],
    )
