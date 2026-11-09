# Hypothetical A/B generator v1

Status: implemented for checkpoint 2. **No empirical calibration is claimed.** This generator
allows the interaction to be reviewed while archive calibration is developed separately.

## Generating mechanism

Each challenge has a constant assumed baseline: retention 0.24, acquisition 0.08, activation
0.36, and paid conversion 0.05. These are fictional product assumptions, not literature-derived
estimates. They do not transfer Upworthy click-through effects into unrelated metrics.

For each of 36 experiments:

1. Draw control sample size by rounding a log-uniform draw on [2,500, 20,000].
2. Draw treatment/control allocation ratio uniformly on [0.8, 1.2], then round treatment size.
3. Assign a hypothetical month uniformly from 1–4. All metric windows are assumed complete.
4. Draw a true log-odds change from this explicitly hypothetical mixture:

| Weight | Distribution |
|---|---|
| 0.25 | Point mass at zero |
| 0.50 | Uniform [−0.10, 0.12] |
| 0.15 | Uniform [0.12, 0.30] |
| 0.10 | Uniform [−0.30, −0.12] |

5. Transform baseline log odds plus this change back to a probability. For the point mass,
   use exactly the baseline probability, avoiding floating-point pseudo-effects under the null.
6. Draw independent binomial success counts for control and treatment. Experiments are also
   independent; no shared users, carryover, interference, or interactions are modeled.

This distribution is independent of any future estimator. It is not designed as a normal-normal
model, but neither is it evidence of realism or a complete stress suite. No portfolio is
accepted/rejected based on desired outcomes. Some seeds may show few or no significant wins.

Separate NumPy SeedSequence streams govern design, latent effects, and outcome sampling for
each experiment. The scenario key is converted to a stable CRC32 integer, not Python's
process-randomized hash. The UI batch permutation uses an additional independent stream.
The generator version and dependency lock are part of the reproducibility contract.

## Observable inference

The estimator uses only aggregate counts, never simulated probabilities:

- Effect: treatment observed rate minus control observed rate.
- SE: square root of the sum of the two unpooled plug-in binomial variances.
- 95% CI: Newcombe's combination of two Wilson score intervals (method 10, without continuity
  correction). It is a marginal interval, not a post-selection or simultaneous interval.
- P-value: two-sided pooled score z test of equal probabilities. If any pooled expected cell
  count is below five, use a two-sided Fisher exact test. Degenerate equal-outcome tables have
  p = 1; intervals remain noncollapsed even when the plug-in SE is zero.
- Significance: p < 0.05, without adjustment across the experimentation program.

The CI and p-value are different inferential constructions; close to the threshold they may
disagree. Default selection depends on the p-value and a positive observed effect, not CI
rounding. The cards use percentage points; source data and exports use probability differences.

Reference checked: [Newcombe (1998), comparison of intervals for independent proportions](https://pubmed.ncbi.nlm.nih.gov/9595617/).
Wilson intervals are calculated with SciPy's `binomtest(...).proportion_ci(method="wilson")`;
see [the SciPy API](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.binomtest.html).

## Information boundary and summary estimand

`generate_portfolio` returns separate observed and truth records for future offline evaluation.
`generate_observed` exposes only the former and discards truth. The UI stores only observed
records and the simulation configuration; download payloads follow the same boundary.
This is an educational disclosure boundary, not cryptographic secrecy: a user with the seed
and source code can reproduce truth offline.

Launch analysis takes the equal-weight mean of observed effects among manually selected,
reviewed experiments within one metric and scenario. It does not sum effects or infer cumulative
ROI. No selected treatments gives an undefined mean (displayed as an em dash), not zero. Negative
selected means are preserved. A descriptive histogram includes all reviewed observations and
distinguishes selected from unselected ones. Reviewing a new batch invalidates the old summary.

## Validation and limits

Tests cover count/probability bounds, seed replay, independence from NumPy's global RNG, stable
portfolio prefixes, symmetry and edge behavior of intervals, and agreement of the pooled score
p-value with the uncorrected two-by-two Pearson test. Null simulations at baseline 0.05 and
0.24 check rejection and marginal coverage over 3,000 replications each. They do not validate
selected-winner coverage, non-null coverage over the full parameter space, or model performance.

AppTests cover manual overrides, Shuffle round trips, navigation, summary invalidation, no-launch
behavior, new seeds, same-seed reset, and progressive truth disclosure. Truth remains absent
until the explicit reveal. A separate approximate empirical CTR generator, fitted correction
models and independent benchmark reports are now implemented.

See `calibration_v1.md` for CTR, `normal_normal_v1.md` for the main correction, and
`hierarchical_benchmark.md` for the Normal and robust mixture hierarchies, shared-control A/B/n,
Holm selection, temporal shifts, rare effects, and repeated selected-winner benchmarks. The
nine-card challenge remains A/B; A/B/n is confined to the benchmark. Browser visual QA of final
screens remains a separate review from AppTest verification.
