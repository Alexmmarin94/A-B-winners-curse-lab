"""Independent simulation checks for frozen priors; no tuning on simulated truth."""
import argparse
from dataclasses import replace
import json
from pathlib import Path
import numpy as np
from scipy.stats import t
from app.configuration import make_config
from app.scenarios import SCENARIO_BY_KEY
from src.models.artifacts import load_model,correct_observations
from src.simulation.engine import generate_portfolio


def summarize(values):
    values=np.array(values,dtype=float)
    if len(values)==0:
        return {'mean':None,'interval_95':None,'replications':0}
    m=float(values.mean())
    if len(values)<2:
        return {'mean':m,'interval_95':None,'replications':len(values)}
    half=float(t.ppf(.975,len(values)-1)*values.std(ddof=1)/np.sqrt(len(values)))
    return {'mean':m,'interval_95':[m-half,m+half],'replications':len(values)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--replications',type=int,default=20)
    parser.add_argument('--size',type=int,default=100)
    parser.add_argument('--estimator',choices=['empirical_bayes','hierarchical'],default='empirical_bayes')
    parser.add_argument('--output',type=Path,default=Path('data/models/validation_v1.json'))
    args=parser.parse_args()
    if args.replications<2:
        parser.error('Need at least two independent replications.')
    result={'schema_version':1,'replications':args.replications,'size_per_replication':args.size,
            'seed_start':73000101,'policy':'positive observed effect and two-sided unadjusted p < 0.05',
            'model_fitting':'Frozen before validation; no refitting or tuning on truth.',
            'interval_method':'t interval over independent portfolio-level metrics; not hyperparameter uncertainty.',
            'limitations':'Initial matched-scenario checks, not a comprehensive stress benchmark or real-data truth validation.',
            'scenarios':{}}
    for key in SCENARIO_BY_KEY:
        config=make_config(key)
        artifact=load_model(config,estimator=args.estimator)
        metrics={name:[] for name in ('naive_mae','posterior_mae','naive_bias','posterior_bias',
                    'naive_coverage','posterior_coverage','posterior_all_coverage','fraction_improved','paired_mae_change')}
        selected_count=unsupported_count=0
        for rep in range(args.replications):
            evaluation=replace(config,seed=73000101+rep,size=args.size)
            load_model(evaluation,estimator=args.estimator) # Enforce scope and no training-seed overlap.
            portfolio=generate_portfolio(evaluation)
            truth={r.experiment_id:r.effect for r in portfolio.truth}
            by_id={r.experiment_id:r for r in portfolio.observed}
            corrections,unsupported=correct_observations(portfolio.observed,by_id.keys(),artifact)
            all_covered=[estimate.ci_low<=truth[key]<=estimate.ci_high for key,estimate in corrections.items()]
            if all_covered:
                metrics['posterior_all_coverage'].append(float(np.mean(all_covered)))
            selected=[r.experiment_id for r in portfolio.observed if r.estimate.effect>0 and r.estimate.significant]
            selected_count+=len(selected)
            unsupported_count+=sum(key in unsupported for key in selected)
            common=[key for key in selected if key in corrections]
            if not common:
                continue
            naive=np.array([by_id[key].estimate.effect-truth[key] for key in common])
            adjusted=np.array([corrections[key].mean-truth[key] for key in common])
            metrics['naive_mae'].append(float(np.mean(abs(naive))))
            metrics['posterior_mae'].append(float(np.mean(abs(adjusted))))
            metrics['naive_bias'].append(float(naive.mean()))
            metrics['posterior_bias'].append(float(adjusted.mean()))
            metrics['naive_coverage'].append(float(np.mean([by_id[k].estimate.ci_low<=truth[k]<=by_id[k].estimate.ci_high for k in common])))
            metrics['posterior_coverage'].append(float(np.mean([corrections[k].ci_low<=truth[k]<=corrections[k].ci_high for k in common])))
            metrics['fraction_improved'].append(float(np.mean(abs(adjusted)<abs(naive))))
            metrics['paired_mae_change'].append(float(np.mean(abs(adjusted)-abs(naive))))
        result['scenarios'][key]={'artifact_id':artifact['artifact_id'],'selected_treatments':selected_count,
            'unsupported_selected':unsupported_count,'comparison_population':'Selected treatments supported by the correction; same records for both estimators.',
            'metrics':{name:summarize(values) for name,values in metrics.items()}}
        print(key, 'selected',selected_count,'unsupported',unsupported_count,
              'posterior selected coverage',result['scenarios'][key]['metrics']['posterior_coverage']['mean'],flush=True)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':
    main()
