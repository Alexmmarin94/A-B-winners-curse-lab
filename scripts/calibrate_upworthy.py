"""Clean local partitions, then fit and freeze calibration using exploratory data only."""
import argparse
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import numpy as np
import pandas as pd
from src.calibration.mixture import EDGES, bootstrap_mixture, fit_mixture, latent_summary
from src.data.upworthy import clean_partition, load_archive, paired_observations, partition_overlaps, source_hash

POLICY = {
    'version': 'upworthy-paired-ctr-v1', 'training_partition': 'exploratory', 'pair_seed': 314159,
    'method': 'symmetric histogram mixture with heteroscedastic approximate Normal log-odds likelihood',
    'effect_scale': 'log odds ratio between outcome-blind randomly oriented variants',
    'edges': EDGES.tolist(), 'design_reservoir_size': 512, 'design_seed': 271828,
    'half_count_correction': 0.5,
}


def quantiles(values):
    return dict(zip(['q01', 'q10', 'q50', 'q90', 'q99'], map(float, np.quantile(values, [.01,.1,.5,.9,.99]))))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw-dir', type=Path, default=Path('raw_data'))
    parser.add_argument('--output-dir', type=Path, default=Path('data/calibration'))
    parser.add_argument('--bootstrap', type=int, default=100)
    args = parser.parse_args()
    paths = {}
    for name in ('exploratory', 'confirmatory', 'holdout', 'undeployed'):
        matches = list(args.raw_dir.glob(f'*archive-{name}-packages*.csv'))
        if len(matches) != 1:
            raise ValueError(f'Expected exactly one {name} file; found {len(matches)}')
        paths[name] = matches[0]
    frames = {name: load_archive(path) for name, path in paths.items()}
    overlaps = partition_overlaps(frames)
    deployed = ('exploratory', 'confirmatory', 'holdout')
    if any(value for key, value in overlaps.items() if all(name in deployed for name in key.split(' / '))):
        raise ValueError(f'Deployed partition overlap requires review: {overlaps}')
    cleaned = {name: clean_partition(frame, name) for name, frame in frames.items()}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    local = Path('.local/quality'); local.mkdir(parents=True, exist_ok=True)
    quality = {'schema_version': 1, 'policy': POLICY, 'source_hashes': {n: source_hash(p) for n,p in paths.items()},
               'partition_overlap_counts': overlaps, 'partitions': {n: r.report for n,r in cleaned.items()}}
    for name, result in cleaned.items():
        result.exclusions.to_csv(local / f'{name}-exclusions.csv')
        print(f'{name}: retained {result.report["experiments_retained"]}/{result.report["experiments_in"]} experiments', flush=True)
    (args.output_dir/'quality_report.json').write_text(json.dumps(quality, indent=2)+'\n')
    train = cleaned['exploratory'].clean
    pairs = paired_observations(train, POLICY['pair_seed'])
    y, se = pairs.log_odds_ratio.to_numpy(), pairs.se.to_numpy()
    fit = fit_mixture(y, se)
    print(f'Fitted {len(pairs)} pairs; bootstrap begins ({args.bootstrap} replications).', flush=True)
    uncertainty = bootstrap_mixture(y, se, replications=args.bootstrap)
    alternate = paired_observations(train, POLICY['pair_seed']+1)
    alternate_fit = fit_mixture(alternate.log_odds_ratio.to_numpy(), alternate.se.to_numpy())
    extended_edges = np.append(EDGES, 6.4)
    extended_fit = fit_mixture(y, se, extended_edges)
    reservoir = pairs.iloc[np.random.default_rng(POLICY['design_seed']).choice(
        len(pairs), min(POLICY['design_reservoir_size'],len(pairs)), replace=False)]
    design_rows = [[int(r.nc), int(r.nt), float(r.anchor_ctr), int(r.variant_count)] for r in reservoir.itertuples()]
    monthly = []
    for month, group in pairs.groupby('month'):
        monthly.append({'month': month, 'experiments': len(group), 'median_anchor_ctr': float(group.anchor_ctr.median()),
                        'median_pair_impressions': float((group.nc+group.nt).median()),
                        'median_log_odds_se': float(group.se.median()), 'median_variants': float(group.variant_count.median())})
    correlations = []
    for _, group in train.groupby('clickability_test_id'):
        if len(group) >= 3:
            arms = group.sort_values('package_id').iloc[:3]
            p = (arms.x+.5)/(arms.n+1)
            v = (p*(1-p)/arms.n).to_numpy()
            correlations.append(float(v[0]/np.sqrt((v[0]+v[1])*(v[0]+v[2]))))
    artifact = {
        'schema_version': 1, 'policy': POLICY, 'source': {'filename': paths['exploratory'].name,
            'sha256': quality['source_hashes']['exploratory'], 'archive_license': 'CC BY 4.0'},
        'references': ['https://upworthy.natematias.com/about-the-archive.html',
            'https://upworthy.natematias.com/2024-06-upworthy-archive-update.html',
            'https://doi.org/10.1093/biostatistics/kxw041'],
        'training': {'experiments': len(pairs), 'sparse_pairs': int(pairs.sparse_pair.sum()),
                     'observed_log_odds_sd': float(np.std(y, ddof=1)), 'median_se': float(np.median(se))},
        'mixture': {'weights': fit.weights.tolist(), 'log_likelihood': fit.log_likelihood,
                    'iterations': fit.iterations, 'optimality_gap': fit.optimality_gap,
                    'summary': latent_summary(fit.weights), 'uncertainty': uncertainty},
        'sensitivity': {'alternate_pair_seed': POLICY['pair_seed']+1,
                        'alternate_pair_summary': latent_summary(alternate_fit.weights),
                        'extended_grid_edges': extended_edges.tolist(),
                        'extended_grid_summary': latent_summary(extended_fit.weights, extended_edges)},
        'design_columns': ['control_n', 'treatment_n', 'smoothed_pooled_pair_ctr', 'source_variant_count'],
        'design_rows': design_rows,
        'descriptive': {'sample_size_per_arm': quantiles(train.n),
                        'pair_anchor_ctr': quantiles(pairs.anchor_ctr), 'source_variants': quantiles(pairs.variant_count),
                        'measurement_se_log_odds': quantiles(se), 'observed_log_odds': quantiles(y),
                        'shared_control_correlation': quantiles(correlations),
                        'shared_control_note': 'Plug-in binomial correlation for first three package IDs; descriptive only. Generator uses one pair, not A/B/n.',
                        'monthly': monthly},
        'limitations': [
            'Approximate Normal measurement errors with half-count log odds; sparse pairs and estimated SEs can distort calibration.',
            'Symmetric bounded histogram support, effect/SE independence, and exchangeability are assumptions; tails are weakly identified.',
            'Bootstrap is conditional on modeling choices; it is not a guarantee of latent-effect identification.',
            'Random pairs are not editorial winners or meaningful untreated controls.',
            'Design reservoir preserves joint paired traffic and pooled CTR approximately; pooled CTR is a noisy plug-in anchor, not a latent baseline estimate.',
            'Latent effects are drawn independently of design; midpoint log odds links anchor CTR to two arm probabilities.',
            'Four synthetic months are labels, not a replay of archive chronology. Temporal changes are reported but not simulated.',
            'Only pairwise CTR is calibrated; no direct transfer to retention, activation, acquisition, or paid conversion.',
            'Confirmatory data is reserved for checking the frozen artifact; holdout outcomes are reserved for final validation.'
        ]}
    canonical = json.dumps(artifact, sort_keys=True, separators=(',',':'))
    artifact['artifact_id'] = sha256(canonical.encode()).hexdigest()
    target = args.output_dir/'upworthy_paired_ctr_v1.json'
    target.write_text(json.dumps(artifact, indent=2)+'\n')
    print(f'Frozen artifact {artifact["artifact_id"][:12]}: {target}', flush=True)


if __name__ == '__main__':
    main()
