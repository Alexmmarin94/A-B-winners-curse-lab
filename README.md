# The Winner's Curse Lab

An interactive Streamlit laboratory for selection bias in experimentation.

**v0.9.1 — a working local demo, fitted models, and reproducible research artifacts.**
The experience follows **Learn → Choose → Launch → Correct & reveal → Understand**.
Start with a visible explanation of selection bias, an interactive teaching illustration, and
how simulation assumptions are sourced and checked. Then choose among four fictional product
challenges or a separate archive-calibrated headline CTR challenge. Inspect compact experiment cards, select launches, apply an independently fitted
correction and reveal synthetic truth in one action. Understand explains each method with experiment-specific formulas and weights;
Benchmark compares four estimators under nine generating mechanisms.

**[Open the introduction](http://localhost:8501/?page=Learn)** while the development server is running.

The product scenarios are hypothetical. Only the separate CTR generator uses Upworthy calibration.
That calibration is approximate, with documented observable discrepancies. Bayesian methods do
not always improve estimates: failure cases and interval undercoverage are displayed, not hidden.
No proprietary company data, invented model outputs, or hardcoded correction discounts are used.

## Run the demo

Use Python 3.12, the version validated locally. From the project directory:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m streamlit run streamlit_app.py --server.address 127.0.0.1 --server.port 8501
```

Open <http://localhost:8501>. Keep this terminal running; Ctrl+C stops it. Production configuration
disables source watching. For development, add `--server.runOnSave true --server.fileWatcherType poll`. Restart an existing environment with:

```bash
cd A-B-winners-curse-lab
source .venv/bin/activate
python -m streamlit run streamlit_app.py --server.address 127.0.0.1 --server.port 8501
```

**No raw CSVs, network downloads, model fitting, or Monte Carlo jobs are needed at startup.**
The demo reads compact artifacts under `data/`. `requirements.txt` pins direct runtime packages;
`requirements.lock.txt` records the complete development environment from macOS arm64.
`pyproject.toml` uses the same runtime pins. CI installs `requirements-dev.txt`, which includes the production requirements and pytest. Linux installation has not
been verified by a hosted CI run. PyMC is unnecessary for these low-dimensional models:
analytic integration and checked numerical quadrature integrate hyperparameter uncertainty.

## What changed in v0.7.0

- Learn now leads with business implications and a visible simulated-data disclosure, followed
  by six visual safeguards explaining the errors the simulation workflow aims to prevent.
- Research cards connect Amazon, Netflix, Airbnb and Spotify to specific decisions in this lab.
  Optimizely and LiftArchive remain contextual references, never calibration datasets.
- Choose asks visitors to pick a familiar work context; Launch makes the company-role exercise,
  automatic starting choices and Shuffle behavior explicit.
- The launch-list editor shows selected counts for the current batch and all other reviewed
  batches. Users can edit the complete list or explicitly keep only the current batch's choices.
  The shrinkage chart includes only the analyzed selection and labels every row with its batch.
- Correction and reveal each have a real-data summary plot for the same supported selected
  treatments. The reveal action follows the correction explanation; truth is never plotted early.
- Understand and Benchmark share plain-language model cards, consistent labels and colors.
  Normal and robust hierarchies remain distinct; robust estimates are blue and truth is gold.
  No statistical model, calibration coefficient, benchmark outcome or simulated portfolio was
  changed for this presentation update.

## What works

| Area | Implemented behavior |
|---|---|
| Learn | Visible explanation, explicitly labeled interactive example, simulation process, evidence and limitations |
| Challenge | Four hypothetical product programs and separate empirical CTR pairs; 36 experiments over four months |
| Cards | Nine per batch, intervals, p-values, manual choices, stable Shuffle, reproducible seed |
| Launch analysis | Explicit snapshot; corrections and truth remain hidden until one explicit comparison action |
| Correction | Normal-normal Empirical Bayes fitted on independent observable histories |
| Reveal | Selected-treatment truth reconstructed from the seed and checked against observed counts |
| Understand | Naive, Empirical Bayes, Normal hierarchy, and robust mixture intervals; truth only after reveal |
| Benchmark | Nine stress mechanisms, four estimators, repeated portfolios, Monte Carlo intervals, shared-control A/B/n |
| Methodology | Cleaning, calibration, bootstrap sensitivity, confirmatory and final holdout checks, model predictive checks |
| Reproducibility | Downloadable configurations, snapshots and reports; source hashes, model IDs, scripts and tests |

The main cards remain A/B. Full A/B/n generation, covariance-aware posterior inference,
Holm selection, and alternative positive-mean decision policies are available in the benchmark.
The main correction action uses Empirical Bayes; the other models appear in Understand.

## Review and validation

```bash
source .venv/bin/activate
python -m pytest -q
curl --fail http://127.0.0.1:8501/_stcore/health
```

Tests cover archive schema and date boundaries; experiment-level exclusions; reproducible
binomial generation; interval and p-value calculations; null calibration; shared-control
covariance and multiplicity; analytic posterior special cases; numerical quadrature;
observable-only inference; model/history compatibility; artifact integrity; and the complete
Streamlit correction/reveal workflow. Predictive checks test new noisy observations, while
benchmarks test latent-effect estimation and decision regret. Those are different targets.

The app is verified locally with Streamlit AppTest and an HTTP health check. AppTest does not
render pixels; browser-level visual QA of the final screens still requires user review.
The `.github/workflows/tests.yml` workflow runs tests and a server smoke check when hosted.
The final local run passed **107 tests**. An extracted demo package was separately checked:
all six screens started without `raw_data/` or local working files, and every packaged file
matched its SHA-256 manifest.

Checkpoints 1–4 were reviewed interactively. Checkpoint 5 adds Understand and Benchmark;
checkpoint 6 adds diagnostics, methodological documentation, versioned artifacts and deployment
configuration. Review the running app before public release; no public deployment has occurred.

## Research reproduction

These commands use the original CSVs under `raw_data/` for archive stages. Raw files and local
quality ledgers remain excluded from publication. Run from the project root with the venv active.

```bash
# Inventory, experiment-level cleaning, and exploratory-only calibration.
python scripts/inspect_archive.py
python -m scripts.calibrate_upworthy --bootstrap 100

# Checks of the frozen calibration; neither command refits it.
python -m scripts.validate_calibration --partition confirmatory --seed 8675309
python -m scripts.validate_calibration --partition holdout --seed 8675310

# Independent observable histories, three fitted model families.
python -m scripts.fit_models --bootstrap 100
python -m scripts.fit_hierarchical
python -m scripts.fit_hierarchical --robust

# Initial matched checks and observable predictive diagnostics.
python -m scripts.validate_models --replications 20 --size 100
python -m scripts.validate_models --estimator hierarchical --replications 20 --size 100 --output data/models/hierarchical_validation_v1.json
python -m scripts.check_model_predictions

# Final stress-v2 report: 30 portfolios × 60 experiments × 9 scenarios, four estimators.
python -m scripts.run_benchmarks --replications 30 --size 60

# Export or replay a portfolio without exposing individual true effects.
python -m scripts.generate_portfolio --scenario retention --seed 20261108 --output .local/portfolio.json
python -m scripts.generate_portfolio --scenario upworthy_ctr --seed 20261108 --output .local/ctr-portfolio.json
python -m scripts.generate_portfolio --config path/to/config.json --output .local/replayed.json
python -m pytest -q
```

`--config` takes precedence over scenario/seed. Reproduction requires the source version,
dependency environment, exact artifact IDs and source hashes. Offline jobs overwrite their
specified outputs; preserve frozen files when comparing versions. The benchmark's stable UI
path is `data/benchmarks/stress_v1.json`; its **internal version is stress-v2**. The earlier
three-model report is retained separately as `stress_v1_initial.json` for development provenance.

The final holdout has now been inspected. It must not be described as unused for future model
development. No calibration parameters were changed after its inspection. Rebuilding an artifact
may change its content hash across dependency versions; retain originals to replay old snapshots.

## Scientific scope and limitations

- The four product priors use histories of 3,000 synthetic experiments each; CTR uses 3,823 real
  exploratory pairs. No unsuccessful results are filtered from these histories. The same
  observable records train all three Bayesian model families.
- Models use an approximate heteroscedastic Normal likelihood for rate differences with estimated
  SEs treated as fixed. Sparse correction cases and posterior intervals outside the probability
  difference bounds are withheld. This does not make the likelihood exact.
- The Normal hierarchy integrates an uncertain program mean and scale. The robust hierarchy fixes
  the mean at zero and uses a 95% narrow / 5% broad Normal mixture with a fivefold SD multiplier.
  Its name is a modeling intention, not a guarantee. Hyperprior and structural sensitivity remain
  further research, particularly for small histories and outlying effects.
- Benchmark uncertainty conditions on frozen histories. Thirty independent portfolios per scenario
  give limited precision, especially for rare selections and extreme effects. Use paired error
  differences and their intervals; do not infer rankings from small differences in point estimates.
- A/B/n tests share one control and permit at most one launch. The benchmark does not learn extra
  treatment-family correlations beyond those documented in the models.
- Cumulative-error and regret metrics assume disjoint populations of 10,000 users per experiment,
  the same binary metric, and no interactions or launch costs. They are not an ROI forecast.
- Upworthy's pooled CTR anchors, independence assumptions, finite effect support, and approximate
  likelihood leave latent tail recovery unresolved. Real archive outcomes reveal no true effects.

Read [calibration](research/calibration_v1.md), [data quality](research/data_foundation.md),
[simulation and inference](research/simulation_v1.md), [Empirical Bayes](research/normal_normal_v1.md),
[hierarchies and benchmark results](research/hierarchical_benchmark.md), and
[source roles and access limitations](research/references.md).

## Interaction and persistence

The root opens Learn for a new session. The introduction link `?page=Learn` also opens Learn
from an existing session without clearing its portfolio or choices. Navigation updates the
`page` query parameter, so each screen can be linked directly. The v0.6.1 learning update
returns existing sessions to Learn once unless an explicit page link is supplied. Its five-test
illustration is hand-chosen educational data, clearly labeled and separate from the generator;
it never creates, changes or reveals a challenge portfolio.

Shuffle replaces the editable batch and its choices from a fixed seeded pool; it does not resample outcomes.
More experiments locks the current choices and opens another batch, up to three saved rounds.
Saved choices survive shuffles, and all choices survive navigation within the Streamlit session. Changes to choices
or the reviewed batch invalidate the launch snapshot, correction and reveal stages. Analyze
synchronizes visible checkbox values before taking the snapshot. Buttons explain unmet prerequisites.
Source reloads preserve completed stages; a new browser session may start fresh.

One explicit action estimates corrections using observations only, then replays and verifies the selected truth. After any truth reveal, a reminder explains
that subsequent choices are no longer blind. Understand defaults to selected treatments; an opt-in toggle includes other reviewed experiments.
Only selected revealed experiments receive truth markers. The orange dashed line labels the known
simulated effect; the gray zero line represents no treatment–control difference. Exported snapshots include estimates and truth only after the comparison
action; configuration exports disclose assumptions and seeds but no per-experiment truth.

## Deployment preparation

The repository layout, `requirements.txt`, Streamlit theme/configuration, and entrypoint
`streamlit_app.py` are ready for a Python 3.12 Streamlit host. Include `app/`, `src/`, `data/`,
`research/`, dependencies, and tests. Exclude `raw_data/`, `.venv/`, `.local/`, caches and secrets
as specified by `.gitignore`. No credentials or external service are needed by the demo.

Create a portable source/demo ZIP from the explicit publication allowlist:

```bash
python -m scripts.package_demo
```

The output is `.local/winners-curse-lab-v0.9.1.zip`, including a SHA-256 file manifest.
It contains code, compact artifacts, tests and documentation; raw data and the virtual
environment are excluded. Install dependencies after extracting it.

The source repository is [Alexmmarin94/A-B-winners-curse-lab](https://github.com/Alexmmarin94/A-B-winners-curse-lab).
The local-only server command above should remain local; Community Cloud supplies its bind settings.
See [DEPLOYMENT.md](DEPLOYMENT.md) for the exact repository, entrypoint, Python version and verification steps.
Archive-derived material is attributed to Matias, Munger, Aubin Le Quéré, and Ebersole (2021),
under CC BY 4.0; see the calibration notes. Project software is MIT-licensed; see [LICENSE](LICENSE).
