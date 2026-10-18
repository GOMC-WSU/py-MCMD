"""PyMBAR estimates on validated, regularly spaced scalar observations."""
from __future__ import annotations

import math
import numpy as np


def analyze(values, *, discard=None, nskip=1, mintime=3, max_lag=200, min_samples=20,
            acquisition_seconds=None, runtime_seconds=None, production_seconds=None,
            uniform_cost=False):
    if nskip < 1 or mintime < 0 or max_lag < 1 or min_samples < 4:
        raise ValueError('Invalid analysis options (minimum samples must be at least 4)')
    for name, number in [('runtime_seconds', runtime_seconds), ('production_seconds', production_seconds)]:
        if number is not None and (not math.isfinite(number) or number <= 0):
            raise ValueError(f'{name} must be finite and positive')
    if runtime_seconds is not None and production_seconds is not None and production_seconds > runtime_seconds:
        raise ValueError('Production runtime cannot exceed total runtime')
    x = np.asarray(values, dtype=float)
    if x.ndim != 1:
        raise ValueError('Expected a one-dimensional observable')
    if discard is not None and (discard < 0 or discard >= len(x)):
        raise ValueError('Discard must leave at least one record')
    result = dict(status='ok', n_input=len(x), discard=discard or 0, n_production=0,
                  mean=None, sem=None, g=None, tau_pymbar_intervals=None, ess=None,
                  total_seconds=runtime_seconds, production_seconds=None,
                  timing_source='unavailable', effective_samples_per_hour=None,
                  seconds_per_effective_sample=None, effective_samples_per_total_hour=None,
                  subsample_indices=[], warnings=[])
    empty_acf = np.array([], dtype=float)
    if not len(x):
        result['status'] = 'empty'
        return result, empty_acf
    if not np.isfinite(x).all():
        result['status'] = 'nonfinite'
        return result, empty_acf
    result.update(n_production=len(x)-(discard or 0), mean=float(x[discard or 0:].mean()))
    if len(x) < min_samples:
        result['status'] = 'insufficient_samples'
        return result, empty_acf
    if x.std() == 0:
        result['status'] = 'constant'
        return result, empty_acf
    try:
        from pymbar import timeseries
    except ImportError as exc:
        raise ImportError('Install offline analysis dependencies: python -m pip install -r requirements-analysis.txt') from exc
    t0 = discard
    if t0 is None:
        t0, _, _ = timeseries.detect_equilibration(x, fast=False, nskip=nskip)
        t0 = int(t0)
    production = x[t0:]
    result.update(discard=t0, n_production=len(production), mean=float(production.mean()))
    if len(production) < min_samples:
        result['status'] = 'insufficient_production_samples'
        return result, empty_acf
    if production.std() == 0:
        result['status'] = 'constant_production'
        return result, empty_acf
    g = float(timeseries.statistical_inefficiency(production, fast=False, mintime=mintime))
    acf = timeseries.normalized_fluctuation_correlation_function(production, N_max=min(max_lag, len(production)-1))
    ess = len(production) / g
    result.update(g=g, ess=ess, tau_pymbar_intervals=(g-1)/2,
                  sem=float(production.std(ddof=1) / math.sqrt(ess)),
                  subsample_indices=[t0+int(i) for i in timeseries.subsample_correlated_data(production, g=g, conservative=True)])
    if ess < 50:
        result['warnings'].append('Fewer than 50 estimated effective samples; correlation estimates need longer runs/replica checks. This is a diagnostic threshold, not a convergence test.')
    if len(acf) > 1 and acf[-1] > 0.1:
        result['warnings'].append('ACF remains positive at the plotted maximum lag; inspect the tail and extend the lag/run.')
    if acquisition_seconds is not None:
        costs = np.asarray(acquisition_seconds, dtype=float)
        if costs.shape != x.shape or not np.isfinite(costs).all() or (costs <= 0).any():
            raise ValueError('Every acquisition_seconds value must be finite, positive and correspond to one sample')
        if runtime_seconds is None:
            result['total_seconds'] = float(costs.sum())
        result['production_seconds'] = float(costs[t0:].sum())
        result['timing_source'] = 'record_acquisition_intervals'
    if production_seconds is not None:
        result['production_seconds'] = production_seconds
        result['timing_source'] = 'user_measured_production'
    elif runtime_seconds is not None and uniform_cost:
        result['production_seconds'] = runtime_seconds * len(production) / len(x)
        result['timing_source'] = 'user_runtime_uniform_cost'
        result['warnings'].append('Production runtime estimated under uniform cost per recorded interval; excludes unrecorded warmup only if the supplied runtime does.')
    if result['production_seconds'] is not None:
        seconds = result['production_seconds']
        result.update(effective_samples_per_hour=3600*ess/seconds, seconds_per_effective_sample=seconds/ess)
    if result['total_seconds'] is not None:
        result['effective_samples_per_total_hour'] = 3600*ess/result['total_seconds']
    return result, np.asarray(acf)
