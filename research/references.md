# References, roles, and access limits

Checked during development on 2026-11-08/09. These sources have distinct roles. Only the
local Upworthy exploratory data calibrate the empirical generator. No private Amazon,
Netflix, Airbnb, Spotify or Optimizely experiment records are available to this project.

| Source | Role here | Access and implementation boundary |
|---|---|---|
| [Upworthy archive](https://upworthy.natematias.com/about-the-archive.html) | Aggregate schema, partition and editorial-field interpretation | Documentation and actual local CSV schema inspected; no individual-level outcomes |
| [Upworthy June 2024 correction](https://upworthy.natematias.com/2024-06-upworthy-archive-update.html) | Randomization-risk exclusion | Whole-experiment date fallback implemented, inclusive boundaries; raw copies have no risk indicator |
| [Stephens (2017), False discovery rates: a new deal](https://doi.org/10.1093/biostatistics/kxw041) | Measurement-error-aware flexible effect-distribution estimation | Motivation for noise-aware mixtures; our fixed symmetric histogram family and calibration objective are not an exact ashr reproduction |
| [Kessler / Amazon Science (2024)](https://www.amazon.science/publications/overcoming-the-winners-curse-leveraging-bayesian-inference-to-improve-estimates-of-the-impact-of-features-launched-via-a-b-tests) | Selection bias in reported launch effects and Bayesian estimation | Publication page and abstract checked; our explicit normal-normal likelihood and MLE are independently implemented, not a claim to reproduce Amazon's analysis or datasets |
| [Netflix, Return-Aware Experimentation (2025)](https://netflixtechblog.medium.com/return-aware-experimentation-3dd93c94b67a) | Program-level impact and evaluation of launch decisions | Accessible official technical blog discusses choosing decision rules and experimentation returns; motivates separating estimation error from decision regret |
| [Airbnb, Selection Bias in Online Experimentation (2017)](https://medium.com/airbnb-engineering/selection-bias-in-online-experimentation-c3d67795cceb) | Educational explanation of selection bias in launch summaries | Article checked; no numerical lift, bias factor, or internal holdout is imported into our calibration |
| [Optimizely, Lessons learned from 173K experiments](https://www.optimizely.com/field-notes/guides/173000-experiments) | Aggregate experimentation context | Guide checked; its population, eligibility and winning definitions differ from ours. Reported uplift is not a latent-effect prior and observational comparisons are not transferred as causal effects |
| [LiftArchive research](https://liftarchive.com/research/) | Published-case context | Research index checked. No counts, win rates or selected case-study effects are used to estimate our latent distribution |
| [Spotify, Why Spotify Is Not Using Bayesian A/B Testing (2026)](https://engineering.atspotify.com/2026/9/why-spotify-is-not-using-bayesian-a-b-testing) | Prior relevance, decision guarantees and maintenance costs | Article checked. Our app does not implement or claim their sequential testing guarantees; experiments here have fixed horizons |

The original brief also links [Estimating the Returns from an Experimentation Program](https://simonejdemyr.com/docs/estimating-returns-2024.pdf).
Full text of that exact PDF was not verified in this session. The Netflix Research listing returned
only a page shell; the accessible official technical blog above was used for high-level motivation.
No paper-specific equations, empirical findings, or exact replication claims are attributed to the
unverified PDF. Our hierarchy is completely specified in `hierarchical_benchmark.md`.

The Amazon abstract explains that the suitability of prior beliefs matters and discusses
misspecification simulations. This project tests its own priors and data-generating mechanisms;
it does not transplant the paper's results. Likewise, the Netflix discussion motivates evaluating
decisions under explicit business utility, but our disjoint 10,000-user populations and zero launch
cost are pedagogical assumptions. They are not a model of Netflix's product economics.

## Data attribution

Matias, J. N., Munger, K., Aubin Le Quéré, M., and Ebersole, C. R. (2021).
*The Upworthy Research Archive, a time series of 32,487 experiments in U.S. media.*
Scientific Data. Archive material is distributed under CC BY 4.0.
Derived artifacts retain source filenames and hashes, author attribution, license, exclusions
and modeling choices. Raw headlines and source experiment/package identifiers are not included
in the demo's design reservoir. Source URLs and source licenses do not imply endorsement.

The project's software uses the MIT license in `LICENSE`. The archive's CC BY 4.0 data
license is separate; neither license grants rights to third-party company articles.
