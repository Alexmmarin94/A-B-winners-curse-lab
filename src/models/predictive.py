"""Observable predictive checks conditional on a frozen history and supplied measurement SEs."""
import numpy as np
from scipy.special import logsumexp, ndtr


def predictive_scores(effects, standard_errors, artifact):
    """Return log density and PIT before conditioning on each new observed effect.

    These are approximate Normal observation-model checks, not binomial posterior
    predictive counts or evidence of coverage for selected latent effects.
    """
    y,se=np.asarray(effects,float),np.asarray(standard_errors,float)
    if y.ndim!=1 or y.shape!=se.shape or not np.isfinite(y).all() or not np.isfinite(se).all() or np.any(se<=0):
        raise ValueError('Require aligned finite observations and positive standard errors.')
    version=artifact['model_version']
    if version=='normal-normal-rd-v1':
        means=np.array([artifact['fit']['mean']]);variance=np.array([artifact['fit']['variance']]);weights=np.ones(1)
    elif version=='hierarchical-normal-rd-v1':
        nodes=artifact['hierarchical']['nodes']
        means=np.array(nodes['mu_mean']);variance=np.array(nodes['tau'])**2+np.array(nodes['mu_variance'])
        weights=np.array(nodes['weights'])
    elif version=='robust-mixture-rd-v1':
        model=artifact['robust'];tau=np.array(model['tau']);w=np.array(model['weights'])
        variance=np.r_[tau**2,(model['wide_scale']*tau)**2];means=np.zeros(len(variance))
        weights=np.r_[(1-model['wide_probability'])*w,model['wide_probability']*w]
    else:raise ValueError('Unsupported predictive model.')
    scores=[];pits=[]
    for start in range(0,len(y),512):
        total=se[start:start+512,None]**2+variance
        residual=y[start:start+512,None]-means
        scores.extend(logsumexp(np.log(weights)-.5*(np.log(2*np.pi*total)+residual**2/total),axis=1))
        # Roundoff in a normalized mixture can put its CDF a few ulps above 1.
        pits.extend(np.clip(ndtr(residual/np.sqrt(total))@weights,0,1))
    return np.asarray(scores),np.asarray(pits)
