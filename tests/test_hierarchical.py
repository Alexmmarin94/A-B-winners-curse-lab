"""Analytic special cases, numerical integration, and covariance-aware prediction."""
import numpy as np
import pytest
from app.configuration import make_config
from src.models.artifacts import load_model
from src.models.hierarchical import fit_hierarchical,predict_hierarchical,predict_joint
from src.models.normal_normal import posterior,PriorFit


def test_joint_posterior_uses_shared_control_covariance():
    artifact={'model_version':'normal-normal-rd-v1','fit':{'mean':0,'variance':1}}
    prediction=predict_joint([2,0],[[2,1],[1,2]],artifact)
    assert [p.mean for p in prediction]==pytest.approx([.75,-.25])
    assert [p.sd**2 for p in prediction]==pytest.approx([.625,.625])
    with pytest.raises(ValueError):predict_joint([2,0],[[1,2],[2,1]],artifact)


def test_hierarchical_single_node_matches_conjugate_result():
    artifact={'model_version':'hierarchical-normal-rd-v1',
              'hierarchical':{'nodes':{'tau':[.03],'mu_mean':[.01],'mu_variance':[.0001],'weights':[1.]}}}
    predicted=predict_hierarchical(.04,.02,artifact)
    exact=posterior(.04,.02,PriorFit(.01,.001,100,0,False))
    assert predicted.mean==pytest.approx(exact.mean)
    assert predicted.sd==pytest.approx(exact.sd)
    assert predicted.ci_low==pytest.approx(exact.ci_low,abs=1e-9)
    assert predicted.ci_high==pytest.approx(exact.ci_high,abs=1e-9)
    joint=predict_joint([.04],[[.02**2]],artifact)[0]
    assert joint.mean==pytest.approx(predicted.mean)
    assert joint.ci_low==pytest.approx(predicted.ci_low)


def test_hierarchical_fit_converges_and_recovers_known_program():
    rng=np.random.default_rng(628)
    y=rng.normal(.01,np.sqrt(.02**2+.01**2),500)
    fitted=fit_hierarchical(y,np.full(len(y),.01),points=1025)
    assert abs(fitted['fit']['mean']-.01)<.004
    assert abs(np.sqrt(fitted['fit']['variance'])-.02)<.004
    assert fitted['diagnostics']['log_evidence_change']<1e-5
    assert sum(fitted['nodes']['weights'])==pytest.approx(1)


def test_histories_match_between_estimators_and_no_truth_input():
    for key in ['retention','acquisition','onboarding','monetization','upworthy_ctr']:
        config=make_config(key);eb=load_model(config);hier=load_model(config,estimator='hierarchical')
        assert eb['training']['observations_sha256']==hier['training']['observations_sha256']
        assert hier['hierarchical']['diagnostics']['edge_mass']<1e-6
        p=predict_hierarchical(.02,.01,hier)
        assert p.ci_low<p.mean<p.ci_high


def test_robust_mixture_changes_component_weight_for_large_observations():
    from src.models.robust import predict_robust
    artifact={'model_version':'robust-mixture-rd-v1','robust':{'tau':[.01],'weights':[1.],
              'wide_probability':.05,'wide_scale':5.,'center':0.}}
    p=predict_robust(.1,.01,artifact)
    narrow=posterior(.1,.01,PriorFit(0,.01**2,100,0,False))
    assert p.mean>narrow.mean
    assert p.ci_low<p.mean<p.ci_high
    joint=predict_joint([.1],[[.01**2]],artifact)[0]
    assert joint.mean==pytest.approx(p.mean)
    assert joint.ci_high==pytest.approx(p.ci_high)


def test_robust_histories_and_quadrature_checks():
    for key in ['retention','acquisition','onboarding','monetization','upworthy_ctr']:
        config=make_config(key);model=load_model(config,estimator='robust')
        assert model['training']['observations_sha256']==load_model(config)['training']['observations_sha256']
        assert model['robust']['diagnostics']['log_evidence_change']<1e-5
        assert model['robust']['center']==0
