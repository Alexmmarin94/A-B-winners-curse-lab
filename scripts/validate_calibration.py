"""Check a frozen calibration on an explicitly selected validation partition without refitting."""
import argparse
import json
from pathlib import Path
import numpy as np
from scipy.stats import ks_2samp, norm, wasserstein_distance
from src.calibration.artifacts import load_calibration
from src.calibration.mixture import predictive_log_density
from src.data.upworthy import clean_partition, load_archive, paired_observations, source_hash
from src.simulation.engine import SimulationConfig, generate_observed


def distribution(values):
    return dict(zip(['q01','q10','q50','q90','q99'], map(float, np.quantile(values, [.01,.1,.5,.9,.99]))))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw-dir', type=Path, default=Path('raw_data'))
    parser.add_argument('--partition', choices=['confirmatory','holdout'], default='confirmatory')
    parser.add_argument('--seed', type=int, default=8675309)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.output is None:
        args.output = Path(f'data/calibration/{args.partition}_validation.json')
    artifact = load_calibration()
    matches = list(args.raw_dir.glob(f'*archive-{args.partition}-packages*.csv'))
    if len(matches) != 1:
        raise ValueError(f'Expected exactly one {args.partition} file.')
    real = paired_observations(clean_partition(load_archive(matches[0]), args.partition).clean,
                               artifact['policy']['pair_seed'])
    weights, edges = artifact['mixture']['weights'], artifact['policy']['edges']
    y, se = real.log_odds_ratio.to_numpy(), real.se.to_numpy()
    improvement = predictive_log_density(y, se, weights, edges) - norm.logpdf(y, scale=se)
    # The artifact is already frozen and hashed before any validation outcomes enter here.
    config = SimulationConfig('upworthy_ctr', 'Click-through rate',
        artifact['descriptive']['pair_anchor_ctr']['q50'], ('Synthetic headline pair',),
        seed=args.seed, size=6000, version='upworthy-paired-ctr-v1', calibration_id=artifact['artifact_id'])
    simulated = generate_observed(config)
    synthetic_y = np.array([np.log((r.treatment_successes+.5)/(r.treatment_n-r.treatment_successes+.5))
                            -np.log((r.control_successes+.5)/(r.control_n-r.control_successes+.5)) for r in simulated])
    comparisons = {
        'pair_impressions': ((real.nc+real.nt).to_numpy(), np.array([r.control_n+r.treatment_n for r in simulated])),
        'pooled_ctr': ((real.xc+real.xt)/(real.nc+real.nt), np.array([(r.control_successes+r.treatment_successes)/(r.control_n+r.treatment_n) for r in simulated])),
        'observed_effect_pp': ((real.xt/real.nt-real.xc/real.nc)*100, np.array([r.estimate.effect*100 for r in simulated])),
        'observed_log_odds_ratio': (y, synthetic_y),
    }
    mean, standard_error = float(improvement.mean()), float(improvement.std(ddof=1)/np.sqrt(len(improvement)))
    report = {'schema_version': 1, 'artifact_id': artifact['artifact_id'], 'partition': args.partition,
              'source_sha256': source_hash(matches[0]), 'real_experiments': len(real), 'simulated_experiments': len(simulated),
              'simulation_seed': config.seed, 'sparse_real_pairs': int(real.sparse_pair.sum()),
              'predictive_check': {'mean_log_density_gain_over_zero_effect_nats': mean,
                 'mean_gain_interval_95': [mean-1.96*standard_error,mean+1.96*standard_error],
                 'note': 'Paired mean score contrast under approximate Normal likelihood, not an estimator-performance benchmark.'},
              'observable_comparisons': {name: {args.partition: distribution(a), 'synthetic': distribution(b),
                 'ks_distance': float(ks_2samp(a,b).statistic), 'wasserstein_distance': float(wasserstein_distance(a,b))}
                 for name,(a,b) in comparisons.items()},
              'limitations': ['Descriptive diagnostics; no threshold was used to tune the frozen artifact.',
                 'One fixed synthetic validation portfolio; sampling variation is not a full Monte Carlo benchmark.',
                 'No true effects exist for archive observations, so this cannot validate latent-effect recovery.',
                 'This selected partition is used only for diagnostic evaluation, never for fitting or tuning this artifact.']}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'artifact': artifact['artifact_id'][:12], 'real': len(real), 'synthetic':len(simulated),
                      'ks_distances': {k:v['ks_distance'] for k,v in report['observable_comparisons'].items()}},indent=2))


if __name__ == '__main__':
    main()
