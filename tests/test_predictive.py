"""Check predictive integration independently of posterior effect estimation."""
import json
from pathlib import Path
import numpy as np
import pytest
from scipy.stats import norm
from app.configuration import make_config
from src.models.artifacts import load_model,content_id
from src.models.predictive import predictive_scores


def test_normal_predictive_matches_analytic_convolution():
    model={'model_version':'normal-normal-rd-v1','fit':{'mean':.01,'variance':.02**2}}
    y=np.array([-.04,.01,.06]);se=np.array([.01,.03,.02])
    score,pit=predictive_scores(y,se,model)
    scale=np.sqrt(se**2+.02**2)
    assert score==pytest.approx(norm.logpdf(y,.01,scale))
    assert pit==pytest.approx(norm.cdf(y,.01,scale))
    with pytest.raises(ValueError):predictive_scores(y,[0,.01,.01],model)


def test_predictive_checks_use_matching_frozen_histories_and_independent_outcomes():
    report=json.loads(Path('data/models/predictive_checks_v1.json').read_text())
    identifier=report.pop('artifact_id');assert identifier==content_id(report)
    for scenario,entry in report['scenarios'].items():
        for method,result in entry['methods'].items():
            model=load_model(make_config(scenario),estimator=method)
            assert model['artifact_id']==result['artifact_id']
            assert model['training']['observations_sha256']!=entry['observations_sha256']
            assert sum(result['pit_decile_counts'])==entry['n']
            assert 0<=result['central_95_predictive_coverage']['mean']<=1


def test_robust_predictive_convolution_matches_explicit_two_component_mixture():
    model={'model_version':'robust-mixture-rd-v1','robust':{'tau':[.01],'weights':[1.],
        'wide_probability':.05,'wide_scale':5.}}
    y=np.array([0.,.1]);se=np.array([.01,.02])
    score,pit=predictive_scores(y,se,model)
    narrow=np.sqrt(se**2+.01**2);wide=np.sqrt(se**2+.05**2)
    assert score==pytest.approx(np.log(.95*norm.pdf(y,scale=narrow)+.05*norm.pdf(y,scale=wide)))
    assert pit==pytest.approx(.95*norm.cdf(y,scale=narrow)+.05*norm.cdf(y,scale=wide))
    _,extremes=predictive_scores([-10,10],[.01,.01],model)
    assert extremes.tolist()==[0.,1.]
