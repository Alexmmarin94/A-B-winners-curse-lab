# Project: The Winner's Curse Lab

I want you to build a scientifically rigorous, interactive Streamlit application called **The Winner's Curse Lab**.

The application should help Product Data Scientists and experimentation practitioners understand the Winner's Curse in A/B testing, explore how treatment selection creates biased estimates, and evaluate whether different Bayesian corrections genuinely improve estimation.

This is intended to become a polished, public GitHub portfolio project demonstrating advanced experimentation methodology, causal reasoning, Bayesian modeling, Monte Carlo simulation, and product-oriented data science.

**Important: Implement the project, not just a plan or a repository scaffold.** Work incrementally, test each component, and prioritize a functioning, statistically defensible application over unnecessary complexity.

## 1. Starting environment

I am developing locally in VS Code using Codex.

The repository is initially almost empty, except for a folder:

`raw_data/`

It contains CSV files from the Upworthy Research Archive, including:

- Exploratory packages.
- Confirmatory packages.
- Holdout packages.
- Undeployed packages.

Discover the actual filenames and inspect the available columns before implementing any processing.

Do not assume the datasets contain fields that have not been verified.

The raw files should remain local and must not be committed to Git.

Create the necessary Python project structure, dependency management, scripts, tests, documentation, and Streamlit application.

Use Python, pandas, NumPy, SciPy, Plotly, Streamlit, and PyMC/ArviZ where appropriate. Prefer established, maintainable libraries.

All code, comments, docstrings, log messages, chart labels, application text, and technical documentation must be written in English.

## 2. Scientific objective

We want to investigate the following question:

**When A/B experiments are selected for launch based on their observed results, how much of the reported improvement is real, how much is sampling noise, and when do statistical corrections improve our estimates?**

The application must distinguish:

1. Valid randomized estimation from post-selection bias.
2. Statistical significance from accuracy of effect-size estimation.
3. The Winner's Curse from the Optimizer's Curse in A/B/n tests.
4. Selection decisions from estimation of the impact of selected treatments.
5. Naive effect estimates from Bayesian posterior estimates.
6. Estimation quality from launch-decision quality.
7. Empirical evidence from assumptions and synthetic scenarios.

Do not assume Bayesian methods are always better.

A valid outcome of the benchmark is that a Bayesian method performs worse than the naive estimator under some conditions.

## 3. Simulation strategy — critical requirement

The central methodology is:

**Empirically Calibrated, Model-Agnostic Monte Carlo Benchmark.**

We want realistic, transparent, reproducible semi-synthetic simulations.

Do not generate every true effect from a normal distribution simply because we intend to evaluate normal-normal Empirical Bayes.

Separate the **data-generating process** from the **models being evaluated**.

### 3.1. Empirical calibration

Use the Upworthy Research Archive to investigate:

- Baseline click-through rates.
- Sample sizes and traffic distributions.
- Number of treatments per experiment.
- Variation in measurement precision.
- Observed effect-size distributions.
- Correlations between estimates sharing the same control.
- Changes in experimental characteristics over time.
- Apparent heterogeneity between experiments.

Upworthy contains aggregate observations, not individual-level behavioral records.

Group variants using the actual experiment identifier and preserve experiment-level structure.

The published archive contains historical randomization concerns. The June 2024 correction identifies potentially unreliable experiments between June 25, 2013 and January 10, 2014.

Check whether the downloaded files contain the updated `problem` or equivalent randomization-risk indicator. Otherwise, implement the documented date-based exclusion, including boundary handling.

Produce a transparent data-quality report documenting excluded experiments and the reasons for exclusion.

Do not treat Upworthy's historical `significance` field as a valid modern p-value. Compute the relevant statistical quantities ourselves.

Do not treat the archive's `winner` field as proof of a statistically significant treatment; it represents an editorial selection decision.

Do not automatically treat undeployed packages as completed experiments with valid observed outcomes.

Preserve the existing exploratory, confirmatory, and holdout partitions. Define explicitly how each is used to prevent leakage.

### 3.2. Estimating empirical effect distributions

A major challenge is separating:

- True heterogeneity across experiments.
- Sampling noise in observed effect estimates.

Do not fit a prior directly to raw observed uplifts without accounting for measurement uncertainty.

Investigate statistically defensible approaches for estimating flexible latent effect distributions, such as heteroscedastic mixture models or nonparametric empirical Bayes methods.

