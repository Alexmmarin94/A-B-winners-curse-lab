# Hierarchical models and stress benchmark

This note documents the v0.6.0 implementations, not an exact reproduction of a company model.
All effects below use probability-difference units; multiply by 100 for percentage points.

## Frozen historical information

All three model families receive identical (observed effect, estimated SE) records. Product
histories contain 3,000 independently generated experiments per program, seed 73000001.
The CTR history contains the 3,823 cleaned exploratory archive pairs. Scripts verify the
observations' canonical content hash against the original Empirical Bayes artifact. No latent
true effect enters fitting. Programs are fitted separately, not pooled across different metrics.

The observation likelihood is y_i | theta_i ~ Normal(theta_i, s_i²). Here y_i is the raw rate
difference and s_i uses half-count-stabilized binomial variance. Treating an estimated SE as
known and assuming a Normal error distribution are approximations, especially for sparse counts.
Sparse rows remain in history to avoid outcome-based filtering; sparse new corrections are withheld.

## Normal hierarchy

The implemented model is

```
mu ~ Normal(0, 0.1²)
tau ~ HalfNormal(0.1)
theta_i | mu, tau ~ Normal(mu, tau²)
y_i | theta_i ~ Normal(theta_i, s_i²)
```

Given tau and history, mu has an analytic Normal posterior. Integrate tau on a log scale over
[1e-7, 1] with trapezoidal quadrature and its Jacobian. Refine 4,097 to 8,193 points: the absolute
log-evidence change must be below 1e-5, and boundary mass below 1e-6. Prune nodes with mass at
most 1e-12 and report their total discarded mass. Artifacts retain the quadrature distribution,
hyperparameter intervals, hyperpriors and convergence checks. These priors are fixed modeling
choices; their applicability across baseline rates is not established by numerical convergence.

For a new A/B observation, integrate the history-based predictive theta distribution against
its likelihood. For A/B/n, jointly update all contrasts in that experiment. Conditional on a
scale node, the prior covariance is tau² I + Var(mu | tau, history) 11'. The observation
covariance contains the shared-control terms. We do not pool the new evaluation portfolio to
refit a historical prior. Means and equal-tail 95% credible intervals come from the resulting
Normal mixture; CDF inversion computes quantiles. No MCMC is used, so R-hat/ESS are inapplicable.

## Robust mixture hierarchy

The implemented alternative deliberately fixes its center at zero:

```
tau ~ HalfNormal(0.1)
theta_i | tau ~ 0.95 Normal(0, tau²) + 0.05 Normal(0, 25 tau²)
```

The 5% probability and fivefold SD are fixed before the final four-model benchmark. Only the
shared scale is learned from history. The likelihood analytically marginalizes the local
component indicator; the same checked quadrature integrates tau. Each new A/B/n treatment
has its own local indicator. All 2^K patterns are integrated jointly with the full observation
covariance (K=4 in this benchmark). This exact enumeration is intentionally bounded to a small
number of variants, not a scalable arbitrary-arm sampler.

A broad component can preserve exceptional effects, but a zero center can misrepresent programs
with positive or negative average effects. Neither mixture flexibility nor quadrature convergence
establishes robustness. No data-derived tuning of the broad weight or multiplier is claimed.
A learned center, additional within-experiment effect correlations, hyperprior sensitivity,
and alternative tail families remain substantive extensions.

## Observable predictive diagnostics

`python -m scripts.check_model_predictions` evaluates all fitted families on 3,000 new observable
experiments per hypothetical program (seed 93000000) and all 17,833 cleaned confirmatory CTR
pairs. The model for each new observation is the history posterior predictive distribution,
convolved with its measurement variance. The observation is scored before using it to update
its own latent effect. Artifacts record mean log density, predictive coverage, PIT decile counts,
source/observation hashes and model IDs.

These are approximate observation-model posterior predictive checks conditional on estimated
SEs, not exact binomial count replication. They use all observations, including sparse pairs.
In CTR, central 95% predictive coverage is approximately 91.6% for both Normal models and 91.1%
for the robust mixture. This exposes observable misfit even though the mixture improves some
synthetic latent-effect metrics. Predictive fit and selected-effect coverage must not be conflated.
Diagnostic intervals treat experiments as independent and histories as fixed. No parameters were
changed in response to these checks.

## Benchmark design and development chronology

An initial three-model diagnostic used seed root 91000000 and is preserved as
`data/benchmarks/stress_v1_initial.json`. The robust mixture was added after inspecting this
initial diagnostic. Its center, mixture weight, multiplier and scale prior were then fixed;
the final four-model run uses fresh root 92000000. This is documented development, not a claim
that the entire model search was preregistered or that evaluation choices were never informed
by earlier diagnostics. The final run does not tune models on its latent truths.

The final report has internal version `stress-v2`, stored at the stable UI path
`data/benchmarks/stress_v1.json`. Each of nine cases uses 30 independently seeded portfolios
of 60 experiments. Case index c and replication r use seed 92000000 + 1000*c + r.
Generating configurations, textual mechanisms, seeds and estimator IDs are included in the
content-hashed report. Generator code never reads estimator parameters.

