"""Fit a quadrature-checked Normal hierarchy on exactly the existing observable histories."""
import argparse
from dataclasses import replace,asdict
import json
from pathlib import Path
from app.configuration import make_config
from app.scenarios import SCENARIO_BY_KEY
from src.models.artifacts import content_id,load_model
from src.models.hierarchical import fit_hierarchical
from src.models.robust import fit_robust
from src.models.normal_normal import stabilized_rate_difference
from src.calibration.artifacts import load_calibration
from src.data.upworthy import load_archive,clean_partition,paired_observations,source_hash
from src.simulation.engine import generate_observed


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw-dir',type=Path,default=Path('raw_data'))
    parser.add_argument('--output-dir',type=Path,default=Path('data/models'))
    parser.add_argument('--robust',action='store_true',help='Fit the fixed-center robust mixture hierarchy instead.')
    args=parser.parse_args();args.output_dir.mkdir(parents=True,exist_ok=True)
    for scenario in SCENARIO_BY_KEY:
        config=make_config(scenario); original=load_model(config)
        rows=[]
        if config.calibration_id:
            calibration=load_calibration(config.calibration_id)
            path=args.raw_dir/calibration['source']['filename']
            if source_hash(path)!=calibration['source']['sha256']:
                raise ValueError('Source hash mismatch.')
            pairs=paired_observations(clean_partition(load_archive(path),'exploratory').clean,calibration['policy']['pair_seed'])
            for r in pairs.itertuples():
                y,se=stabilized_rate_difference(r.xc,r.nc,r.xt,r.nt);rows.append([r.experiment_id,y,se])
        else:
            history=generate_observed(replace(config,seed=original['training']['simulation_seed'],size=original['training']['n']))
            for r in history:
                y,se=stabilized_rate_difference(r.control_successes,r.control_n,r.treatment_successes,r.treatment_n)
                rows.append([r.experiment_id,y,se])
        if content_id(rows)!=original['training']['observations_sha256']:
            raise ValueError('Histories differ between estimators.')
        if args.robust:
            fitted=fit_robust([r[1] for r in rows],[r[2] for r in rows])
            artifact={'schema_version':1,'model_version':'robust-mixture-rd-v1','scope':original['scope'],
                'training':original['training'],'fit':fitted['fit'],'robust':fitted,
                'assumptions':['Center fixed at zero; unlike the Normal hierarchy, a nonzero program mean is not learned.',
                    'Wide-component probability .05 and scale multiplier 5 are fixed assumptions, not tuned on evaluation truth.',
                    'Global scale has HalfNormal(.1) prior; integrated by checked quadrature.',
                    'Robustness and interval calibration are evaluated, never presumed.']}
            artifact['artifact_id']=content_id(artifact)
            (args.output_dir/f'{scenario}_robust_mixture_v1.json').write_text(json.dumps(artifact,indent=2,allow_nan=False)+'\n')
            print(scenario,fitted['diagnostics'],flush=True)
            continue
        hierarchy=fit_hierarchical([r[1] for r in rows],[r[2] for r in rows])
        artifact={'schema_version':1,'model_version':'hierarchical-normal-rd-v1','scope':original['scope'],
            'training':original['training'],'fit':hierarchy['fit'],'hierarchical':hierarchy,
            'assumptions':['Normal population with uncertain common mean and SD; fixed weak Normal/half-Normal hyperpriors.',
                'Approximate Normal measurement error, stabilized binomial SE treated as known.',
                'Separate comparable programs; no proprietary Netflix model or data.',
                'Individual prediction conditions on history plus that experiment; joint A/B/n prediction uses all contrasts and covariance.']}
        artifact['artifact_id']=content_id(artifact)
        (args.output_dir/f'{scenario}_hierarchical_normal_v1.json').write_text(json.dumps(artifact,indent=2,allow_nan=False)+'\n')
        print(scenario,hierarchy['diagnostics'],flush=True)


if __name__=='__main__':main()