Do not assume the true effect distribution is perfectly identified by Upworthy.

Quantify uncertainty where feasible, especially in the tails.

If a complex nonparametric method is not reliable or practical, implement and document a simpler defensible approach instead of presenting an unsupported result.

Export compact, versioned calibration artifacts containing parameters, estimated distributions, uncertainty information, source references, and methodological assumptions.

### 3.3. Synthetic data generation

Create an independent synthetic experimentation engine.

Each generated experiment should contain at least:

- Experiment ID.
- Scenario and experimentation program.
- Date or period.
- Descriptive intervention name.
- Primary metric.
- Control baseline.
- Number of variants.
- Sample size per variant.
- Simulated outcomes.
- True treatment effects.
- Estimated treatment effects.
- Standard errors.
- Confidence intervals.
- P-values.
- Statistical significance.
- Relevant covariance information.
- Random seed and simulation configuration.

For binary conversion metrics, generate statistically coherent results using appropriate probability models, such as binomial sampling.

Do not simulate millions of user-level rows unnecessarily. Aggregate sufficient statistics are preferable when they preserve the relevant properties.

For A/B/n experiments, account for the dependence between comparisons sharing the same control.

Keep true effects strictly separate from the information accessible to the estimators.

### 3.4. Simulation scenarios

Implement a range of data-generating mechanisms:

**A. Empirically calibrated scenario**

Use observable characteristics derived from Upworthy and flexible estimates of its effect distribution.

**B. Heterogeneous experiment families**

Allow different experimentation programs to have genuinely different effect distributions.

**C. Rare breakthroughs**

Include occasional exceptionally large true effects, including distributions with heavy tails or mixtures.

**D. Prior misspecification**

Create circumstances where historical effect distributions differ from those in the evaluation portfolio.

**E. Temporal distribution shifts**

Allow effect distributions and experimental characteristics to evolve.

**F. Low-powered experimentation**

Include experiments with heterogeneous sample sizes and limited precision.

**G. A/B/n experimentation**

Allow multiple variants and different selection policies.

Do not describe all these scenarios as empirically observed at Upworthy.

Clearly distinguish:

- Empirically estimated parameters.
- Literature-informed assumptions.
- Explicit hypothetical stress scenarios.

### 3.5. Avoiding benchmark favoritism

This is non-negotiable.

The benchmark must not be designed to make Bayesian methods win.

Use independent generating mechanisms, including ones that violate the assumptions of the evaluated estimators.

Use independent training and evaluation portfolios.

Do not tune estimator parameters using held-out true effects.

Use repeated Monte Carlo simulations and uncertainty intervals around benchmark results.

Every estimator must receive the same observable data.

Use reproducible seeds and save scenario configurations.

Include tests that specifically verify no ground-truth leakage occurs.

Also validate observable characteristics of synthetic data against held-out real Upworthy data when possible.

## 4. Main user experience

The application should feel like an interactive product experimentation challenge, not a statistical configuration interface.

Build a narrative learning experience with progressive disclosure.

### Section 0 — Introduction

Before any interaction, explain in accessible English:

- What the Winner's Curse is.
- Why a statistically valid A/B test can still overestimate the impact of selected winners.
- Why the issue becomes important when estimating the impact of product launches.
- Why A/B/n selection can make the problem worse.

Use a simple illustration and one short example.

Avoid overwhelming the visitor with formulas.

### Section 1 — Where does our data come from?

Explain the simulation methodology visually:

Real experimentation archive → Empirical calibration → Independent Monte Carlo generation → Treatment selection → Estimator benchmarking.

Explain the roles of:

- Upworthy.
- Optimizely aggregate research.
- Airbnb research on selection bias.
- Amazon's Empirical Bayes research.
- Netflix's hierarchical Bayesian research.
- Other methodological references where justified.

Do not pretend we have access to internal Netflix or Amazon datasets.

Explain why our synthetic experiments have known true effects and real archived experiments do not.

Explain what we did to avoid designing the simulations in favor of one estimator.

Provide links to sources and a technical methodology section.

### Section 2 — Choose an experimentation challenge

Offer four thematic experiences:

1. **Improve D7 Retention** — Social product.
2. **Grow Acquisition** — Signup or acquisition conversion.
3. **Improve Onboarding** — User activation.
4. **Improve Monetization** — Paid conversion.

Each experience has:

- A short fictional product context.
- One clearly defined primary metric.
- A meaningful baseline.
- Plausible intervention names.
- A portfolio of experiments.
- An experimentation period of four months.

