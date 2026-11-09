"""Independent two-arm binomial inference in probability units.

Intervals use Newcombe's uncorrected Wilson combination (1998, method 10).
P-values use a two-sided pooled score z test; sparse tables use Fisher's exact test.
These are marginal, pre-selection intervals, not simultaneous or selective intervals.
"""

from dataclasses import dataclass
from math import hypot, sqrt
from numbers import Integral

from scipy.stats import binomtest, fisher_exact, norm


@dataclass(frozen=True)
class BinaryEstimate:
    effect: float
    standard_error: float
    ci_low: float
    ci_high: float
    p_value: float
    p_method: str

    @property
    def significant(self) -> bool:
        return self.p_value < 0.05


def estimate_binary(control_successes: int, control_n: int,
                    treatment_successes: int, treatment_n: int) -> BinaryEstimate:
    for successes, n in ((control_successes, control_n), (treatment_successes, treatment_n)):
        if any(not isinstance(value, Integral) or isinstance(value, bool) for value in (successes, n)):
            raise ValueError("Counts and sample sizes must be integers.")
        if n <= 0 or not 0 <= successes <= n:
            raise ValueError("Require n > 0 and 0 <= successes <= n.")
    pc, pt = control_successes / control_n, treatment_successes / treatment_n
    effect = pt - pc
    se = sqrt(pc * (1 - pc) / control_n + pt * (1 - pt) / treatment_n)
    c = binomtest(control_successes, control_n).proportion_ci(method="wilson")
    t = binomtest(treatment_successes, treatment_n).proportion_ci(method="wilson")
    low = effect - hypot(pt - t.low, c.high - pc)
    high = effect + hypot(t.high - pt, pc - c.low)
    pooled = (control_successes + treatment_successes) / (control_n + treatment_n)
    expected = [n * p for n in (control_n, treatment_n) for p in (pooled, 1 - pooled)]
    if min(expected) < 5:
        p_value = float(fisher_exact([[treatment_successes, treatment_n - treatment_successes],
                                     [control_successes, control_n - control_successes]]).pvalue)
        method = "Fisher exact (two-sided)"
    else:
        null_se = sqrt(pooled * (1 - pooled) * (1 / control_n + 1 / treatment_n))
        p_value = float(2 * norm.sf(abs(effect / null_se)))
        method = "Pooled score z (two-sided)"
    return BinaryEstimate(effect, se, max(-1.0, low), min(1.0, high), p_value, method)
