"""Auditable CSV/JSON results and standalone correlation figures."""
from __future__ import annotations

import csv
import json
from pathlib import Path


def write_csv(path: Path, rows: list[dict], fields=None):
    fields = fields or list(dict.fromkeys(key for row in rows for key in row))
    with path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_report(output: Path, dataset, results: list[dict], acfs: dict, *, plot=True):
    output.mkdir(parents=True, exist_ok=True)
    write_csv(output/'samples.csv', dataset.rows)
    (output/'report.json').write_text(json.dumps({'metadata': dataset.metadata,
        'warnings': dataset.warnings, 'results': results}, indent=2, allow_nan=False)+'\n')
    write_csv(output/'correlation_summary.csv', [
        {k: v for k,v in result.items() if k not in ('warnings', 'subsample_indices')}
        for result in results])
    acf_rows, index_rows = [], []
    spacing = dataset.metadata['record_spacing']
    for result in results:
        observable = result['observable']
        for lag, value in enumerate(acfs[observable]):
            acf_rows.append(dict(observable=observable, lag_intervals=lag,
                lag_index_units=lag*spacing, correlation=float(value),
                available_pairs=result['n_production']-lag))
        for index in result['subsample_indices']:
            index_rows.append(dict(observable=observable, row_index=index,
                                  sample_index=dataset.rows[index]['sample_index']))
    write_csv(output/'acf.csv', acf_rows, ['observable','lag_intervals','lag_index_units','correlation','available_pairs'])
    write_csv(output/'subsample_indices.csv', index_rows, ['observable','row_index','sample_index'])
    if plot:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig, axes = plt.subplots(len(results), 2, figsize=(11, 3.5*len(results)), squeeze=False)
        for result, (series_ax, acf_ax) in zip(results, axes):
            observable = result['observable']
            indices = [r['sample_index'] for r in dataset.rows]
            series_ax.plot(indices, [r[observable] for r in dataset.rows], linewidth=0.8)
            if indices:
                cutoff = min(result['discard'],len(indices)-1)
                series_ax.axvline(indices[cutoff], color='tab:red', label='Production start')
                series_ax.legend()
            series_ax.set(xlabel=dataset.metadata['index_unit'], ylabel=observable,
                          title=result['status'])
            acf = acfs[observable]
            acf_ax.plot([i*spacing for i in range(len(acf))], acf)
            acf_ax.axhline(0, color='gray', linewidth=0.7)
            acf_ax.set(xlabel=f"Lag ({dataset.metadata['index_unit']})", ylabel='C(lag)', title=observable)
        fig.tight_layout()
        fig.savefig(output/'correlation.png', dpi=180)
        fig.savefig(output/'correlation.pdf')
        plt.close(fig)


def compare_reports(current: dict, reference: dict, *, matched_model=False) -> list[dict]:
    """Descriptive ratios; algorithmic speedup requires an explicit model-match assertion."""
    other = {r['observable']: r for r in reference['results']}
    comparisons = []
    for result in current['results']:
        baseline = other.get(result['observable'])
        if baseline is None:
            continue
        if result.get('unit') != baseline.get('unit'):
            raise ValueError(f"Cannot compare different units for {result['observable']}")
        current_species = current.get('metadata', {}).get('species')
        reference_species = reference.get('metadata', {}).get('species')
        if current_species and reference_species and current_species != reference_species:
            raise ValueError('Cannot compare different guest species as the same observable')
        a, b = result['effective_samples_per_hour'], baseline['effective_samples_per_hour']
        comparison = dict(observable=result['observable'], efficiency_ratio=None,
            interpretation='user_asserted_matched_model' if matched_model else 'descriptive_only_model_match_unverified',
            current_timing_source=result['timing_source'], reference_timing_source=baseline['timing_source'])
        if result['status'] == baseline['status'] == 'ok' and a is not None and b is not None and b > 0:
            comparison['efficiency_ratio'] = a/b
        comparisons.append(comparison)
    return comparisons