Make clear that experiments were conducted throughout the four-month period, not necessarily simultaneously.

Use Upworthy calibration only where statistically transferable. Themed retention or monetization scenarios must not be falsely presented as directly calibrated from Upworthy CTR effects.

Give them separate, clearly documented literature-informed or hypothetical generating assumptions.

Use a clear, visually attractive scenario selector with a sensible default.

### Section 3 — Select your experiments

The user assumes the role of the experimentation lead.

Show approximately 8–12 compact experiment cards at a time.

Each card should display:

- Experiment name.
- Month or approximate timing.
- Primary metric.
- Observed uplift, clearly labeled as percentage points or relative percent.
- Standard error.
- 95% confidence interval.
- Statistical significance.
- A checkbox indicating whether the user would launch it.

Positive statistically significant experiments should be selected by default under the stated baseline policy.

Include positive, negative, significant, and nonsignificant results.

Allow users to override every selection manually.

Add a **Shuffle** button to show another set of experiments from a stable, reproducible simulated portfolio.

Shuffle should not silently change the underlying calibration, simulation assumptions, or already generated results.

Provide a separate advanced action for generating a completely new portfolio.

The experiment cards should be visually compact. Prefer a small interval visualization or concise effect indicator rather than large charts for every card.

Avoid large tables occupying the entire page.

If an experiment includes several treatment variants, respect the experiment-level decision: the user should be able to inspect candidates, and the default policy should select at most one variant per experiment unless the scenario explicitly supports a different deployment design.

Include a collapsible advanced-settings section instead of showing all statistical controls by default.

### Section 4 — Analyze your launches

After the visitor chooses treatments, provide an explicit button:

**Analyze My Launches**

Only after clicking should the application display:

- Number of experiments reviewed.
- Number of treatments selected.
- Mean reported effect among selected treatments.
- Distribution of observed effects.
- Clear explanation of what the summary estimates.

Do not automatically apply Bayesian corrections.

Do not automatically reveal true effects.

Do not sum arbitrary uplifts from unrelated metrics.

Do not equate the simple sum of treatment effects with actual cumulative business impact unless assumptions such as comparable units, additivity, and deployment populations have been explicitly defined.

### Section 5 — Apply Bayesian Correction

Provide a second button:

**Apply Bayesian Correction**

This should introduce the comparison between:

- Naive observed effects.
- Normal-normal Empirical Bayes.
- Hierarchical Bayesian estimation.
- Robust hierarchical Bayesian estimation, where implemented and validated.

Start with the simplest model, using accessible explanations.

For each selected experiment, show:

- Original estimate.
- Adjusted estimate.
- Appropriate uncertainty interval.
- Estimated shrinkage.
- Which historical information informed the correction.

Explain why less precise estimates may receive more shrinkage.

Explain that shrinkage is not a fixed percentage discount.

Use trained model parameters or precomputed posterior artifacts, not arbitrary hardcoded correction factors.

If the historical model is insufficiently supported or incompatible with a scenario, show an explicit warning rather than a misleading corrected estimate.

Do not imply the posterior mean is the true effect.

### Section 6 — Reveal Ground Truth

Only after the user explicitly clicks:

**Reveal Ground Truth**

show the synthetic true effects.

Compare:

- Observed estimate.
- Bayesian estimate.
- True simulated effect.

Highlight cases where the correction improved accuracy and cases where it made the estimate worse.

Explain why this is possible.

Keep the educational conclusions honest and data-dependent.

### Section 7 — Experiment Deep Dive

Create a dedicated section to inspect individual experiments.

Use visually clear interval plots comparing:

- Raw effect and confidence interval.
- Posterior mean and credible interval.
- True effect, once revealed.

Show the selection threshold, experiment precision, and degree of shrinkage.

Offer intuitive explanations of why the estimator changed or did not change the original effect.

Include examples of exceptional true effects and situations where the prior is unsuitable.

### Section 8 — Model & Methodology Lab

Create a more technical section for experienced visitors.

Allow comparison of:

- Naive estimator.
- Normal-normal Empirical Bayes.
- Hierarchical Normal Bayesian model.
- Robust hierarchical model, such as a heavy-tailed or mixture-based specification.

Include benchmark metrics:

- Bias among selected winners.
- MAE and RMSE.
- Interval coverage.
- Error on exceptional true effects.
- Error in cumulative estimated effects under explicitly stated assumptions.
- Decision regret under a defined utility function.

