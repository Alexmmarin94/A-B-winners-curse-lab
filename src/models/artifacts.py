"""Versioned estimator artifacts with scenario, source, and overlap checks."""
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import numpy as np
from src.models.normal_normal import PriorFit, posterior, stabilized_rate_difference

MODEL_DIR=Path(__file__).resolve().parents[2]/'data/models'


def content_id(payload):
    return sha256(json.dumps(payload,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def load_model(config, directory=MODEL_DIR, estimator='empirical_bayes'):
    suffix={'empirical_bayes':'normal_normal_v1','hierarchical':'hierarchical_normal_v1','robust':'robust_mixture_v1'}
    if estimator not in suffix:
        raise ValueError('Estimator is not implemented.')
    artifact=json.loads((Path(directory)/f'{config.scenario}_{suffix[estimator]}.json').read_text())
    identifier=artifact.pop('artifact_id',None)
    if identifier != content_id(artifact):
        raise ValueError('Estimator artifact checksum mismatch.')
    artifact['artifact_id']=identifier
    if artifact['model_version'] not in ('normal-normal-rd-v1','hierarchical-normal-rd-v1','robust-mixture-rd-v1'):
        raise ValueError('Unsupported estimator version.')
    scope=artifact['scope']
    if (scope['scenario'],scope['metric'],scope['generator_version'],scope['calibration_id']) != (
        config.scenario,config.metric,config.version,config.calibration_id):
        raise ValueError('Historical model does not match this scenario, metric, or calibration version.')
    if not np.isclose(scope['baseline_metadata'],config.baseline,rtol=0,atol=1e-12):
        raise ValueError('Baseline assumptions differ from the fitted history.')
    if artifact['training'].get('simulation_seed')==config.seed:
        raise ValueError('This seed overlaps the synthetic training history. Use another portfolio seed.')
    fit=PriorFit(**artifact['fit'])
    if fit.n_history<100 or not np.isfinite([fit.mean,fit.variance]).all() or fit.variance<0:
        raise ValueError('Historical model is insufficiently supported or invalid.')
    return artifact


def correct_observations(observed, selected_ids, artifact):
    """Only observable records enter prediction. Sparse/boundary predictions are withheld."""
    by_id={item.experiment_id:item for item in observed}
    if not set(selected_ids)<=by_id.keys():
        raise ValueError('Selected experiments are not in this portfolio.')
    prior=PriorFit(**artifact['fit'])
    corrections,unsupported={},{}
    for key in selected_ids:
        item=by_id[key]
        if min(item.control_successes,item.treatment_successes,
               item.control_n-item.control_successes,item.treatment_n-item.treatment_successes)<5:
            unsupported[key]='A cell has fewer than five outcomes; this Normal approximation is not supported.'
            continue
        effect,se=stabilized_rate_difference(item.control_successes,item.control_n,
                                            item.treatment_successes,item.treatment_n)
        if artifact['model_version']=='robust-mixture-rd-v1':
            from src.models.robust import predict_robust
            estimate=predict_robust(effect,se,artifact)
        elif artifact['model_version']=='hierarchical-normal-rd-v1':
            from src.models.hierarchical import predict_hierarchical
            estimate=predict_hierarchical(effect,se,artifact)
        else:
            estimate=posterior(effect,se,prior)
        if estimate.ci_low < -1 or estimate.ci_high > 1:
            unsupported[key]='The Normal interval crosses the valid risk-difference range; no clipped posterior is substituted.'
            continue
        corrections[key]=estimate
    return corrections,unsupported
