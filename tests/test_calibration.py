"""Measurement-error likelihood, fit recovery, artifact integrity, and empirical sampling."""
from dataclasses import asdict
import json
import numpy as np
import pytest
from scipy.integrate import quad
from scipy.stats import norm
from app.configuration import make_config
from src.calibration.artifacts import load_calibration
from src.calibration.mixture import EDGES, component_log_likelihood, fit_mixture, latent_summary
from src.simulation.engine import generate_portfolio


def test_uniform_convolution_matches_quadrature():
    y,se=.3,.25
    logs=component_log_likelihood([y],[se])[0]
    assert np.exp(logs[0])==pytest.approx(norm.pdf(y,scale=se))
    for index,(a,b) in enumerate(zip(EDGES[:-1],EDGES[1:]),start=1):
        expected=(quad(lambda theta:norm.pdf(y-theta,scale=se),a,b)[0]
                 +quad(lambda theta:norm.pdf(y-theta,scale=se),-b,-a)[0])/(2*(b-a))
        assert np.exp(logs[index])==pytest.approx(expected,rel=1e-8,abs=1e-12)
    assert np.allclose(component_log_likelihood([y],[se]),component_log_likelihood([-y],[se]))


def test_noise_aware_fit_recovers_scale_without_using_truth():
    rng=np.random.default_rng(510)
    truth=rng.uniform(-.4,.4,6000)
    se=rng.uniform(.12,.6,len(truth))
    observed=truth+rng.normal(0,se)
    fit=fit_mixture(observed,se)
    rms=latent_summary(fit.weights)['rms_log_odds_effect']
    assert abs(rms-np.sqrt(np.mean(truth**2)))<.035
    assert rms<np.std(observed)*.75
    assert fit.optimality_gap<1e-5
    assert fit.weights.sum()==pytest.approx(1)


def test_known_measurement_noise_null_fit():
    rng=np.random.default_rng(154)
    se=rng.uniform(.1,.4,6000)
    fit=fit_mixture(rng.normal(0,se),se)
    assert latent_summary(fit.weights)['rms_log_odds_effect']<.065


def test_artifact_integrity_and_truth_separation(tmp_path):
    artifact=load_calibration()
    assert artifact['policy']['training_partition']=='exploratory'
    assert artifact['mixture']['uncertainty']['replications']==100
    altered=json.loads(json.dumps(artifact)); altered['mixture']['weights'][0]+=.01
    path=tmp_path/'altered.json'; path.write_text(json.dumps(altered))
    with pytest.raises(ValueError,match='checksum'):
        load_calibration(path=path)
    with pytest.raises(ValueError,match='checksum'):
        load_calibration(expected_id='wrong')
    config=make_config('upworthy_ctr',seed=718)
    first=generate_portfolio(config)
    assert first==generate_portfolio(config)
    assert config.calibration_id==artifact['artifact_id']
    assert config.version=='upworthy-paired-ctr-v1'
    design={(r[0],r[1],r[3]) for r in artifact['design_rows']}
    for observed,truth in zip(first.observed,first.truth):
        assert (observed.control_n,observed.treatment_n,observed.source_variant_count) in design
        assert 0<truth.control_probability<1 and 0<truth.treatment_probability<1
        assert observed.control_successes<=observed.control_n
        assert observed.treatment_successes<=observed.treatment_n
        assert 'truth' not in asdict(observed)