Benchmark results should be calculated using independent simulated portfolios.

Use multiple Monte Carlo replications.

Provide uncertainty around reported benchmark metrics.

Allow users to choose predefined stress scenarios.

The application should explicitly demonstrate that different estimators can perform better under different assumptions.

Provide reproducibility information: source versions, calibration artifacts, seeds, model configurations, and code references.

### Section 9 — Small Experimentation Programs

End with a practical section titled:

**What If You Only Run a Few Experiments?**

Explain that Winner's Curse can affect even one selected experiment.

Discuss what happens for programs running only 2–10 experiments per quarter or approximately 30 experiments per year.

Explain why these organizations may not have enough relevant historical experiments to learn reliable empirical priors.

Recommend:

- Preserving all historical results, including unsuccessful experiments.
- Reporting uncertainty instead of treating observed uplifts as guaranteed future impact.
- Separating launch decisions from ROI estimation.
- Considering independent validation or replication when decisions are important.
- Avoiding arbitrary shrinkage factors.
- Using external priors only when their relevance and sensitivity can be justified.

Do not present complicated hierarchical models as universally appropriate for small portfolios.

## 5. Statistical models

Implement models separately from the Streamlit interface.

### Model A — Naive estimator

Use the observed experiment effect.

This serves as the baseline.

### Model B — Normal-normal Empirical Bayes

Implement a documented estimator inspired by Ryan Kessler's work.

Estimate prior parameters using historical observed effects and their measurement uncertainty.

Never use the hidden true effects for fitting.

Include uncertainty and calibration checks.

### Model C — Hierarchical Bayesian

Implement a model inspired by Netflix's experimentation-program framework.

Where appropriate, model:

- Related treatments within experiments.
- Experiments within comparable programs.
- Shared-control covariance.
- Hierarchical uncertainty.

Do not claim an exact reproduction of Netflix's proprietary implementation.

### Model D — Robust Hierarchical Bayesian

Investigate a heavy-tailed or mixture-based prior capable of accommodating rare large effects.

Use diagnostics and posterior predictive checks.

Compare its performance against simpler models.

Do not assume robustness solely because the model is more flexible.

### Computational considerations

PyMC models may be expensive to fit interactively.

Perform expensive training and benchmark jobs offline.

Save compact, versioned posterior or calibration artifacts.

Use fast prediction or precomputed results for the public Streamlit experience.

If predictions require retraining after arbitrary changes, clearly indicate that limitation.

Do not fake a hierarchical correction by substituting an unrelated fixed shrinkage factor.

The deployed app should not require downloading Upworthy or running hours of MCMC at startup.

## 6. Technical architecture

Create a clean, modular project structure, approximately:

- `streamlit_app.py`
- `app/`
- `src/data/`
- `src/calibration/`
- `src/simulation/`
- `src/statistics/`
- `src/models/`
- `src/evaluation/`
- `src/visualization/`
- `scripts/`
- `data/calibration/`
- `data/presets/`
- `research/`
- `tests/`
- `raw_data/`
- `README.md`
- `pyproject.toml`
- `.gitignore`

Adjust this structure if there is a more maintainable approach.

All raw Upworthy datasets must remain Git-ignored.

The published repository should contain compact artifacts needed to run the demo.

Use `st.session_state` to preserve scenarios, selected experiments, shuffled batches, and reveal stages.

Use Streamlit caching appropriately.

Changing a checkbox must not regenerate the experiment results.

Use Plotly for interactive plots.

Use deterministic NumPy random generators and isolated random streams where appropriate.

Prefer testable pure functions for simulations, estimators, launch policies, and benchmark metrics.

## 7. Reproducibility and quality requirements

Create automated tests for:

- Correct data loading and schema validation.
- Upworthy exclusion rules.
- Valid conversion probabilities and counts.
- Reproducible simulation results.
- Correct standard errors and confidence intervals.
- Statistical significance calculations.
- Monte Carlo calibration under known null effects.
- A/B/n covariance handling.
- Experiment-level selection and multiplicity adjustments.
- Correct calculation of naive and posterior estimates.
- No data leakage between generation, training, and evaluation.
- No exposure of true effects before the reveal action.
- No silent regeneration from Streamlit widget updates.
- Correct behavior when no experiments are selected.
- Correct behavior with zero launches or negative aggregate true effects.

