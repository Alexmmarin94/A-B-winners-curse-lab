"""Predefined stress mechanisms, independent of estimator priors and evaluation truth use."""
from dataclasses import dataclass,replace
import numpy as np
from scipy.special import expit,logit
from src.simulation.engine import ObservedExperiment,generate_portfolio
from src.statistics.binary import estimate_binary

STRESS_CASES={
 'matched':'Original hypothetical retention mechanism; independent evaluation outcomes.',
 'null':'Exactly zero effects in every treatment; original hypothetical traffic.',
 'heterogeneous':'Two equally likely families with log-odds effects Uniform(-.25,.05) or Uniform(.05,.35). Pooled historical model is unchanged.',
 'rare_breakthroughs':'Original mixture plus a 6% chance of a positive Pareto(2.5) breakthrough, minimum .35 and cap 2 log-odds units.',
 'prior_shift':'Original mixture shifted upward by .25 log-odds units; history unchanged.',
 'temporal_shift':'Original mixture plus -.12, 0, .12, .24 log-odds by month; traffic grows 20% per month.',
 'low_power':'Original effects; control n is log-uniform from 200 to 2,000.',
 'abn':'Four independently generated treatments share one sampled control. At most one variant can launch.',
 'archive_ctr':'Frozen archive-calibrated pair generator, using archive-fitted estimator histories.',
}


@dataclass(frozen=True)
class MultiArmObservation:
    experiment_id: str
    contrasts: tuple[ObservedExperiment,...]
    covariance: np.ndarray


@dataclass(frozen=True)
class StressPortfolio:
    observed: tuple[MultiArmObservation,...]
    effects: tuple[tuple[float,...],...]


def shared_control_covariance(control_successes,control_n,treatment_successes,treatment_n):
    nc=int(control_n); nt=np.asarray(treatment_n,int);xt=np.asarray(treatment_successes,int)
    if nc<=0 or not 0<=control_successes<=nc or np.any(nt<=0) or np.any(xt<0) or np.any(xt>nt):
        raise ValueError('Invalid counts for shared-control covariance.')
    pc=(control_successes+.5)/(nc+1);pt=(xt+.5)/(nt+1)
    return np.full((len(nt),len(nt)),pc*(1-pc)/nc)+np.diag(pt*(1-pt)/nt)


def holm_adjust(pvalues):
    p=np.asarray(pvalues,float)
    if p.ndim!=1 or not np.isfinite(p).all() or np.any((p<0)|(p>1)):
        raise ValueError('Invalid p-values.')
    order=np.argsort(p,kind='stable');adjusted=np.empty(len(p))
    adjusted[order]=np.minimum(1,np.maximum.accumulate(p[order]*(len(p)-np.arange(len(p)))))
    return adjusted


def select_variant(observation):
    adjusted=holm_adjust([r.estimate.p_value for r in observation.contrasts])
    eligible=[i for i,r in enumerate(observation.contrasts) if r.estimate.effect>0 and adjusted[i]<.05]
    return max(eligible,key=lambda i:observation.contrasts[i].estimate.effect) if eligible else None


def _group(rows):
    first=rows[0]
    cov=shared_control_covariance(first.control_successes,first.control_n,
        [r.treatment_successes for r in rows],[r.treatment_n for r in rows])
    return MultiArmObservation(first.experiment_id.split(':')[0],tuple(rows),cov)


def generate_stress(config,case,seed,size):
    if case not in STRESS_CASES or size<1:
        raise ValueError('Unknown stress case or invalid portfolio size.')
    if case in ('matched','archive_ctr'):
        result=generate_portfolio(replace(config,seed=seed,size=size))
        return StressPortfolio(tuple(_group([r]) for r in result.observed),tuple((t.effect,) for t in result.truth))
    groups=[];truth=[]
    for index in range(size):
        streams=np.random.SeedSequence([seed,index,202605]).spawn(3)
        design,latent,sampling=(np.random.default_rng(s) for s in streams)
        month=int(design.integers(1,5)); count=4 if case=='abn' else 1
        bounds=(200,2000) if case=='low_power' else (2500,20000)
        nc=int(round(np.exp(design.uniform(*np.log(bounds)))))
        if case=='temporal_shift':nc=int(round(nc*(1+.2*month)))
        nt=np.rint(nc*design.uniform(.8,1.2,count)).astype(int)
        component=latent.choice(4,size=count,p=[.25,.50,.15,.10])
        edges=np.array([[0,0],[-.1,.12],[.12,.3],[-.3,-.12]])
        delta=np.array([latent.uniform(*edges[c]) for c in component])
        if case=='null':delta[:]=0
        elif case=='heterogeneous':
            family=int(latent.integers(2)); delta=latent.uniform(*[(-.25,.05),(.05,.35)][family],size=count)
        elif case=='rare_breakthroughs':
            breakthrough=latent.random(count)<.06
            delta=np.where(breakthrough,np.minimum(.35*(1+latent.pareto(2.5,count)),2),delta)
        elif case=='prior_shift':delta+=.25
        elif case=='temporal_shift':delta+=-.12+.12*(month-1)
        pc=config.baseline;pt=np.where(delta==0,pc,expit(logit(pc)+delta))
        xc=int(sampling.binomial(nc,pc));xt=sampling.binomial(nt,pt)
        identifier=f'{case}-{seed}-{index:04d}'
        rows=[ObservedExperiment(f'{identifier}:{i}',f'Variant {i+1}',config.scenario,config.metric,month,nc,int(nt[i]),xc,int(xt[i]),
                                 estimate_binary(xc,nc,int(xt[i]),int(nt[i])),count+1) for i in range(count)]
        groups.append(_group(rows));truth.append(tuple(float(p-pc) for p in pt))
    return StressPortfolio(tuple(groups),tuple(truth))
