"""A fixed-center scale-mixture hierarchy; robustness is an empirical question.

mu is fixed at zero. tau ~ HalfNormal(.1); each theta has a .95 Normal(0,tau²)
component and a .05 Normal(0,25*tau²) component. Only tau is learned. This model
integrates scale uncertainty but deliberately does not estimate a nonzero center.
"""
import numpy as np
from scipy.special import logsumexp
from src.models.hierarchical import predict_hierarchical


def fit_robust(y,se,points=4097):
    y,se=np.asarray(y,float),np.asarray(se,float)
    if y.ndim!=1 or y.shape!=se.shape or len(y)<3 or not np.isfinite(y).all() or not np.isfinite(se).all() or np.any(se<=0):
        raise ValueError('Invalid historical observations.')
    def integrate(n):
        log_tau=np.linspace(np.log(1e-7),0,n);tau=np.exp(log_tau);likelihood=[]
        for chunk in np.array_split(tau,max(1,int(np.ceil(n/128)))):
            variance=se[None,:,None]**2+chunk[:,None,None]**2*np.array([1.,25.])
            logs=np.log([.95,.05])-.5*(np.log(2*np.pi*variance)+y[None,:,None]**2/variance)
            likelihood.extend(logsumexp(logs,axis=2).sum(axis=1))
        lw=np.array(likelihood)+np.log(np.sqrt(2/np.pi)/.1)-.5*(tau/.1)**2+log_tau+np.log(log_tau[1]-log_tau[0])
        lw[[0,-1]]-=np.log(2);evidence=float(logsumexp(lw));weights=np.exp(lw-evidence)
        return tau,weights,evidence
    coarse=integrate(points);tau,weights,evidence=integrate(2*points-1)
    change=abs(evidence-coarse[2]);edge=float(weights[:8].sum()+weights[-8:].sum())
    if change>1e-5 or edge>1e-6:raise RuntimeError('Robust quadrature failed refinement or boundary check.')
    keep=weights>1e-12;discarded=float(weights[~keep].sum());tau,weights=tau[keep],weights[keep];weights/=weights.sum()
    return {'tau':tau.tolist(),'weights':weights.tolist(),'center':0.,'wide_probability':.05,'wide_scale':5.,
            'fit':{'mean':0.,'variance':float(weights@(2.2*tau**2)),'n_history':len(y),'log_likelihood':evidence,'boundary':False},
            'diagnostics':{'method':'fixed-center mixture likelihood with log-tau quadrature','coarse_points':points,
                           'fine_points':2*points-1,'log_evidence_change':change,'edge_mass':edge,'discarded_mass':discarded}}


def predict_robust(effect,standard_error,artifact):
    model=artifact['robust'];tau=np.array(model['tau']);weights=np.array(model['weights'])
    expanded={'hierarchical':{'nodes':{'tau':np.r_[tau,model['wide_scale']*tau],
        'weights':np.r_[(1-model['wide_probability'])*weights,model['wide_probability']*weights],
        'mu_mean':np.zeros(2*len(tau)),'mu_variance':np.zeros(2*len(tau))}}}
    return predict_hierarchical(effect,standard_error,expanded)
