"""Normal-normal empirical Bayes with heteroscedastic marginal maximum likelihood.

Everything is in probability-difference units. Prediction is conditional on fitted
hyperparameters, not a full hierarchical posterior. Estimated measurement variances
and Normal observation errors are approximations for binomial rate differences.
"""
from dataclasses import dataclass
from math import sqrt
import numpy as np
from scipy.optimize import minimize_scalar
from scipy.stats import norm


@dataclass(frozen=True)
class PriorFit:
    mean: float
    variance: float
    n_history: int
    log_likelihood: float
    boundary: bool


@dataclass(frozen=True)
class PosteriorEstimate:
    mean: float
    sd: float
    ci_low: float
    ci_high: float
    prior_weight: float
    model_se: float


def stabilized_rate_difference(xc: int, nc: int, xt: int, nt: int) -> tuple[float, float]:
    if nc <= 0 or nt <= 0 or not (0 <= xc <= nc and 0 <= xt <= nt):
        raise ValueError('Invalid binary counts.')
    pc, pt = (xc+.5)/(nc+1), (xt+.5)/(nt+1)
    # Half-count plug-in SE stabilizes zero/all-success cells; it does not make a
    # sparse Normal likelihood exact. The effect estimate itself is uncorrected.
    return xt/nt-xc/nc, sqrt(pc*(1-pc)/nc + pt*(1-pt)/nt)


def fit_normal_normal(effects, standard_errors) -> PriorFit:
    y, s = np.asarray(effects,dtype=float), np.asarray(standard_errors,dtype=float)
    if y.ndim != 1 or y.shape != s.shape or len(y) < 3:
        raise ValueError('Need at least three aligned historical effect/SE observations.')
    if not np.isfinite(y).all() or not np.isfinite(s).all() or np.any(s <= 0):
        raise ValueError('Effects must be finite and SEs strictly positive.')
    # Work in pp for numerical stability; convert all returned parameters back.
    yp, v = y*100, (s*100)**2
    def profile(tau2):
        total = v + tau2
        weights = 1/total
        mu = float(np.sum(weights*yp)/weights.sum())
        nll = .5*float(np.sum(np.log(2*np.pi*total)+(yp-mu)**2/total))
        return nll, mu
    # Any tau2 above the squared data range has a positive profile derivative.
    upper = max(float(np.ptp(yp)**2), float(np.max(v)), 1e-8)
    grid = np.r_[0, np.geomspace(max(upper*1e-12,1e-16), upper, 100)]
    values = np.array([profile(t)[0] for t in grid])
    candidates = [(float(values[0]), 0.0), (float(values[-1]), upper)]
    # Profile likelihood can have multiple stationary points with unequal SEs.
    for i in range(1,len(grid)-1):
        if values[i] <= values[i-1] and values[i] <= values[i+1]:
            result = minimize_scalar(lambda t:profile(t)[0], bounds=(grid[i-1],grid[i+1]),
                                     method='bounded', options={'xatol':1e-12})
            if not result.success:
                raise RuntimeError('Prior variance optimization failed.')
            candidates.append((float(result.fun),float(result.x)))
    nll,tau2 = min(candidates)
    mu = profile(tau2)[1]
    # Density change-of-units restores the log likelihood in probability units.
    return PriorFit(mu/100,tau2/10000,len(y),-nll+len(y)*np.log(100),tau2==0)


def posterior(effect: float, standard_error: float, prior: PriorFit) -> PosteriorEstimate:
    values = [effect,standard_error,prior.mean,prior.variance]
    if not np.isfinite(values).all() or standard_error <= 0 or prior.variance < 0:
        raise ValueError('Invalid posterior inputs.')
    data_weight = prior.variance/(prior.variance+standard_error**2)
    mean = data_weight*effect+(1-data_weight)*prior.mean
    sd = sqrt(data_weight*standard_error**2)
    z = float(norm.ppf(.975))
    return PosteriorEstimate(float(mean),sd,float(mean-z*sd),float(mean+z*sd),float(1-data_weight),standard_error)


def fit_uncertainty(y, se, replications=100, seed=1907):
    rng=np.random.default_rng(seed)
    y,se=np.asarray(y),np.asarray(se)
    estimates=[]
    for _ in range(replications):
        indices=rng.integers(0,len(y),len(y))
        fit=fit_normal_normal(y[indices],se[indices])
        estimates.append([fit.mean,sqrt(fit.variance)])
    return {'replications':replications,'seed':seed,'method':'experiment-level percentile bootstrap',
            'mean_interval_95':np.quantile(estimates,[.025,.975],axis=0)[:,0].tolist(),
            'sd_interval_95':np.quantile(estimates,[.025,.975],axis=0)[:,1].tolist(),
            'limitation':'These intervals describe fitting uncertainty; predictive credible intervals do not integrate it.'}
