# Approximate paired-CTR calibration v1

This is an implemented, reproducible calibration, not a claim that Upworthy's latent effect
distribution has been identified. The app exposes both the artifact and its diagnostics.
It is separate from the four hypothetical product challenges and from the evaluated correction models.

## Source and estimand

Source: the local exploratory package, SHA-256
`8368313b060f4015a0c6fb34e6d788163cee29554144aba9390b14922eb9d8ce`.
After experiment-level exclusions, 3,823 tests remain. A stable salted hash chooses two
packages and their orientation without inspecting outcomes. The estimand is the log odds ratio
between arbitrary variants within a test, not the effect of the editorial winner against an
untreated control. Random orientation motivates symmetry; it does not establish unimodality.

Only one pair contributes per test. This discards information but avoids fitting a factorized
likelihood to correlated shared-control contrasts. The artifact describes source variant counts
and illustrative plug-in shared-control correlations; the empirical synthetic generator uses two arms. A separate hypothetical A/B/n stress generator now models shared controls.

## Measurement-error likelihood

For each pair, add 0.5 to all four cells, calculate the log odds ratio y, and set SE to the
square root of the sum of reciprocal corrected cells. Approximate y conditional on latent
effect theta by Normal(theta, SE²). This accounts for heteroscedastic measurement uncertainty
instead of fitting the prior directly to observed effects. It treats estimated SEs as fixed,
assumes effect/SE independence, and can be inaccurate at low counts. All 59 training pairs with
a cell below five remain in training; dropping them would select on observed outcomes.

The latent distribution is a point mass at zero plus symmetric positive/negative uniform
bins with absolute boundaries 0, .05, .10, .20, .40, .80, 1.60, and 3.20. Independent weights
allow non-unimodal shapes. This is neither a single Normal prior nor an exact reproduction of
ashr. Normal-error convolutions of uniforms are evaluated with stable log-CDF differences.
Weights maximize the concave finite-mixture likelihood on the simplex using SLSQP; a directional
derivative optimality gap must be below 1e-5 or fitting raises an error.

Measurement-error-aware mixtures are motivated by
[Stephens (2017)](https://doi.org/10.1093/biostatistics/kxw041), but the present component family
and calibration purpose differ. No posterior correction is implemented by this fitting step.

## Uncertainty and sensitivity

One hundred experiment-level bootstrap refits provide percentile intervals conditional on
the pair rule, grid, likelihood, and cleaning. They omit structural/model uncertainty, dependence
between actual tests, and uncertainty about the original randomization. With 100 refits, tail
quantiles of the bootstrap distribution have limited numerical precision.

The fitted RMS log-odds effect is 0.301 (conditional bootstrap range 0.289–0.314); the observed
log-odds SD is 0.431 and the median measurement SE is 0.236. These different quantities illustrate
the role of measurement noise but do not prove recovery of true heterogeneity. The exact-zero
weight is especially weakly determined (bootstrap interval 0–0.410); do not report it as a known
fraction of ineffective treatments.

An alternate outcome-blind pairing seed gives fitted RMS 0.315. Extending the support to 6.4
gives RMS 0.301. These are exploratory sensitivities, not proof that extreme effects are absent.
The fixed support remains an assumption. The artifact retains full weights, intervals, optimizer
diagnostics, and sensitivity summaries.

## Independent synthetic generation

A deterministic reservoir of 512 exploratory pairs records paired sample sizes, smoothed
pooled CTR, and source variant counts. It omits raw headlines and source identifiers. Resampling
reservoir rows jointly approximately preserves dependence among those design features.
The pooled CTR is a noisy plug-in design anchor, not an estimated latent control distribution.

Draw a latent log-odds change from the fitted histogram mixture independently of design.
Place control and treatment log odds at logit(anchor) minus/plus half that change, then sample
independent binomial counts. This midpoint convention is an explicit synthetic assumption;
it need not exactly preserve pooled CTR after nonlinear transformation. Month labels are
synthetic, not a replay of archive dates. Source time variation is reported separately.

Scientific truth has its own record type. UI state and downloads receive observations only.
The empirical configuration includes the exact calibration content hash; checksum mismatch
or missing artifacts cause an error, never an implicit hypothetical fallback. No fitting,
bootstrap, raw-data loading, or downloads occur at app startup.

## Confirmatory check after freezing

The artifact was serialized and hashed before the validation script accessed confirmatory
outcome distributions. No coefficients, bins, or generating assumptions were changed in response
to that check. The validation contains 17,833 cleaned confirmatory pairs and 6,000 new synthetic
pairs from seed 8675309.

| Observable | KS distance |
|---|---:|
| Total paired impressions | 0.022 |
| Pooled CTR | 0.065 |
| Observed effect in percentage points | 0.019 |
| Observed log odds ratio | 0.032 |

These are descriptive discrepancies, not acceptance thresholds or a performance benchmark.
At the 99th percentile, synthetic pooled CTR is 5.53% versus 4.63% in confirmatory data, and
synthetic observed uplift is 1.91 pp versus 1.57 pp. Conversely, the synthetic log-odds tails
are narrower. Do not claim distributional equivalence or validated tail recovery. The independent
design/effect assumption, noisy anchors, and finite reservoir warrant further investigation.

The report also records a paired predictive log-density contrast against a zero-effect model
under the approximate observation likelihood, with a normal interval for its mean. This is an
observable predictive check, not evidence that a Bayesian correction improves selected effects.
The final holdout was subsequently checked without refitting: 3,812 cleaned real pairs and
6,000 new synthetic pairs (seed 8675310). KS distances are .022 for paired impressions, .104
for pooled CTR, .029 for observed pp effects and .059 for log odds. These discrepancies,
especially the CTR distribution, remain limitations. The check is saved separately in
`data/calibration/holdout_validation.json`; the original calibration artifact is unchanged.
The holdout has now been inspected and cannot be called an untouched future validation set.
Notes inside the original signed artifact that describe a reserved holdout record its fitting-stage status.

## Reproduction and attribution

```bash
python -m scripts.calibrate_upworthy --bootstrap 100
python -m scripts.validate_calibration
python -m scripts.validate_calibration --partition holdout --seed 8675310
python -m scripts.generate_portfolio --scenario upworthy_ctr --seed 20261108 --output .local/ctr-portfolio.json
python -m pytest -q
```

The raw source remains local. Derived artifacts are in `data/calibration/`; individual
exclusion ledgers are in `.local/quality/`. Tests check numerical convolutions against quadrature,
known-noise synthetic recovery, date boundaries, paired selection, artifact integrity, and
raw-data-free UI execution. These tests do not validate real latent effects or winner coverage.

Archive attribution: Matias, Munger, Aubin Le Quéré, and Ebersole (2021), *The Upworthy Research
Archive, a time series of 32,487 experiments in U.S. media*, Scientific Data. Archive license:
CC BY 4.0. Sources: [archive documentation](https://upworthy.natematias.com/about-the-archive.html)
and [June 2024 correction](https://upworthy.natematias.com/2024-06-upworthy-archive-update.html).
