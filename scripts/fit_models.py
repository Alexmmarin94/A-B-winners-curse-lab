"""Fit normal-normal priors from independent observable histories, then freeze artifacts."""
import argparse
from dataclasses import asdict, replace
import json
from pathlib import Path
import numpy as np
from app.configuration import make_config
from app.scenarios import SCENARIO_BY_KEY
from src.calibration.artifacts import load_calibration
from src.data.upworthy import load_archive, clean_partition, paired_observations, source_hash
from src.models.artifacts import content_id
from src.models.normal_normal import fit_normal_normal, fit_uncertainty, stabilized_rate_difference
from src.simulation.engine import generate_observed


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw-dir',type=Path,default=Path('raw_data'))
    parser.add_argument('--output-dir',type=Path,default=Path('data/models'))
    parser.add_argument('--bootstrap',type=int,default=100)
    args=parser.parse_args()
    if args.bootstrap<20:
        parser.error('At least 20 bootstrap refits are required.')
    args.output_dir.mkdir(parents=True,exist_ok=True)
    for key in SCENARIO_BY_KEY:
        config=make_config(key)
        rows=[]
        if key=='upworthy_ctr':
            artifact=load_calibration(config.calibration_id)
            path=args.raw_dir/artifact['source']['filename']
            if source_hash(path)!=artifact['source']['sha256']:
                raise ValueError('Raw archive does not match the frozen calibration source.')
            pairs=paired_observations(clean_partition(load_archive(path),'exploratory').clean,
                                      artifact['policy']['pair_seed'])
            for r in pairs.itertuples():
                y,se=stabilized_rate_difference(r.xc,r.nc,r.xt,r.nt)
                rows.append([r.experiment_id,y,se])
            training={'kind':'real exploratory archive pairs','source_sha256':source_hash(path),
                      'pair_seed':artifact['policy']['pair_seed'],'sparse_pairs_retained':int(pairs.sparse_pair.sum()),
                      'description':'3,823 eligible exploratory Upworthy pairs; all outcomes, not editorial winners.'}
        else:
            history_config=replace(config,seed=73000001,size=3000)
            history=generate_observed(history_config)
            for r in history:
                y,se=stabilized_rate_difference(r.control_successes,r.control_n,r.treatment_successes,r.treatment_n)
                rows.append([r.experiment_id,y,se])
            training={'kind':'independent synthetic historical portfolio','simulation_seed':history_config.seed,
                      'config':asdict(history_config),
                      'description':'3,000 independent synthetic historical experiments under this hypothetical program; no real product data.'}
        y,se=np.array([r[1] for r in rows]),np.array([r[2] for r in rows])
        fit=fit_normal_normal(y,se)
        payload={'schema_version':1,'model_version':'normal-normal-rd-v1',
                 'scope':{'scenario':key,'metric':config.metric,'generator_version':config.version,
                          'calibration_id':config.calibration_id,'baseline_metadata':config.baseline},
                 'training':{**training,'observations_sha256':content_id(rows),'n':len(rows)},
                 'fit':asdict(fit),'fitting_uncertainty':fit_uncertainty(y,se,args.bootstrap),
                 'assumptions':['Independent Normal risk-difference prior and approximate Normal measurement errors.',
                     'Half-count-stabilized binomial SE; historical sparse pairs retained to avoid outcome-based trimming.',
                     'Estimated SE is treated as known; prior effect/precision independence can fail.',
                     'Conditional plug-in credible intervals omit hyperparameter uncertainty and are not guaranteed after selection.',
                     'A compatible model can still worsen estimates or under-cover extreme effects.'],
                 'reference':'https://www.amazon.science/publications/overcoming-the-winners-curse-leveraging-bayesian-inference-to-improve-estimates-of-the-impact-of-features-launched-via-a-b-tests'}
        payload['artifact_id']=content_id(payload)
        target=args.output_dir/f'{key}_normal_normal_v1.json'
        target.write_text(json.dumps(payload,indent=2,allow_nan=False)+'\n')
        print(f'{key}: n={len(rows)}, prior mean={100*fit.mean:.4f} pp, prior SD={100*np.sqrt(fit.variance):.4f} pp; {payload["artifact_id"][:12]}',flush=True)


if __name__=='__main__':
    main()
