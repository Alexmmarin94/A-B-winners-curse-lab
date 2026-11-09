"""Generation and summaries must respect reproducibility and information boundaries."""

from dataclasses import asdict, replace
import json
import numpy as np
import pytest
from app.playground_state import Playground
from app.scenarios import SCENARIOS
from src.evaluation.launches import summarize_launches
from src.simulation.engine import SimulationConfig, generate_observed, generate_portfolio


def config():
    return SimulationConfig("test", "conversion", 0.1, ("A", "B"), seed=41)


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.key)
def test_valid_counts_probabilities_and_separate_truth(scenario):
    result = generate_portfolio(SimulationConfig(scenario.key, scenario.metric,
                                                 scenario.proposed_baseline, scenario.interventions))
    for item, truth in zip(result.observed, result.truth):
        assert item.experiment_id == truth.experiment_id
        assert 0 <= item.control_successes <= item.control_n
        assert 0 <= item.treatment_successes <= item.treatment_n
        assert 0 < truth.control_probability < 1
        assert 0 < truth.treatment_probability < 1
        assert truth.effect == truth.treatment_probability - truth.control_probability
        assert 1 <= item.month <= 4
        assert not hasattr(item, "truth")
        assert not hasattr(item, "treatment_probability")


def test_reproducibility_stream_independence_and_config_version():
    first = generate_portfolio(config())
    np.random.seed(123)
    np.random.random(100)
    assert first == generate_portfolio(config())
    assert first != generate_portfolio(replace(config(), seed=42))
    assert first.observed[:5] == generate_observed(replace(config(), size=5))
    with pytest.raises(ValueError):
        replace(config(), version="unsupported")


def test_truth_changes_cannot_change_observable_summary():
    result = generate_portfolio(config())
    reviewed = {item.experiment_id for item in result.observed}
    selections = dict.fromkeys(reviewed, True)
    original = summarize_launches(result.observed, reviewed, selections)
    modified = replace(result, truth=tuple(replace(item, effect=0.987654321) for item in result.truth))
    assert original == summarize_launches(modified.observed, reviewed, selections)
    assert "0.987654321" not in json.dumps([asdict(item) for item in modified.observed])


def test_empty_and_negative_selection_and_metric_guard():
    observations = generate_observed(config())
    reviewed = {item.experiment_id for item in observations}
    empty = summarize_launches(observations, reviewed, {})
    assert empty.mean_reported_effect is None
    assert empty.selected_ids == ()
    negatives = {item.experiment_id: True for item in observations if item.estimate.effect < 0}
    assert negatives
    assert summarize_launches(observations, reviewed, negatives).mean_reported_effect < 0
    with pytest.raises(ValueError):
        summarize_launches(observations, {"unknown"}, {})
    with pytest.raises(ValueError):
        summarize_launches((replace(observations[0], metric="different"), *observations[1:]), reviewed, {})


def test_review_policy_shuffle_and_snapshot():
    program = Playground.create(config())
    first = program.visible()
    assert len(first) == 9
    for item in first:
        assert program.selections[item.experiment_id] == (item.estimate.effect > 0 and item.estimate.significant)
    key = first[0].experiment_id
    program.select(key, not program.selections[key])
    selected = program.selections[key]
    program.analyze()
    assert len(program.summary.reviewed_ids) == 9
    seen = {item.experiment_id for item in first}
    for _ in range(program.batches-1):
        program.shuffle()
        batch = program.visible()
        assert seen.isdisjoint(item.experiment_id for item in batch)
        seen.update(item.experiment_id for item in batch)
    assert len(seen) == 45
    program.shuffle()
    assert program.visible() == first
    assert program.selections[key] == (first[0].estimate.effect > 0 and first[0].estimate.significant)
    assert program.summary is None
