"""Evaluate frozen observation-model predictions on independent observable outcomes only."""
import argparse
from dataclasses import replace
import json
from pathlib import Path
import numpy as np
from app.configuration import make_config
from app.scenarios import SCENARIO_BY_KEY
from src.calibration.artifacts import load_calibration
from src.data.upworthy import load_archive,clean_partition,paired_observations,source_hash
from src.models.artifacts import load_model,content_id
from src.models.normal_normal import stabilized_rate_difference
from src.models.predictive import predictive_scores
from src.simulation.engine import generate_observed
from scripts.validate_models import summarize


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw-dir',type=Path,default=Path('raw_data'))
    parser.add_argument('--output',type=Path,default=Path('data/models/predictive_checks_v1.json'))
    args=parser.parse_args()
    report={'version':'predictive-checks-v1','scenarios':{},
        'interpretation':'Predictions of new observed rate differences conditional on their estimated SEs and frozen history. No new effect is used to update its own predictive distribution.',
        'limitations':['Approximate Normal observation model, not exact binomial count predictions.',
            'Coverage refers to new observed estimates, not posterior intervals for selected true effects.',
            'SEs are estimated from the same counts and treated as fixed; PIT need not be uniform under misspecification.',
            'Intervals treat experiments as independent and histories as fixed. No parameters are tuned using this check.']}
    for key in SCENARIO_BY_KEY:
        config=make_config(key);seed=93000000;rows=[]
        if config.calibration_id:
            matches=list(args.raw_dir.glob('*archive-confirmatory-packages*.csv'))
            if len(matches)!=1:raise ValueError('Expected one confirmatory source.')
            calibration=load_calibration(config.calibration_id)
            pairs=paired_observations(clean_partition(load_archive(matches[0]),'confirmatory').clean,calibration['policy']['pair_seed'])
            for r in pairs.itertuples():
                y,se=stabilized_rate_difference(r.xc,r.nc,r.xt,r.nt);rows.append([r.experiment_id,y,se])
            source={'partition':'confirmatory','sha256':source_hash(matches[0])}
        else:
            evaluation=replace(config,seed=seed,size=3000)
            for r in generate_observed(evaluation):
                y,se=stabilized_rate_difference(r.control_successes,r.control_n,r.treatment_successes,r.treatment_n)
                rows.append([r.experiment_id,y,se])
            source={'partition':'independent hypothetical program','simulation_seed':seed}
        y,se=np.array([r[1:] for r in rows]).T
        entry={'n':len(rows),'source':source,'observations_sha256':content_id(rows),'methods':{}}
        for method in ['empirical_bayes','hierarchical','robust']:
            model=load_model(replace(config,seed=seed),estimator=method)
            scores,pit=predictive_scores(y,se,model)
            entry['methods'][method]={'artifact_id':model['artifact_id'],'mean_log_density_nats':summarize(scores),
                'central_95_predictive_coverage':summarize(((pit>=.025)&(pit<=.975)).astype(float)),
                'pit_decile_counts':np.histogram(pit,np.linspace(0,1,11))[0].tolist()}
        report['scenarios'][key]=entry
        print(key,len(rows),{m:round(v['central_95_predictive_coverage']['mean'],3) for m,v in entry['methods'].items()},flush=True)
    report['artifact_id']=content_id(report)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':main()
