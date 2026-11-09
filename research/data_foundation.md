# Data foundation and final validation

## Verified local schema

The input directory contains four CSVs:

- `upworthy-archive-exploratory-packages-03.12.2020.csv`
- `upworthy-archive-confirmatory-packages-03.12.2020.csv`
- `upworthy-archive-holdout-packages-03.12.2020.csv`
- `upworthy-archive-undeployed-packages.01.12.2021.csv`

Each contains `clickability_test_id`, `created_at`, `impressions`, and `clicks`.
The deployed partitions have an unnamed first column; undeployed has `_id` instead.
Neither `problem` nor the documented randomization-risk aliases occurs in these copies.
See `archive_inventory.json` for exact columns, row counts, and source hashes.

The original inventory is supplemented by the implemented quality report in
`data/calibration/quality_report.json` and the frozen paired-CTR calibration artifact.
All raw files remain unchanged and Git-ignored.

## Sources checked on 2026-11-08

- [Archive documentation](https://upworthy.natematias.com/about-the-archive.html)
- [June 2024 correction](https://upworthy.natematias.com/2024-06-upworthy-archive-update.html)

The archive describes aggregate packages grouped by `clickability_test_id`, with no
individual-level records. Its `significance` field is not an interpretable p-value and
`winner` denotes editorial selection. These columns will not define our significance tests.

The correction warns of randomization concerns from June 25, 2013 through January 10, 2014.
The implemented fallback excludes both boundary days: recorded dates in
`[2013-06-25, 2014-01-11)`. The docs say `created_at` has unknown timezone; do not convert
timestamps to an assumed timezone. Exclude the entire experiment if any package overlaps
the affected interval. Date parsing failures must be quarantined and counted. This is a
conservative implementation policy, covered by boundary and experiment-level exclusion tests.

The documentation uses both `problem` and `randomization_imbalace_risk` (its spelling).
The loader recognizes these and the correctly spelled alias, validates flag values,
and counts conflicts with dates rather than silently ignoring them. Exclusion uses the union
of affected dates and flags. Missing/invalid flags and inconsistent flags within a test are
quarantined conservatively; a zero flag never overrides an affected date.

## Partition policy, before fitting

| Partition | Intended use |
|---|---|
| Exploratory | Develop data-quality rules and calibration methods |
| Confirmatory | Evaluate frozen calibration choices; document any subsequent revision |
| Holdout | Final observable-distribution validation after choices are frozen |
| Undeployed | Inventory only; not assumed to be completed experiments |

ID checks found no overlap between deployed partitions. The undeployed file shares five IDs
with confirmatory and one with holdout; undeployed records are excluded in full. Holdout
schema/count validity was checked before fitting. Its final observable-distribution check is now complete without refitting; see `calibration_v1.md`.

## Exclusions produced from the actual local files

| Partition | Experiments in | Retained | Excluded | Missing-ID rows |
|---|---:|---:|---:|---:|
| Exploratory | 4,873 | 3,823 | 1,050 | 0 |
| Confirmatory | 22,743 | 17,833 | 4,910 | 0 |
| Holdout | 4,871 | 3,812 | 1,059 | 0 |
| Undeployed | 18,514 | 0 | 18,514 | 57 |

All excluded deployed experiments overlap the randomization-risk period. Two excluded
confirmatory tests also have fewer than two packages; reasons overlap and must not be summed.
Any invalid row excludes its whole experiment: malformed/nonpositive sample sizes, counts
outside [0, n], noninteger counts, invalid dates, missing or duplicate package IDs, and risk flags.
Rows without an experiment ID are quarantined separately, not invented into an experiment.

The machine-readable report includes source SHA-256 hashes, boundary policy, input/retained
row counts, and overlapping reason counts. Per-experiment reason ledgers stay local under
`.local/quality/`. An undeployed exclusion does not imply every one of its rows has zero traffic;
these records are not trusted as complete experiments.

## Implemented decisions and remaining investigations

1. Cleaning and experiment-level ledgers are implemented as described above.
2. A stable salted hash of experiment/package IDs chooses and orients one pair per experiment,
   without using outcomes, winner, significance, or traffic. The reference is an arbitrary
   comparator, not a meaningful untreated control. Each experiment contributes one likelihood
   observation, avoiding pseudo-replication from shared-reference comparisons.
3. Traffic, paired pooled CTR anchors, variants per source test, measurement precision, and
   monthly changes are recorded in the artifact. Shared-control correlation is described by
   plug-in binomial covariance for three arms; it is not used as independent calibration data.
4. A heteroscedastic histogram-mixture likelihood accounts approximately for measurement
   error. Bootstrap and sensitivity results are saved. Sparse-pair approximation, tail
   identification, and baseline/effect/precision dependence require further investigation.
5. CTR effects do not directly calibrate the four product contexts. The new CTR laboratory
   is separate and explicitly limited to pairs. A hypothetical A/B/n benchmark now uses one shared control and four treatments.
6. Source roles and access limitations are documented in `references.md`. No proprietary company-specific model or dataset is reproduced.

Calibration, simulation, three Bayesian fitting workflows, and repeated estimator benchmarking are implemented. See `calibration_v1.md` and `hierarchical_benchmark.md` for methods, failures and checks.