Include unit tests, integration tests, and a basic Streamlit smoke test if feasible.

Create a reproducible command-line workflow for:

1. Inspecting and cleaning Upworthy.
2. Generating calibration artifacts.
3. Generating synthetic portfolios.
4. Fitting and validating models.
5. Running Monte Carlo benchmarks.
6. Starting Streamlit.

The README should explain both the easy demo workflow and the full research reproduction workflow.

Document all statistical assumptions, limitations and source references.

## 8. UX and visual design

The application should look like a polished data science product, not a notebook converted into Streamlit.

Use:

- Clean typography.
- Compact experiment cards.
- Consistent spacing and metric formatting.
- Restrained colors.
- Clear labels and intuitive explanations.
- Responsive layout.
- Minimal clutter.
- Expandable methodological details.
- Well-designed Plotly visualizations.

Avoid overwhelming visitors with controls or jargon.

Provide an intuitive default scenario so the experience works immediately.

Use progressive disclosure:

**Learn → Choose → Launch → Correct → Reveal → Understand.**

The interactive story is the main experience.

The methodological lab provides the scientific depth.

## 9. Research references

Use these publications as starting methodological references:

**Upworthy Research Archive**

https://upworthy.natematias.com/about-the-archive.html

https://upworthy.natematias.com/2024-06-upworthy-archive-update.html

**Amazon — Ryan Kessler**

https://www.amazon.science/publications/overcoming-the-winners-curse-leveraging-bayesian-inference-to-improve-estimates-of-the-impact-of-features-launched-via-a-b-tests

**Netflix — Estimating the Returns from an Experimentation Program**

https://simonejdemyr.com/docs/estimating-returns-2024.pdf

**Airbnb — Selection Bias in Online Experimentation**

https://medium.com/airbnb-engineering/selection-bias-in-online-experimentation-c3d67795cceb

**Optimizely**

https://www.optimizely.com/field-notes/guides/173000-experiments

**LiftArchive**

https://liftarchive.com/research/

**Spotify — Bayesian A/B Testing**

https://engineering.atspotify.com/2026/9/why-spotify-is-not-using-bayesian-a-b-testing

Check the sources before making detailed claims based on them. If a publication or website cannot be accessed, document the limitation rather than inventing results.

## 10. Implementation order

Develop incrementally, with a working application at each major milestone.

**Milestone 1 — Data foundation**

- Inspect existing files.
- Validate the Upworthy schema.
- Implement cleaning and quality filters.
- Produce an initial empirical calibration report.
- Set up reproducibility infrastructure.

**Milestone 2 — Simulation engine**

- Implement independently generated experiments.
- Add empirical calibration and scenario configurations.
- Implement effect estimation and selection policies.
- Validate simulations with tests.
- Produce a working Streamlit experiment-selection playground.

**Milestone 3 — Bayesian estimation**

- Implement naive and Empirical Bayes estimators.
- Implement the hierarchical model.
- Add robust variants where defensible.
- Integrate correction and ground-truth reveal actions.

**Milestone 4 — Benchmarking**

- Implement Monte Carlo evaluation.
- Add model comparisons and stress scenarios.
- Document failure cases and diagnostic results.

**Milestone 5 — Polish and publication**

- Complete narrative sections.
- Improve UX and visualizations.
- Document scientific references.
- Ensure the application starts without raw datasets.
- Prepare the repository for GitHub and Streamlit deployment.

Keep the app runnable throughout development.

Do not silently substitute arbitrary synthetic values when real calibration is missing. Use an explicitly labeled development fallback only if necessary, and document the limitation.

## 11. What I want you to do now

Start by inspecting the actual repository and `raw_data/` contents.

Then implement the project in the order above, making concrete progress rather than only describing future work.

Prioritize a complete, tested simulation engine and an end-to-end working Streamlit user experience.

Where a complex statistical component cannot yet be implemented reliably, isolate it behind a clear interface, document its status, and never present placeholder output as a validated correction.

At the end, report:

1. What was implemented.
2. What was validated.
3. What remains incomplete.
4. Which statistical assumptions require further investigation.
5. The exact local commands needed to run the application and reproduce the research.

The ultimate objective is a project that an experienced experimentation scientist at a company such as Amazon, Netflix, Spotify, or Airbnb could inspect and recognize as methodologically thoughtful, reproducible, transparent about limitations, and genuinely useful for understanding selection bias in online experimentation.
