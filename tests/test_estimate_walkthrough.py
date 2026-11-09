"""Explanations must reproduce predictions, not invent a simpler model."""
import pytest
from app.configuration import make_config
from app.estimate_walkthrough import explanation_parts
from src.models.artifacts import load_model,correct_observations
from src.simulation.engine import generate_observed


@pytest.mark.parametrize('scenario',['retention','acquisition','onboarding','monetization','upworthy_ctr'])
@pytest.mark.parametrize('method',['empirical_bayes','hierarchical','robust'])
def test_numeric_walkthrough_reconstructs_predictor_across_effects(scenario,method):
    config=make_config(scenario)
    observed=sorted(generate_observed(config),key=lambda r:r.estimate.effect)
    items=[observed[0],observed[len(observed)//2],observed[-1]]
    artifact=load_model(config,estimator=method)
    predicted,unsupported=correct_observations(items,[r.experiment_id for r in items],artifact)
    assert predicted
    for item in items:
        if item.experiment_id in unsupported:continue
        p=predicted[item.experiment_id]
        d=explanation_parts(item.estimate.effect,p.model_se,artifact)
        assert d['mean']==pytest.approx(p.mean,abs=1e-12)
        assert d['history_weight']==pytest.approx(p.prior_weight,abs=1e-12)
        w=d['history_weight']
        assert (1-w)*item.estimate.effect+w*d['center']==pytest.approx(p.mean,abs=1e-12)
        if method=='robust':
            q=d['wide_probability']
            assert 0<=q<=1
            assert (1-q)*d['narrow_mean']+q*d['wide_mean']==pytest.approx(p.mean,abs=1e-12)