| Case | Generating assumption |
|---|---|
| Matched | Original non-Normal hypothetical retention mixture and traffic |
| Null | Every true effect exactly zero |
| Heterogeneous | Two equally likely families, log-odds Uniform(-.25,.05) or Uniform(.05,.35) |
| Rare breakthroughs | Original mixture, replaced with probability .06 by positive Pareto(2.5), minimum .35 and cap 2 log-odds |
| Prior mismatch | Original effects shifted +.25 log-odds, unchanged training history |
| Temporal shift | Month shifts -.12, 0, .12, .24 log-odds; traffic multiplier 1 + .2*month |
| Low power | Original effects, control n log-uniform 200–2,000 |
| A/B/n | Four independent latent treatments with one shared sampled control |
| Archive CTR | Frozen paired-CTR generator and archive-trained models |

Only the last case is empirically calibrated. Other cases are hypothetical stress mechanisms,
not Upworthy findings. Themed cases use baseline .24 and treatment traffic .8–1.2 times control.

## Selection, fairness and estimands

The primary rule chooses at most one positive observed effect with Holm-adjusted two-sided
p < .05, taking the largest eligible observed effect. Holm adjustment is within an experiment,
not across the whole portfolio. A/B is the one-comparison special case. All estimators receive
the same counts, contrasts and covariance. A group with any cell <5, or any posterior interval
outside [-1,1], is excluded from every method and counted. Results therefore apply to the common
supported population, not all generated experiments.

For contrast j, the shared-control covariance is Vc + Vtj on its diagonal and Vc off-diagonal,
using half-count-stabilized plug-in binomial variances. All three Bayesian methods condition on
the full matrix. The naive estimate retains its Newcombe–Wilson marginal interval, which is not
a simultaneous interval or a selective confidence interval.

Selected-treatment metrics are bias, mean absolute error, RMSE, interval coverage, and MAE for
exceptional |true effect| >=5 pp (product) or >=1 pp (CTR). Metrics are first calculated within
each portfolio and then averaged equally across contributing portfolios; they are not pooled
per-treatment metrics. Empty conditional subsets are undefined, omitted, and counted by the
number of contributing portfolios. The empty additive total remains zero.

Cumulative absolute error is |sum(selected estimate − true effect)| ×10,000, assuming separate
10,000-user populations per experiment, one binary metric, and no interactions. Decision regret
is a **different comparison**: each estimator chooses its highest positive estimated mean or
no launch; the oracle chooses max(0, true effects). Average lost conversions are reported per
supported experiment. There is no significance threshold in this policy, nor cost to launching
a null treatment; consequently all methods have zero regret in the exact-null case. Neither
metric is compounded business impact or a general deployment-cost model.

Student-t intervals describe uncertainty in mean portfolio metrics. The paired MAE difference
uses the same portfolios for the estimator and naive baseline. Histories are frozen; intervals
do not include uncertainty from collecting and fitting new historical programs. Coverage intervals
can extend beyond [0,1] as an approximation; they are not individual credible intervals.

## Measured final results

Mean selected-treatment MAE in pp, from the frozen final four-model report:

| Case | Naive | Empirical Bayes | Normal hierarchy | Robust mixture |
|---|---:|---:|---:|---:|
| Matched | .627 | .591 | .591 | .598 |
| Null | 1.663 | 1.514 | 1.514 | 1.460 |
| Heterogeneous | .592 | .639 | .638 | .655 |
| Rare breakthroughs | .664 | .822 | .816 | .658 |
| Prior mismatch | .612 | .792 | .791 | .732 |
| Temporal shift | .481 | .490 | .489 | .478 |
| Low power | 3.111 | 1.467 | 1.467 | 1.510 |
| A/B/n | .606 | .553 | .553 | .575 |
| Archive CTR | .335 | .431 | .430 | .268 |

Do not rank methods from rounded point estimates alone. For example, in rare breakthroughs,
robust-minus-naive MAE has a 95% Monte Carlo interval approximately [-.039, .026] pp, compatible
with no improvement. Empirical Bayes worsens that case: [.094, .221] pp. In prior mismatch,
all three methods worsen MAE; the robust interval is [.100, .141] pp. In low power, all three
improve MAE. These are conditional results for these mechanisms, not universal endorsements.

Nominal 95% selected coverage is particularly poor under the null selection filter and under
misspecification. In archive CTR it is approximately 75.7% for both Normal models and 93.7% for
the robust mixture. Numerical integration cannot correct model misspecification. With large
histories, integrating hyperparameter uncertainty produces very similar estimates to Empirical
Bayes; model complexity alone should not be credited with a benefit.

The saved report contains uncertainty, unsupported counts, exceptional-effect counts and all
metrics. Extend replication counts before drawing precise tail or ranking conclusions. The final
holdout validates observable calibration only; it supplies no latent truth for these comparisons.
