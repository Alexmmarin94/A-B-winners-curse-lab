"""Analytic correctness, measurement-error fitting, scope, and disclosure boundaries."""
from dataclasses import asdict,replace
import json
import numpy as np
import pytest
from app.configuration import make_config
from app.playground_state import Playground
from src.models.artifacts import load_model,correct_observations
from src.models.normal_normal import PriorFit,fit_normal_normal,posterior,stabilized_rate_difference
from src.simulation.engine import generate_portfolio


def test_normal_posterior_matches_analytic_result():
    prior=PriorFit(.01,.0004,1000,0,False)
    result=posterior(.05,.02,prior)
    assert result.mean==pytest.approx(.03)
    assert result.sd==pytest.approx(np.sqrt(.0002))
    assert result.prior_weight==pytest.approx(.5)
    assert posterior(.05,.005,prior).prior_weight<result.prior_weight
    assert posterior(-.02,.02,prior).mean>-.02
    boundary=posterior(.05,.02,replace(prior,variance=0,boundary=True))
    assert boundary.mean==prior.mean and boundary.sd==0


def test_homoscedastic_fit_matches_closed_form_mle():
    y=np.random.default_rng(412).normal(.003,.025,4000)
    se=np.full(len(y),.01)
    result=fit_normal_normal(y,se)
    assert result.mean==pytest.approx(float(y.mean()),abs=1e-10)
    assert result.variance==pytest.approx(float(y.var()-.01**2),rel=1e-6)
    null=fit_normal_normal([.001,.001,.001],[.01,.01,.01])
    assert null.variance==0 and null.boundary


def test_invalid_model_data_and_stabilized_edge_variance():
    for y,se in [([1,2],[1,1]),([1,2,3],[0,1,1]),([1,np.nan,3],[1,1,1])]:
        with pytest.raises(ValueError):
            fit_normal_normal(y,se)
    effect,se=stabilized_rate_difference(0,100,0,100)
    assert effect==0 and se>0
    with pytest.raises(ValueError):
        posterior(0,0,PriorFit(0,1,100,0,False))


def test_artifact_scope_integrity_and_overlap_guard(tmp_path):
    config=make_config('retention')
    artifact=load_model(config)
    assert artifact['training']['n']==3000
    with pytest.raises(ValueError,match='overlaps'):
        load_model(replace(config,seed=artifact['training']['simulation_seed']))
    with pytest.raises(ValueError,match='Baseline'):
        load_model(replace(config,baseline=.20))
    with pytest.raises(ValueError,match='match'):
        load_model(replace(config,metric='Different metric'))
    artifact['fit']['mean']+=1
    (tmp_path/'retention_normal_normal_v1.json').write_text(json.dumps(artifact))
    with pytest.raises(ValueError,match='checksum'):
        load_model(config,directory=tmp_path)


def test_correction_never_generates_or_accesses_truth(monkeypatch):
    program=Playground.create(make_config('retention'))
    first=program.visible()[0]
    program.select(first.experiment_id,True)
    program.analyze()
    assert 'corrections' not in program.snapshot()
    def forbidden(*args,**kwargs):
        raise AssertionError('Prediction must neither generate truth nor refit a model.')
    with monkeypatch.context() as patch:
        patch.setattr('src.simulation.engine.generate_portfolio',forbidden)
        patch.setattr('src.models.normal_normal.fit_normal_normal',forbidden)
        program.correct()
    assert program.revealed_effects is None
    assert 'revealed_effects' not in program.snapshot()
    assert 'corrections' in program.snapshot()
    program.reveal()
    actual={r.experiment_id:r.effect for r in generate_portfolio(program.config).truth}
    assert program.revealed_effects=={key:actual[key] for key in program.summary.selected_ids}
    assert program.snapshot()['revealed_effects']==program.revealed_effects
    program.select(first.experiment_id,False)
    assert program.summary is None and program.corrections is None and program.revealed_effects is None
    assert program.ever_revealed


def test_reveal_requires_stages_and_consistent_replay():
    program=Playground.create(make_config('retention'))
    with pytest.raises(ValueError):
        program.correct()
    with pytest.raises(ValueError):
        program.reveal()
    program.visible();program.analyze();program.correct()
    item=program.observed[0]
    program.observed=(replace(item,control_successes=item.control_successes+1),*program.observed[1:])
    with pytest.raises(ValueError,match='replay differs'):
        program.reveal()
    assert program.revealed_effects is None


def test_sparse_correction_is_withheld():
    program=Playground.create(make_config('retention'))
    item=replace(program.observed[0],control_successes=0)
    corrections,unsupported=correct_observations((item,),(item.experiment_id,),load_model(program.config))
    assert not corrections
    assert item.experiment_id in unsupported


@pytest.mark.parametrize('which',['zero','negative'])
def test_zero_or_negative_true_mean_is_preserved(which):
    program=Playground.create(make_config('retention'))
    truth={r.experiment_id:r.effect for r in generate_portfolio(program.config).truth}
    # Build a selection through the same lock/current mechanism as the UI.
    for round_index in range(4):
        for item in program.visible():
            key=item.experiment_id
            program.select(key, truth[key]==0 if which=='zero' else truth[key]<0)
        if round_index<3:program.add_more()
    program.analyze();program.correct();program.reveal()
    assert program.revealed_effects
    average=np.mean(list(program.revealed_effects.values()))
    assert average==0 if which=='zero' else average<0


def test_hot_reload_restores_progress_without_regeneration(monkeypatch):
    from dataclasses import fields, make_dataclass
    from app.playground_state import restore_playground
    program = Playground.create(make_config('retention'))
    program.visible(); program.analyze(); program.correct(); program.reveal()
    previous_type = make_dataclass('PreviousPlayground', [(f.name, object) for f in fields(Playground)])
    previous = previous_type(**{f.name: getattr(program, f.name) for f in fields(Playground)})
    def forbidden(*args, **kwargs):
        raise AssertionError('Reload must preserve existing observations.')
    monkeypatch.setattr('src.simulation.engine.generate_portfolio', forbidden)
    restored = restore_playground(previous)
    assert isinstance(restored, Playground)
    assert restored.observed == program.observed
    assert restored.snapshot() == program.snapshot()
    assert restored.ever_revealed
