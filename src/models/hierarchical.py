"""Normal hierarchical inference with integrated program mean and scale uncertainty.

mu ~ Normal(0, .1^2), tau ~ HalfNormal(.1); theta_i | mu,tau ~ Normal(mu,tau^2).
Historical observations have known approximate heteroscedastic Normal errors.
Integrate mu analytically and tau by checked log-grid quadrature, not fake MCMC.
"""
import numpy as np
from scipy.special import logsumexp, ndtr
from scipy.optimize import brentq
from src.models.normal_normal import PosteriorEstimate


def mixture_quantile(probability, means, variances, weights):
    means,variances,weights=map(np.asarray,(means,variances,weights))
    sd=np.sqrt(np.maximum(variances,1e-30))
    lo=float(np.min(means-12*sd)); hi=float(np.max(means+12*sd))
    return float(brentq(lambda value:float(weights@ndtr((value-means)/sd))-probability,lo,hi,xtol=1e-12))


def _quadrature(y,se,points,mu_scale,tau_scale):
    log_tau=np.linspace(np.log(1e-7),np.log(1.0),points)
    tau=np.exp(log_tau); v0=mu_scale**2
    likelihood=[]; means=[]; variances=[]
    for values in np.array_split(tau, max(1,int(np.ceil(points/128)))):
        total=se[None,:]**2+values[:,None]**2
        precision=1/v0+np.sum(1/total,axis=1)
        linear=np.sum(y[None,:]/total,axis=1)
        quadratic=np.sum(y[None,:]**2/total,axis=1)
        likelihood.extend(-.5*(len(y)*np.log(2*np.pi)+np.log(total).sum(axis=1)
                              +np.log(v0*precision)+quadratic-linear**2/precision))
        means.extend(linear/precision); variances.extend(1/precision)
    means,variances=np.array(means),np.array(variances)
    log_weights=np.array(likelihood)+np.log(np.sqrt(2/np.pi)/tau_scale)-.5*(tau/tau_scale)**2+log_tau
    log_weights+=np.log(log_tau[1]-log_tau[0]);log_weights[[0,-1]]-=np.log(2)
    evidence=float(logsumexp(log_weights)); weights=np.exp(log_weights-evidence)
    return tau,means,variances,weights,evidence


def fit_hierarchical(effects, standard_errors, points=4097, mu_scale=.1, tau_scale=.1):
    y,se=np.asarray(effects,float),np.asarray(standard_errors,float)
    if y.ndim!=1 or y.shape!=se.shape or len(y)<3 or not np.isfinite(y).all() or not np.isfinite(se).all() or np.any(se<=0):
        raise ValueError('Require aligned finite observations and positive standard errors.')
    if points<257 or mu_scale<=0 or tau_scale<=0:
        raise ValueError('Invalid quadrature settings.')
    coarse=_quadrature(y,se,points,mu_scale,tau_scale)
    fine=_quadrature(y,se,2*points-1,mu_scale,tau_scale)
    tau,means,variances,weights,evidence=fine
    evidence_difference=abs(evidence-coarse[-1])
    edge_mass=float(weights[:8].sum()+weights[-8:].sum())
    if evidence_difference>1e-5 or edge_mass>1e-6:
        raise RuntimeError(f'Quadrature did not converge: log-evidence change={evidence_difference}, edge mass={edge_mass}')
    keep=weights>1e-12
    discarded=float(weights[~keep].sum())
    tau,means,variances,weights=(x[keep] for x in (tau,means,variances,weights))
    weights/=weights.sum()
    mean=float(weights@means)
    predictive_variance=float(weights@(tau**2+variances+means**2)-mean**2)
    return {'nodes':{'tau':tau.tolist(),'mu_mean':means.tolist(),'mu_variance':variances.tolist(),'weights':weights.tolist()},
            'fit':{'mean':mean,'variance':predictive_variance,'n_history':len(y),'log_likelihood':evidence,'boundary':False},
            'hyperprior':{'mu_mean':0,'mu_sd':mu_scale,'tau_halfnormal_sd':tau_scale},
            'hyperparameter_intervals_95':{
                'mu':[mixture_quantile(q,means,variances,weights) for q in [.025,.975]],
                'tau':[float(np.interp(q,np.cumsum(weights),tau)) for q in [.025,.975]]},
            'diagnostics':{'method':'analytic mu integration and trapezoidal log-tau quadrature',
                           'coarse_points':points,'fine_points':2*points-1,'log_evidence_change':evidence_difference,
                           'edge_mass':edge_mass,'discarded_mass':discarded,'retained_nodes':int(keep.sum())}}


