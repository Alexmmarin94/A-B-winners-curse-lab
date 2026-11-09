# Normal-normal Empirical Bayes correction v1

Implemented for checkpoint 4. This is an approximate, fitted estimator with documented failure
cases, not an arbitrary percentage discount and not a substitute for a hierarchical model.

## Model and fitting

Let y_i be an observed treatment-minus-control rate difference and s_i its estimated SE.
The model assumes y_i | theta_i ~ Normal(theta_i, s_i²) and theta_i ~ Normal(mu, tau²).
Historical marginal observations follow Normal(mu, tau² + s_i²). The mean and variance are
fitted by marginal maximum likelihood; hidden effects are never fit inputs.

For a fixed tau², mu is the inverse-total-variance weighted mean. The implementation profiles
mu, scans a log-spaced variance grid, refines local candidate minima, and includes the zero
variance boundary. Calculations use percentage points internally for numerical stability and
return probability units. A homogeneous-SE unit test checks the closed-form MLE.

For binary observations, y remains the raw rate difference. Measurement SE uses binomial
plug-in variance after replacing each arm rate by (successes + 0.5)/(n + 1). This prevents
zero estimated variance at boundary counts; it does not make the Normal likelihood exact.
It differs slightly from the card's raw plug-in SE and is labeled in the details table.
Historical sparse pairs are retained to avoid outcome-based trimming. For an individual
prediction, any observed cell below five causes the correction to be withheld, with an
explicit explanation. Intervals outside the valid risk-difference range are also withheld;
no clipping or fabricated estimate is substituted.

The posterior data weight is w_i = tau²/(tau² + s_i²), the posterior mean is
w_i y_i + (1 - w_i) mu, and the posterior variance is w_i s_i². The displayed prior weight
is 1 - w_i: a fraction of distance toward the prior mean, not a percent discount on uplift.
Effects below the prior mean can move upward. Equal-tail 95% intervals use the conditional
Normal posterior. If a fitted prior variance is zero, this plug-in model degenerates to a
point mass; it does not magically establish certainty about real effects.

## Histories, provenance, and no-leakage rules

- Retention, acquisition, onboarding, and monetization each use 3,000 independent synthetic
  historical experiments from seed 73000001. Histories include all outcomes. The source is
  hypothetical, not a real product dataset. Scenario-specific streams keep programs separate.
- CTR uses the 3,823 eligible exploratory archive pairs, with the same outcome-blind pairing
  policy as calibration. No confirmatory or holdout observations are used to fit this estimator.
- The empirical generator and CTR estimator share exploratory source information. Synthetic
  evaluation outcomes are independent conditional on the frozen artifacts; this is not a claim
  of wholly independent empirical calibration datasets. Broader misspecification stress tests
  remain necessary.
- Each model records its source/configuration, observable-input digest, scope, parameters,
  bootstrap ranges, and content hash. Compatibility checks require the same metric, scenario,
  baseline metadata, generator version, and calibration artifact. Reusing the synthetic training
  seed in evaluation disables correction rather than silently allowing overlap.
- Prediction accepts observable records only. Tests prohibit simulation generation or fitting
  during correction. No current evaluation outcome is used to refit a prior.

One hundred bootstrap history refits quantify prior-fitting variability. These ranges are
reported separately and **are not integrated into the conditional posterior intervals**.
Estimated SEs, prior shape, effect/precision independence, binomial independence, and model
compatibility remain assumptions. Neither the posterior mean nor its interval establishes truth.

The conceptual motivation is consistent with the prior-sensitivity discussion in
[Kessler's Amazon Science publication (2024)](https://www.amazon.science/publications/overcoming-the-winners-curse-leveraging-bayesian-inference-to-improve-estimates-of-the-impact-of-features-launched-via-a-b-tests).
The publication page was checked; this implementation is not claimed as an exact reproduction
of its analysis or Amazon's internal implementation. No Amazon data is used.

## Initial independent validation and failure cases

Models were frozen before evaluating 20 independent portfolios of 100 experiments per scenario,
using seeds 73000101 through 73000120. Selection is positive observed uplift with an unadjusted
two-sided p < 0.05. Both estimators are compared on the same supported selected treatments;
unsupported counts are reported rather than silently dropped. Metrics are averaged across
portfolios, with Student-t intervals for their means in `data/models/validation_v1.json`.
There is no refitting, hyperparameter tuning, or model selection using evaluation truth.

| Scenario | Naive selected MAE (pp) | EB selected MAE (pp) | Conditional 95% interval coverage among selected |
|---|---:|---:|---:|
| Retention | 0.647 | 0.580 | 91.8% |
| Acquisition | 0.442 | 0.367 | 90.8% |
| Onboarding | 0.717 | 0.663 | 91.8% |
| Monetization | 0.366 | 0.285 | 89.5% |
| Archive CTR | 0.364 | 0.416 | 72.4% |

These are computed diagnostics, not evidence of universal superiority. In the CTR check,
5 of 231 selected treatments were unsupported. The remaining comparison shows worse average
absolute error and substantial undercoverage. The app labels this as a model failure case,
not a recommended adjustment. Prior effect/precision dependence and heterogeneous CTR
baselines are plausible contributors, but this check does not isolate causes.

The product scenarios also under-cover selected effects despite improving average MAE here.
The validation is conditional on one fitted historical model per program and does not capture
full training-history variability. It is not the full rare-breakthrough, temporal-shift, or
prior-misspecification benchmark requested for later work. No parameters were changed to hide
these failures or improve these reported metrics.

## Progressive disclosure

1. Analyze My Launches freezes a descriptive selected-treatment summary.
2. Apply Bayesian Correction loads the fitted model and predicts only from observations.
3. Reveal Ground Truth explicitly reconstructs the seeded simulation, verifies all observed
   records match the reviewed portfolio, and exposes only selected treatment effects.

Before reveal, state, plots, and exports contain no per-treatment true effects. After reveal,
plots compare observed estimates, posterior means, uncertainty intervals, and true effects.
Accuracy changes are shown for both improvements and worsening estimates; comparisons use
the same supported subset. The mean true effect includes all selected treatments. Zero and
negative true means are preserved and never used as denominators for impact ratios.

Changing selection or batch invalidates the analysis, correction, and reveal. Reanalysis resets
the later steps. Once truth has been seen, a reminder notes that later decisions are no longer
blind. This is an educational disclosure boundary, not secrecy from someone with the source
code and seed. Artifacts and predictions are fast to load; no offline fitting is run in the UI.

## Reproduction

```bash
python -m scripts.fit_models --bootstrap 100
python -m scripts.validate_models --replications 20 --size 100
python -m pytest -q
```

The first command needs local raw data for the CTR model. The app needs only the committed
compact artifacts. Separate Normal and robust mixture hierarchies, observable predictive checks,
and stress benchmarks are now implemented; see `hierarchical_benchmark.md`. They do not change
this conditional Empirical Bayes model. Quadrature diagnostics replace MCMC diagnostics because
no model in this release uses MCMC.
