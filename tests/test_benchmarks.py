"""Shared-control sampling, multiplicity, truthful metrics, and repeated benchmark artifacts."""
from dataclasses import replace
import numpy as np
import pytest
from app.configuration import make_config
from src.models.artifacts import load_model
from src.simulation.stress import STRESS_CASES,generate_stress,holm_adjust,select_variant,shared_control_covariance
from scripts.run_benchmarks import evaluate_portfolio
from app.benchmark_view import load_report


def test_holm_known_adjustment_and_one_launch_per_experiment():
    assert holm_adjust([.01,.04,.03]).tolist()==pytest.approx([.03,.06,.06])
    p=generate_stress(make_config('retention'),'abn',902,20)
    for group in p.observed:
        choice=select_variant(group)
        assert choice is None or 0<=choice<4
        assert len({r.control_successes for r in group.contrasts})==1
        assert group.covariance.shape==(4,4)
        assert np.linalg.eigvalsh(group.covariance).min()>0


def test_empirical_shared_control_covariance_matches_binomial_sampling():
    rng=np.random.default_rng(553)
    nc=2000;nt=np.array([2500,3000]);pc=.24;pt=np.array([.26,.22]);reps=50000
    xc=rng.binomial(nc,pc,reps);xt=rng.binomial(nt,pt,(reps,2))
    effects=xt/nt-xc[:,None]/nc
    observed=np.cov(effects,rowvar=False)
    theoretical=np.full((2,2),pc*(1-pc)/nc)+np.diag(pt*(1-pt)/nt)
    assert np.allclose(observed,theoretical,rtol=.035,atol=0)
    estimated=shared_control_covariance(int(nc*pc),nc,np.rint(nt*pt).astype(int),nt)
    assert np.allclose(estimated,theoretical,rtol=.003)


@pytest.mark.parametrize('case',list(STRESS_CASES))
def test_stress_reproducible_and_probabilities_valid(case):
    config=make_config('upworthy_ctr' if case=='archive_ctr' else 'retention')
    first=generate_stress(config,case,773,10);second=generate_stress(config,case,773,10)
    assert first.effects==second.effects
    for a,b in zip(first.observed,second.observed):
        assert a.contrasts==b.contrasts
        assert np.array_equal(a.covariance,b.covariance)
        for row in a.contrasts:
            assert 0<=row.control_successes<=row.control_n
            assert 0<=row.treatment_successes<=row.treatment_n
    if case=='null':assert all(t==0 for group in first.effects for t in group)


def test_truth_does_not_change_selection_and_empty_launch_metrics():
    config=make_config('retention');portfolio=generate_stress(config,'null',175,20)
    altered=replace(portfolio,effects=tuple(tuple(.25 for _ in row) for row in portfolio.effects))
    assert [select_variant(r) for r in portfolio.observed]==[select_variant(r) for r in altered.observed]
    # No reviewed experiments means no invented conditional accuracy, but additive empty sum is zero.
    empty=replace(portfolio,observed=(),effects=())
    models={m:load_model(config,estimator=m) for m in ['empirical_bayes','hierarchical','robust']}
    result=evaluate_portfolio(empty,models,.05)
    assert result['metrics']['naive']['mae_pp'] is None
    assert result['metrics']['naive']['cumulative_absolute_error_conversions']==0
    result=evaluate_portfolio(portfolio,models,.05)
    assert result['metrics']['naive']['decision_regret_conversions']==0


def test_report_has_real_replications_and_matching_estimator_populations():
    report=load_report()
    assert report['replications']>=30
    for result in report['cases'].values():
        counts=[v['selected_supported'] for v in result['methods'].values()]
        assert len(set(counts))==1
        for method in result['methods'].values():
            assert method['mae_pp']['replications']<=report['replications']


def test_holm_controls_false_launches_under_shared_control_null():
    from scipy.stats import norm
    rng=np.random.default_rng(781);replications=5000;n=2500;p=.24
    xc=rng.binomial(n,p,replications);xt=rng.binomial(n,p,(replications,4))
    pooled=(xt+xc[:,None])/(2*n)
    z=(xt/n-xc[:,None]/n)/np.sqrt(pooled*(1-pooled)*2/n)
    raw=2*norm.sf(abs(z))
    adjusted=np.array([holm_adjust(row) for row in raw])
    family_rejection=np.mean((adjusted<.05).any(axis=1))
    assert family_rejection<.06
    assert np.mean((raw<.05).any(axis=1))>.08
