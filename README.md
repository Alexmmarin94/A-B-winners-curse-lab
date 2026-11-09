# The Winner's Curse Lab

**Your winners look great. How much is real?**

A/B tests help teams decide what to launch. But when the strongest results earn a place on the roadmap, some of what looks like growth can be favorable noise. Reusing those winning estimates as an impact forecast can make a successful experimentation program look better than it really is.

This interactive lab lets you make the launch decisions, compare estimates informed by historical experiments, and reveal the simulated truth. Explore when Bayesian corrections recover a more credible effect—and when they make the estimate worse.

The goal is **better judgment about impact after selection**, not an automatic discount on every winner. All challenge outcomes are simulated: the headline CTR laboratory is informed by Upworthy data, while the four product challenges use hypothetical assumptions. The interface and exports are in English.

## Live demo

**[Explore The Winner's Curse Lab →](https://experimentation-winners-curse-lab-mkvnxjreewatpepwas8pgt.streamlit.app/?page=Learn)**

Start with **Learn**, choose a familiar product context, and select the treatments you would launch at your company. Then compare what the tests reported with the historical correction and the hidden answer. No upload or API key is required.

## Quick start

Use Python 3.12. The repository includes the compact calibration, model and benchmark artifacts needed to run the app; there is no need to download the original archive, fit models or run Monte Carlo jobs at startup.

```bash
git clone https://github.com/Alexmmarin94/A-B-winners-curse-lab.git
cd A-B-winners-curse-lab
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

On Windows, activate with `.venv\Scripts\activate`. Open the local URL printed by Streamlit, or use the [live demo](https://experimentation-winners-curse-lab-mkvnxjreewatpepwas8pgt.streamlit.app/?page=Learn).

## Repository structure

```text
A-B-winners-curse-lab/
├── streamlit_app.py             # App entry point and navigation
├── app/                        # Learning journey, launch cards and model explanations
├── src/
│   ├── data/                   # Archive cleaning and experiment-level checks
│   ├── calibration/            # Measurement-error-aware empirical calibration
│   ├── simulation/             # Reproducible A/B portfolios and stress scenarios
│   ├── statistics/             # Binary outcomes, intervals and tests
│   ├── models/                 # Empirical Bayes, Normal and robust hierarchies
│   └── evaluation/             # Launch summaries and evaluation helpers
├── data/
│   ├── calibration/            # Frozen calibration and held-out validation reports
│   ├── models/                 # Fitted models and predictive diagnostics
│   └── benchmarks/             # Repeated comparisons across generating mechanisms
├── research/                   # Methods, assumptions, evidence and references
├── scripts/                    # Offline calibration, fitting and reproduction
├── tests/                      # Statistical and Streamlit workflow tests
├── .streamlit/config.toml       # Theme and hosting configuration
├── .github/workflows/tests.yml  # Automated Linux validation
├── requirements.txt            # Runtime dependencies
└── DEPLOYMENT.md               # Streamlit Community Cloud setup
```

## Six screens, one connected investigation

| Screen | What you can learn or do |
| --- | --- |
| Learn | See why selecting favorable results changes the impact story, and why simulation gives us an answer key. |
| Choose | Pick a familiar product challenge or explore the separate Upworthy-informed headline CTR lab. |
| Launch | Review nine cards at a time, choose what to ship, then compare observed effects, corrected estimates and simulated truth. |
| Understand | Follow one selected experiment through four estimators, with its own numbers, weights, formulas and accuracy comparison. |
| Benchmark | Check whether a method helps across repeated portfolios, including cases that challenge its assumptions. |
| Methodology | Inspect data cleaning, calibration, held-out checks, model diagnostics and the evidence behind the lab. |

### Follow the workflow in the demo

#### 01 · See the hidden risk in a winning result

Start with a simple question: if you keep the most promising A/B results, do you also keep their favorable noise? The interactive teaching example lets you switch between all results and the ones you would launch. The underlying effects stay the same; the selected average changes.

Learn then explains what a valid experiment can establish, why significance does not certify effect size, and how an inflated launch summary can distort expectations. The teaching example is explicitly illustrative, separate from the generated challenge portfolios.

#### 02 · Choose a context you recognize

Explore retention, acquisition, onboarding or monetization as an experimentation lead. These fictional programs make the decision familiar without claiming that headline clicks establish retention or revenue effects.

A separate headline CTR challenge uses Upworthy-derived calibration. The app distinguishes the empirical inputs, generation rules and hypothetical product assumptions before you interpret results.

#### 03 · Make the launch decisions, then check the answer

Review nine experiment cards with observed uplift, uncertainty intervals and p-values. Some treatments are selected by the starting rule; change those choices to reflect what you would actually launch.

- **Shuffle** replaces the editable batch and discards its choices. It leaves saved selections intact.
- **More experiments** saves the current choices and opens another batch. You can save three rounds, then continue editing or shuffling the final batch.
- **Analyze My Launches** summarizes your chosen treatments.
- **Correct estimates & reveal truth** shows the Empirical Bayes correction, the simulated answer and the accuracy insights together.

The correction is computed from observable results before the answer key is opened. Compare the same selected treatments throughout: an adjustment can improve some estimates and worsen others. The portfolio's mean effect is not a sum of business value or an ROI forecast.

#### 04 · Understand one experiment at a time

The inspector starts with **only the experiments you selected for launch**. An optional toggle includes the other reviewed experiments. The selector controls every chart, formula and explanation below it.

Compare the measured result with three historical models. Each method shows how it arrived at its estimate using this experiment's values: the influence of the test versus history, the historical target, the direction of the adjustment, and the resulting error where truth has been revealed. The robust model also shows how the result changes its probability of belonging to the broader effect group.

**Read the reference lines:** the orange dashed vertical line marks the true simulated effect; the gray dotted line at zero means no treatment–control difference. Only selected treatments included in the revealed comparison receive a truth marker. The app explains its absence for other experiments.

#### 05 · Test whether the correction holds up

One favorable example cannot establish that a method works. Benchmark compares four estimators across nine generating mechanisms using repeated portfolios, paired error comparisons and Monte Carlo uncertainty intervals.

Stress scenarios include unusual effects, shifts in the effect distribution and shared-control A/B/n experiments. The comparison separates estimation accuracy from decision regret: getting an effect size closer and making a better launch decision are different questions. Failure cases remain visible.

#### 06 · Inspect what supports the result

Methodology connects the interface to the research: archive exclusions, calibration assumptions, confirmatory and final holdout checks, prior-fitting uncertainty, and model predictive diagnostics.

The lab keeps mismatches and uncertainty visible. Research from experimentation teams provides context; it does not imply access to their private data or reproduction of their proprietary systems. [Source roles and access limitations](research/references.md) explain what each reference contributes.

## Four ways to estimate the same effect

| Method | How it uses the evidence | What to keep in mind |
| --- | --- | --- |
| Observed result | Uses the treatment–control difference measured in this test. | Selecting a winner does not remove its sampling noise. |
| History-adjusted · Empirical Bayes | Combines the test with a center and spread fitted from historical effects, accounting for measurement uncertainty. | Fitted historical parameters are treated as fixed. This is the main Launch correction. |
| Uncertain history · Normal hierarchy | Integrates uncertainty about the historical center and spread. | A more complex model can yield a similar answer; an unsuitable Normal assumption can still mislead. |
| Outlier-aware · Robust hierarchy | Uses a narrow and a broader effect group, integrating uncertainty in their shared scale. | Its center is fixed at zero. “Robust” describes the design, not guaranteed accuracy. |

The latter two models are compared in **Understand** and **Benchmark**. None of the estimates is ground truth, and a narrower interval does not automatically mean a better estimate.

## Why simulate—and what comes from real data?

A real experiment gives us a noisy estimate. To check whether a correction gets closer to the underlying effect, this lab also needs an answer key. The simulator sets the true probabilities first, then samples visitors and outcomes. Estimators receive only the observed counts and historical model information.

| Source | Role in the lab |
| --- | --- |
| Upworthy exploratory experiments | Inform headline CTR traffic patterns, rate anchors and an approximate latent-effect distribution; historical observable pairs also train the CTR estimators. |
| Confirmatory and holdout partitions | Check the frozen calibration against separate observable data without refitting it. |
| Hypothetical product assumptions | Define the retention, acquisition, onboarding and monetization challenges and their independent synthetic histories. |
| Stress mechanisms | Test how estimators behave when effects depart from convenient assumptions. |

Binomial counts make the simulated experiments compatible with the same aggregate A/B calculations under that sampling model. They remain generated data, and their relevance to a business depends on the assumptions matching that setting. Real archive results do not reveal their true effects.

**Optimizely is context, not another calibration dataset.** Published aggregate reports and company articles inform the questions; their selected winning effects are not imported as a population of known true effects.

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

## Interaction, exports and persistence

Launch choices survive navigation within a Streamlit session. Changing the selection invalidates its analysis, correction and reveal, so those results must be recomputed for the new choices. Once truth has been revealed, the app notes that further choices from that portfolio are no longer blind.

Download configurations, launch snapshots, fitted models and reports to retain the assumptions and results. Seeds and artifact IDs support replay; they do not certify realism. The hosted demo has no persistent user account or database, and selections can reset after a reconnect or restart.

## Verify

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

**107 tests passed**, together with dependency installation and the server health check on Linux, in the [verified GitHub Actions run](https://github.com/Alexmmarin94/A-B-winners-curse-lab/actions/runs/42647815609).

Tests cover archive cleaning, reproducible simulation, intervals and p-values, shared-control covariance, posterior special cases, numerical integration, model compatibility, artifact integrity and the complete Streamlit journey. They also check that the experiment-specific explanations reproduce the actual estimators and that hidden truth does not enter inference.

The portable package was checked separately: all six screens started without original CSVs or local working files, and every packaged file matched its manifest. Streamlit AppTest does not render pixels; these checks are not a claim of automated desktop/mobile visual validation.

## Reproduce the research

The live app uses frozen artifacts. Rebuilding the research is an optional offline workflow, with the original archive files required for the archive stages. See the method notes linked above before changing calibration, priors or evaluation assumptions.

<details>
<summary>Calibration, model fitting, benchmark and replay commands</summary>


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

</details>

## Deployment and development

The [live app](https://experimentation-winners-curse-lab-mkvnxjreewatpepwas8pgt.streamlit.app/?page=Learn) runs on Streamlit Community Cloud. [DEPLOYMENT.md](DEPLOYMENT.md) records the repository, entrypoint, Python version and deployment checks for another instance.

Runtime dependencies are pinned in `requirements.txt`; `requirements-dev.txt` adds the test dependency. The macOS development snapshot in `requirements.lock.txt` is retained for provenance. No credentials or external APIs are required by the app.

Production configuration disables source watching. For local development, enable it explicitly:

```bash
python -m streamlit run streamlit_app.py --server.address 127.0.0.1 --server.runOnSave true --server.fileWatcherType poll
```

Create a portable source/demo ZIP with `python -m scripts.package_demo`. It includes code, compact artifacts, tests, documentation and a SHA-256 manifest. Original CSVs, virtual environments, local outputs and secrets are excluded.

## License and attribution

Project software is distributed under the [MIT license](LICENSE).

Archive-derived material is attributed to Matias, Munger, Aubin Le Quéré and Ebersole (2021), *The Upworthy Research Archive, a time series of 32,487 experiments in U.S. media*, under **CC BY 4.0**. See [data attribution](research/references.md#data-attribution) and the [calibration notes](research/calibration_v1.md) for sources, exclusions and transformations. The software and archive licenses are separate; neither implies endorsement by the referenced organizations.