def predict_hierarchical(effect, standard_error, artifact):
    if not np.isfinite([effect,standard_error]).all() or standard_error<=0:
        raise ValueError('Invalid prediction inputs.')
    nodes=artifact['hierarchical']['nodes']
    tau,means,mu_variance,weights=(np.asarray(nodes[k]) for k in ('tau','mu_mean','mu_variance','weights'))
    prior_variance=tau**2+mu_variance
    total=prior_variance+standard_error**2
    log_weights=np.log(weights)-.5*(np.log(2*np.pi*total)+(effect-means)**2/total)
    weights=np.exp(log_weights-logsumexp(log_weights))
    w=prior_variance/total
    posterior_mean=w*effect+(1-w)*means
    posterior_variance=w*standard_error**2
    mean=float(weights@posterior_mean)
    variance=float(weights@(posterior_variance+(posterior_mean-mean)**2))
    return PosteriorEstimate(mean,float(np.sqrt(variance)),
        mixture_quantile(.025,posterior_mean,posterior_variance,weights),
        mixture_quantile(.975,posterior_mean,posterior_variance,weights),
        float(weights@(1-w)),standard_error)


def predict_joint(effects,covariance,artifact):
    """Condition on all treatment/control contrasts in an experiment, respecting covariance."""
    y=np.asarray(effects,float); covariance=np.asarray(covariance,float)
    if y.ndim!=1 or covariance.shape!=(len(y),len(y)) or not np.isfinite(y).all() or not np.isfinite(covariance).all():
        raise ValueError('Invalid multivariate observation.')
    if not np.allclose(covariance,covariance.T) or np.linalg.eigvalsh(covariance).min()<=0:
        raise ValueError('Measurement covariance must be symmetric positive definite.')
    if artifact['model_version']=='normal-normal-rd-v1':
        tau=np.array([np.sqrt(artifact['fit']['variance'])]); means=np.array([artifact['fit']['mean']])
        mu_variance=np.array([0.]); weights=np.array([1.])
    elif artifact['model_version']=='robust-mixture-rd-v1':
        from itertools import product
        model=artifact['robust'];scales=np.array(model['tau']);mass=np.array(model['weights'])
        patterns=np.array(list(product([0,1],repeat=len(y))))
        pattern_weights=np.prod(np.where(patterns,model['wide_probability'],1-model['wide_probability']),axis=1)
        # Each treatment has a local component indicator; all share the uncertain global scale.
        component_variances=(scales[:,None,None]**2*model['wide_scale']**(2*patterns[None,:,:])).reshape(-1,len(y))
        prior=np.array([np.diag(v) for v in component_variances])
        means=np.zeros(len(prior));weights=(mass[:,None]*pattern_weights).ravel()
        tau=None;mu_variance=None
    else:
        nodes=artifact['hierarchical']['nodes']
        tau,means,mu_variance,weights=(np.array(nodes[k]) for k in ('tau','mu_mean','mu_variance','weights'))
    dimension=len(y)
    if artifact['model_version']!='robust-mixture-rd-v1':
        prior=tau[:,None,None]**2*np.eye(dimension)+mu_variance[:,None,None]*np.ones((dimension,dimension))
    total=prior+covariance
    residual=y[None,:]-means[:,None]
    inverse=np.linalg.inv(total)
    log_weights=np.log(weights)-.5*(dimension*np.log(2*np.pi)+np.linalg.slogdet(total)[1]
        +np.einsum('bi,bij,bj->b',residual,inverse,residual))
    weights=np.exp(log_weights-logsumexp(log_weights))
    gain=prior@inverse
    conditional_mean=means[:,None]+np.einsum('bij,bj->bi',gain,residual)
    conditional_cov=prior-gain@prior
    result=[]
    for i in range(dimension):
        m=conditional_mean[:,i];v=np.maximum(conditional_cov[:,i,i],0)
        mean=float(weights@m);sd=float(np.sqrt(weights@(v+(m-mean)**2)))
        result.append(PosteriorEstimate(mean,sd,mixture_quantile(.025,m,v,weights),
            mixture_quantile(.975,m,v,weights),float(weights@(1-gain[:,i,i])),float(np.sqrt(covariance[i,i]))))
    return tuple(result)
