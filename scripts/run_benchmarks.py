"""Repeated paired comparisons of frozen estimators under predefined independent stress mechanisms."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import numpy as np
from app.configuration import make_config
from src.models.artifacts import content_id,load_model
from src.models.hierarchical import predict_joint,predict_hierarchical
from src.models.normal_normal import PriorFit,posterior
from src.models.robust import predict_robust
from src.simulation.stress import STRESS_CASES,generate_stress,select_variant
from scripts.validate_models import summarize

METHODS=('naive','empirical_bayes','hierarchical','robust')
METRICS=('bias_pp','mae_pp','rmse_pp','coverage','exceptional_mae_pp','cumulative_absolute_error_conversions',
         'decision_regret_conversions','mae_change_vs_naive_pp')


def evaluate_portfolio(portfolio,models,exception_threshold):
    if set(models)!=set(METHODS)-{'naive'}:
        raise ValueError('Every implemented estimator must receive the same evaluation portfolio.')
    selected={m:[] for m in METHODS};regret={m:[] for m in METHODS};exceptional={m:[] for m in METHODS}
    selected_truth=[];unsupported=0;total_selected=0
    for observation,truth_tuple in zip(portfolio.observed,portfolio.effects):
        truth=np.asarray(truth_tuple); rows=observation.contrasts
        choice=select_variant(observation);total_selected+=choice is not None
        # All models receive identical counts/contrasts and measurement covariance.
        if any(min(r.control_successes,r.control_n-r.control_successes,r.treatment_successes,r.treatment_n-r.treatment_successes)<5 for r in rows):
            unsupported+=1;continue
        y=np.array([r.estimate.effect for r in rows]);cov=observation.covariance
        predictions={'naive':[(r.estimate.effect,r.estimate.ci_low,r.estimate.ci_high) for r in rows]}
        for method,artifact in models.items():
            if len(y)==1:
                if method=='robust':p=predict_robust(y[0],float(np.sqrt(cov[0,0])),artifact)
                elif method=='hierarchical':p=predict_hierarchical(y[0],float(np.sqrt(cov[0,0])),artifact)
                else:p=posterior(y[0],float(np.sqrt(cov[0,0])),PriorFit(**artifact['fit']))
                result=(p,)
            else:result=predict_joint(y,cov,artifact)
            predictions[method]=[(p.mean,p.ci_low,p.ci_high) for p in result]
        if any(lo < -1 or hi > 1 for method in models for _,lo,hi in predictions[method]):
            unsupported+=1;continue
        for method,values in predictions.items():
            means=np.array([v[0] for v in values]);decision=int(np.argmax(means))
            utility=truth[decision] if means[decision]>0 else 0
            regret[method].append(10000*(max(0,float(truth.max()))-utility))
            if choice is not None:
                mean,lo,hi=values[choice];error=mean-truth[choice]
                selected[method].append((error,lo<=truth[choice]<=hi))
                if abs(truth[choice])>=exception_threshold:exceptional[method].append(abs(error)*100)
        if choice is not None:selected_truth.append(float(truth[choice]))
    results={}
    for method in METHODS:
        records=selected[method];errors=np.array([v[0] for v in records]);count=len(errors)
        results[method]={'selected_supported':count,'exceptional_selected':len(exceptional[method]),
            'bias_pp':float(errors.mean()*100) if count else None,
            'mae_pp':float(abs(errors).mean()*100) if count else None,
            'rmse_pp':float(np.sqrt(np.mean(errors**2))*100) if count else None,
            'coverage':float(np.mean([v[1] for v in records])) if count else None,
            'exceptional_mae_pp':float(np.mean(exceptional[method])) if exceptional[method] else None,
            'cumulative_absolute_error_conversions':float(abs(errors.sum())*10000),
            'decision_regret_conversions':float(np.mean(regret[method])) if regret[method] else None}
    for method in METHODS:
        results[method]['mae_change_vs_naive_pp']=results[method]['mae_pp']-results['naive']['mae_pp'] if selected_truth else None
    return {'metrics':results,'selected_total':int(total_selected),'unsupported_experiments':unsupported,
            'supported_experiments':len(regret['naive']),'selected_true_total':float(sum(selected_truth))}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--replications',type=int,default=30);parser.add_argument('--size',type=int,default=60)
    parser.add_argument('--output',type=Path,default=Path('data/benchmarks/stress_v1.json'))
    args=parser.parse_args()
    if args.replications<2 or args.size<1:parser.error('Require at least two replications and positive size.')
    report={'schema_version':1,'version':'stress-v2','replications':args.replications,'size':args.size,
        'methods':list(METHODS),'seed_start':92000000,
        'selection_policy':'Choose at most one positive variant with Holm-adjusted two-sided p < .05, ranked by observed effect.',
        'intervals':'Student-t confidence intervals across independent portfolio-level metrics; frozen fitted histories.',
        'decision_utility':'Each experiment has a separate deployment population of 10,000, one metric, and no interactions. Oracle chooses max(0, true effects). Each estimator chooses the variant with the highest positive estimated mean, otherwise no launch. No significance threshold for this separate decision comparison.',
        'cumulative_estimand':'Sum of selected effects times 10,000 for disjoint equal-sized populations. Not compounded uplift or shared-population ROI.',
        'fairness':'Same supported experiments, counts, contrasts, and covariance for every estimator. No truth enters fitting or selection. Unsupported groups are excluded from all estimators and counted.',
        'limitations':['Fixed training artifacts; uncertainty intervals do not include new-history variability.',
            'All stress mechanisms except the paired CTR case are hypothetical. Robust mixture fixes its center at zero and its broad-component assumptions.',
            'Full A/B/n is implemented in the benchmark generator and covariance-aware predictions, not the nine-card A/B challenge UI.'],
        'cases':{}}
    for index,(case,description) in enumerate(STRESS_CASES.items()):
        config=make_config('upworthy_ctr' if case=='archive_ctr' else 'retention')
        models={m:load_model(config,estimator=m) for m in ('empirical_bayes','hierarchical','robust')}
        records=[]
        for rep in range(args.replications):
            seed=92000000+index*1000+rep
            if any(seed==a['training'].get('simulation_seed') for a in models.values()):raise ValueError('Training seed overlap.')
            portfolio=generate_stress(config,case,seed,args.size)
            records.append(evaluate_portfolio(portfolio,models,.01 if case=='archive_ctr' else .05))
        entry={'description':description,'config':asdict(config),'exception_threshold_probability':.01 if case=='archive_ctr' else .05,
            'model_ids':{m:a['artifact_id'] for m,a in models.items()},'seeds':[92000000+index*1000+r for r in range(args.replications)],
            'selected_total':sum(r['selected_total'] for r in records),'unsupported_experiments':sum(r['unsupported_experiments'] for r in records),
            'supported_experiments':sum(r['supported_experiments'] for r in records),'methods':{}}
        for method in METHODS:
            entry['methods'][method]={metric:summarize([r['metrics'][method][metric] for r in records if r['metrics'][method][metric] is not None]) for metric in METRICS}
            entry['methods'][method]['selected_supported']=sum(r['metrics'][method]['selected_supported'] for r in records)
            entry['methods'][method]['exceptional_selected']=sum(r['metrics'][method]['exceptional_selected'] for r in records)
        report['cases'][case]=entry
        print(case,'selected',entry['selected_total'],'unsupported',entry['unsupported_experiments'],flush=True)
    report['artifact_id']=content_id(report)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':main()
