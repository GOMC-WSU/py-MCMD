import numpy as np
import pytest
timeseries = pytest.importorskip('pymbar.timeseries')

from py_mcmd_refactored.analysis.correlation import analyze


def ar1(n=40000, phi=0.8):
    rng = np.random.default_rng(417)
    noise = rng.normal(size=n+1000)
    x = np.zeros(n+1000)
    for i in range(1, len(x)):
        x[i] = phi*x[i-1]+noise[i]
    return x[1000:]


def test_ar1_theory_and_exact_pymbar_agreement():
    x = ar1()
    result, acf = analyze(x, discard=0, max_lag=25)
    assert result['g'] == pytest.approx((1+0.8)/(1-0.8), rel=0.15)
    assert result['g'] == timeseries.statistical_inefficiency(x, fast=False)
    np.testing.assert_allclose(acf, timeseries.normalized_fluctuation_correlation_function(x, N_max=25))
    np.testing.assert_allclose(acf[:6], 0.8**np.arange(6), atol=0.035)
    assert result['ess'] == len(x)/result['g']
    assert result['tau_pymbar_intervals'] == (result['g']-1)/2


def test_units_and_sample_indices():
    x = ar1(3000)
    a, acf_a = analyze(x, discard=40)
    b, acf_b = analyze(-7*x+100, discard=40)
    assert a['g'] == pytest.approx(b['g'])
    np.testing.assert_allclose(acf_a, acf_b, atol=1e-12)
    assert a['subsample_indices'][0] == 40
    assert max(a['subsample_indices']) < len(x)
    assert len(set(a['subsample_indices'])) == len(a['subsample_indices'])


def test_white_noise():
    result, _ = analyze(np.random.default_rng(917).normal(size=20000), discard=0)
    assert result['g'] == pytest.approx(1, abs=0.1)


@pytest.mark.parametrize('values,discard,status', [
    ([], None, 'empty'), ([1, float('nan')], None, 'nonfinite'),
    ([1,2,3], None, 'insufficient_samples'), (np.ones(40), None, 'constant'),
    (np.r_[np.arange(20),np.ones(30)], 20, 'constant_production'),
    (np.arange(40), 30, 'insufficient_production_samples'),
])
def test_invalid_or_inadequate_series_never_yield_throughput(values, discard, status):
    result, acf = analyze(values, discard=discard, runtime_seconds=100)
    assert result['status'] == status
    assert result['g'] is None and result['ess'] is None
    assert result['effective_samples_per_hour'] is None
    assert not len(acf)


def test_equilibration_recomputes_retained_length():
    x = np.r_[np.full(50, 30.0), ar1(1000)]
    result, _ = analyze(x, nskip=10)
    assert result['discard'] >= 40
    assert result['ess'] == result['n_production']/result['g']


def test_timing_exact_intervals_and_override():
    x = ar1(100)
    costs = np.arange(1, 101)
    result, _ = analyze(x, discard=20, acquisition_seconds=costs)
    assert result['production_seconds'] == costs[20:].sum()
    assert result['total_seconds'] == costs.sum()
    assert result['effective_samples_per_hour'] == 3600*result['ess']/costs[20:].sum()
    measured, _ = analyze(x, discard=20, runtime_seconds=500, production_seconds=400)
    assert measured['timing_source'] == 'user_measured_production'
    assert measured['seconds_per_effective_sample'] == 400/measured['ess']


def test_total_runtime_does_not_invent_production_cost():
    x = ar1(100)
    result, _ = analyze(x, discard=20, runtime_seconds=500)
    assert result['production_seconds'] is None
    assert result['effective_samples_per_hour'] is None
    assert result['effective_samples_per_total_hour'] == 3600*result['ess']/500
    assumed, _ = analyze(x, discard=20, runtime_seconds=500, uniform_cost=True)
    assert assumed['production_seconds'] == 400
    assert 'uniform' in assumed['timing_source']


@pytest.mark.parametrize('options', [{'discard':100}, {'discard':-1}, {'nskip':0},
    {'min_samples':3}, {'runtime_seconds':0}, {'runtime_seconds':float('nan')},
    {'runtime_seconds':5,'production_seconds':6}, {'acquisition_seconds':[1,2]}])
def test_invalid_options(options):
    with pytest.raises(ValueError):
        analyze(ar1(100), **options)
