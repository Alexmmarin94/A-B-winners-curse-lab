"""Load only verified, versioned calibration artifacts; never fall back silently."""
from hashlib import sha256
import json
from pathlib import Path
import numpy as np

ARTIFACT_PATH = Path(__file__).resolve().parents[2] / 'data/calibration/upworthy_paired_ctr_v1.json'


def load_calibration(expected_id=None, path=ARTIFACT_PATH):
    artifact = json.loads(Path(path).read_text(encoding='utf-8'))
    identifier = artifact.pop('artifact_id', None)
    actual = sha256(json.dumps(artifact, sort_keys=True, separators=(',',':')).encode()).hexdigest()
    if identifier != actual or (expected_id is not None and identifier != expected_id):
        raise ValueError('Calibration checksum/version mismatch. Restore the referenced artifact or explicitly create a new portfolio.')
    artifact['artifact_id'] = identifier
    if artifact['schema_version'] != 1 or artifact['policy']['version'] != 'upworthy-paired-ctr-v1':
        raise ValueError('Unsupported calibration schema or generator policy.')
    weights = np.asarray(artifact['mixture']['weights'])
    edges = np.asarray(artifact['policy']['edges'])
    rows = np.asarray(artifact['design_rows'])
    if len(weights) != len(edges) or not np.isfinite(weights).all() or np.any(weights < 0) or not np.isclose(weights.sum(), 1):
        raise ValueError('Invalid calibration mixture weights.')
    if edges[0] != 0 or np.any(np.diff(edges) <= 0) or not np.isfinite(edges).all():
        raise ValueError('Invalid calibration mixture support.')
    if rows.ndim != 2 or len(rows) == 0 or rows.shape[1] != 4 or not np.isfinite(rows).all():
        raise ValueError('Invalid design reservoir.')
    if np.any(rows[:,:2] < 1) or np.any(rows[:,:2] % 1) or np.any((rows[:,2] <= 0) | (rows[:,2] >= 1)):
        raise ValueError('Invalid sample sizes or anchor probabilities.')
    return artifact
