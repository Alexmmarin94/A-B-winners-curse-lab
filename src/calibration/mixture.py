"""Symmetric histogram mixture with heteroscedastic approximate Normal likelihood.

Components are a point mass at zero plus symmetric pairs of uniform intervals.
Weights can be non-unimodal; this is not a single Normal generating distribution.
The observation-error approximation and effect/SE independence remain assumptions.
"""
from dataclasses import dataclass
import numpy as np
from scipy.optimize import minimize
from scipy.special import log_ndtr, logsumexp
from scipy.stats import norm

EDGES = np.array([0, .05, .10, .20, .40, .80, 1.60, 3.20])


def log_normal_interval(lower, upper):
    # Reflect positive-tail bounds to avoid subtracting two CDFs rounded to one.
    a = np.where(lower > 0, -upper, lower)
    b = np.where(lower > 0, -lower, upper)
    log_a, log_b = log_ndtr(a), log_ndtr(b)
    return log_b + np.log(-np.expm1(np.minimum(log_a - log_b, -1e-15)))


def component_log_likelihood(y, se, edges=EDGES):
    y, se = np.asarray(y, dtype=float), np.asarray(se, dtype=float)
    edges = np.asarray(edges, dtype=float)
    if y.ndim != 1 or y.shape != se.shape or not len(y) or not np.all(np.isfinite(y)):
        raise ValueError('Require nonempty, finite, aligned vectors.')
    if not np.all(np.isfinite(se)) or np.any(se <= 0):
        raise ValueError('Standard errors must be finite and positive.')
    if edges[0] != 0 or np.any(np.diff(edges) <= 0):
        raise ValueError('Edges must start at zero and increase strictly.')
    components = [norm.logpdf(y, scale=se)]
    for low, high in zip(edges[:-1], edges[1:]):
        positive = log_normal_interval((y-high)/se, (y-low)/se) - np.log(high-low)
        negative = log_normal_interval((y+low)/se, (y+high)/se) - np.log(high-low)
        components.append(np.logaddexp(positive, negative) - np.log(2))
    return np.column_stack(components)


@dataclass(frozen=True)
class MixtureFit:
    weights: np.ndarray
    log_likelihood: float
    iterations: int
    optimality_gap: float


def fit_mixture(y, se, edges=EDGES, frequencies=None):
    logs = component_log_likelihood(y, se, edges)
    offsets = logs.max(axis=1)
    density = np.exp(logs - offsets[:, None])
    f = np.ones(len(logs)) if frequencies is None else np.asarray(frequencies, dtype=float)
    if f.shape != (len(logs),) or np.any(f < 0) or not np.isfinite(f).all() or f.sum() <= 0:
        raise ValueError('Invalid observation frequencies.')
    normalized = f / f.sum()
    def objective(w):
        return -float(normalized @ np.log(np.maximum(density @ w, 1e-300)))
    def gradient(w):
        return -(density.T @ (normalized / np.maximum(density @ w, 1e-300)))
    k = density.shape[1]
    result = minimize(objective, np.full(k, 1/k), jac=gradient, method='SLSQP',
                      bounds=[(0, 1)]*k, constraints={'type': 'eq', 'fun': lambda w: w.sum()-1,
                                                     'jac': lambda w: np.ones(k)},
                      options={'ftol': 1e-12, 'maxiter': 1500})
    w = np.maximum(result.x, 0); w /= w.sum()
    # For a concave simplex likelihood, this directional derivative bounds remaining
    # improvement per observation (Frank-Wolfe gap).
    scores = -gradient(w)
    gap = float(scores.max() - w @ scores)
    if not result.success or gap > 1e-5:
        raise RuntimeError(f'Mixture optimizer failed: {result.message}; optimality gap {gap}')
    return MixtureFit(w, float(f @ (np.log(density @ w) + offsets)), int(result.nit), gap)


def latent_summary(weights, edges=EDGES):
    edges, weights = np.asarray(edges), np.asarray(weights)
    variances = (edges[:-1]**2 + edges[:-1]*edges[1:] + edges[1:]**2)/3
    tail_fraction = np.maximum(edges[1:] - np.maximum(edges[:-1], .8), 0)/np.diff(edges)
    return {'rms_log_odds_effect': float(np.sqrt(weights[1:] @ variances)),
            'mass_abs_log_odds_above_0_8': float(weights[1:] @ tail_fraction),
            'outer_bin_mass': float(weights[-1])}


def bootstrap_mixture(y, se, replications=100, seed=4815):
    if replications < 20:
        raise ValueError('At least 20 bootstrap replications are required.')
    rng = np.random.default_rng(seed)
    weights, summaries = [], []
    for _ in range(replications):
        frequencies = rng.multinomial(len(y), np.full(len(y), 1/len(y)))
        fit = fit_mixture(y, se, frequencies=frequencies)
        weights.append(fit.weights)
        summaries.append(latent_summary(fit.weights))
    return {'replications': replications, 'seed': seed, 'method': 'experiment-level percentile bootstrap',
            'weight_intervals_95': np.quantile(weights, [.025, .975], axis=0).T.tolist(),
            'summary_intervals_95': {key: np.quantile([s[key] for s in summaries], [.025, .975]).tolist()
                                     for key in summaries[0]},
            'limitations': 'Conditional on pair rule, support grid, likelihood approximation, and cleaning; not full identification uncertainty.'}


def predictive_log_density(y, se, weights, edges=EDGES):
    return logsumexp(component_log_likelihood(y, se, edges) + np.log(np.maximum(weights, 1e-300)), axis=1)
