"""Numerical and Monte Carlo checks for binary inference."""

from math import sqrt
import numpy as np
import pytest
from scipy.stats import chi2_contingency
from src.statistics.binary import estimate_binary


def test_known_effect_se_and_independent_score_test():
    result = estimate_binary(100, 1000, 140, 1000)
    assert result.effect == pytest.approx(0.04)
    assert result.standard_error == pytest.approx(sqrt((0.1 * 0.9 + 0.14 * 0.86) / 1000))
    expected = chi2_contingency([[100, 900], [140, 860]], correction=False).pvalue
    assert result.p_value == pytest.approx(expected)
    assert 0.01 < result.ci_low < 0.02
    assert 0.06 < result.ci_high < 0.07
    reverse = estimate_binary(140, 1000, 100, 1000)
    assert reverse.ci_low == pytest.approx(-result.ci_high)
    assert reverse.ci_high == pytest.approx(-result.ci_low)
    assert reverse.p_value == pytest.approx(result.p_value)


@pytest.mark.parametrize("counts", [(0, 20, 0, 20), (20, 20, 20, 20), (0, 20, 20, 20)])
def test_boundary_intervals(counts):
    result = estimate_binary(*counts)
    assert -1 <= result.ci_low < result.ci_high <= 1
    assert result.ci_low <= result.effect <= result.ci_high
    assert 0 <= result.p_value <= 1
    if counts[0] == counts[2]:
        assert result.p_value == 1
        assert result.p_method.startswith("Fisher")


@pytest.mark.parametrize("counts", [(1, 0, 1, 1), (-1, 10, 2, 10), (11, 10, 2, 10), (1.2, 10, 2, 10)])
def test_invalid_counts_rejected(counts):
    with pytest.raises(ValueError):
        estimate_binary(*counts)


@pytest.mark.parametrize("probability", [0.05, 0.24])
def test_null_rejection_and_interval_coverage(probability):
    rng = np.random.default_rng(917)
    replications = 3000
    control_n = rng.integers(2500, 20001, size=replications)
    treatment_n = rng.integers(2500, 20001, size=replications)
    xc = rng.binomial(control_n, probability)
    xt = rng.binomial(treatment_n, probability)
    estimates = [estimate_binary(int(c), int(nc), int(t), int(nt))
                 for c, nc, t, nt in zip(xc, control_n, xt, treatment_n)]
    rejection = np.mean([e.significant for e in estimates])
    coverage = np.mean([e.ci_low <= 0 <= e.ci_high for e in estimates])
    # Four Monte Carlo SEs: a regression check, not proof of exact or selective coverage.
    tolerance = 4 * sqrt(0.05 * 0.95 / replications)
    assert abs(rejection - 0.05) < tolerance
    assert abs(coverage - 0.95) < tolerance
