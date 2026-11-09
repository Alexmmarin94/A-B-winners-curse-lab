"""Conservative Upworthy cleaning; preserve supplied partitions and whole experiments."""
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import numpy as np
import pandas as pd

RISK_FIELDS = ('problem', 'randomization_imbalace_risk', 'randomization_imbalance_risk')
REQUIRED = {'clickability_test_id', 'created_at', 'impressions', 'clicks'}


@dataclass
class CleanedPartition:
    clean: pd.DataFrame
    exclusions: pd.DataFrame
    report: dict


def load_archive(path: Path) -> pd.DataFrame:
    columns = pd.read_csv(path, nrows=0).columns.tolist()
    missing = REQUIRED - set(columns)
    if missing:
        raise ValueError(f'{path.name}: missing required columns {sorted(missing)}')
    package_column = '_id' if '_id' in columns else 'Unnamed: 0'
    if package_column not in columns:
        raise ValueError('Stable source package identifier is required.')
    wanted = list(REQUIRED) + [package_column] + [c for c in RISK_FIELDS if c in columns]
    frame = pd.read_csv(path, usecols=wanted, dtype=str)
    return frame.rename(columns={package_column: 'package_id'})


def source_hash(path: Path) -> str:
    digest = sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def clean_partition(raw: pd.DataFrame, partition: str) -> CleanedPartition:
    required = REQUIRED | {'package_id'}
    if required - set(raw.columns):
        raise ValueError(f'Missing columns: {sorted(required - set(raw.columns))}')
    df = raw.copy().reset_index(drop=True)
    ids = df.clickability_test_id.astype('string').fillna('').str.strip()
    missing_id = ids.eq('')
    # Missing IDs cannot be grouped into an invented experiment; each row gets a quarantine key.
    keys = ids.mask(missing_id, pd.Series([f'__missing_row_{i}' for i in df.index]))
    df['clickability_test_id'] = ids
    dates = pd.to_datetime(df.created_at, errors='coerce', format='mixed')
    if not pd.api.types.is_datetime64_dtype(dates.dtype):
        raise ValueError('Expected timezone-naive recorded dates; mixed/timezone-aware timestamps need review.')
    df['date'] = dates
    n = pd.to_numeric(df.impressions, errors='coerce')
    x = pd.to_numeric(df.clicks, errors='coerce')
    df['n'], df['x'] = n, x
    date_risk = dates.ge('2013-06-25') & dates.lt('2014-01-11')
    flags = {
        'missing_experiment_id': missing_id,
        'invalid_date': dates.isna(),
        'randomization_date_window': date_risk,
        'invalid_counts': (~np.isfinite(n) | ~np.isfinite(x) | (n <= 0) | (x < 0) | (x > n)
                           | n.mod(1).ne(0) | x.mod(1).ne(0)),
        'missing_package_id': df.package_id.astype('string').fillna('').str.strip().eq(''),
        'duplicate_package_id': df.package_id.duplicated(keep=False),
        'fewer_than_two_packages': keys.map(keys.value_counts()).lt(2),
    }
    risk_fields = [c for c in RISK_FIELDS if c in df]
    disagreement = pd.Series(False, index=df.index)
    for column in risk_fields:
        parsed = df[column].astype('string').str.lower().str.strip().map({'0': 0, '1': 1, 'false': 0, 'true': 1})
        flags[f'{column}_invalid'] = parsed.isna()
        flags[f'{column}_flagged'] = parsed.eq(1)
        flags[f'{column}_inconsistent_within_experiment'] = keys.map(parsed.groupby(keys).nunique()).gt(1)
        disagreement |= parsed.notna() & parsed.ne(date_risk.astype(int))
    if partition == 'undeployed':
        flags['undeployed_not_completed'] = pd.Series(True, index=df.index)
    reasons = pd.DataFrame(flags)
    grouped = reasons.groupby(keys, sort=True).any()
    excluded = grouped.any(axis=1)
    rejected_keys = set(grouped.index[excluded])
    keep = ~keys.isin(rejected_keys)
    clean = df.loc[keep].copy()
    clean[['n', 'x']] = clean[['n', 'x']].astype('int64')
    ledger = grouped.loc[excluded].copy()
    ledger.index.name = 'experiment_id_or_quarantine_row'
    report = {
        'partition': partition, 'rows_in': len(df), 'experiments_in': int(ids[~missing_id].nunique()),
        'missing_id_rows': int(missing_id.sum()), 'rows_retained': int(keep.sum()),
        'experiments_retained': int(clean.clickability_test_id.nunique()),
        'experiments_excluded': int(ids[~missing_id & ~keep].nunique()),
        'reason_counts_including_missing_id_quarantine_rows': {c: int(grouped[c].sum()) for c in grouped},
        'risk_columns': risk_fields, 'flag_date_disagreement_rows': int(disagreement.sum()),
        'boundary_policy': '[2013-06-25, 2014-01-11), recorded dates, whole experiment, union with flags',
        'note': 'Reasons overlap; do not add reason counts. Missing-ID rows are quarantined separately.',
    }
    return CleanedPartition(clean, ledger, report)


def partition_overlaps(partitions: dict[str, pd.DataFrame]) -> dict[str, int]:
    sets = {name: set(df.clickability_test_id.dropna()) - {''} for name, df in partitions.items()}
    names = list(sets)
    return {f'{a} / {b}': len(sets[a] & sets[b]) for i, a in enumerate(names) for b in names[i+1:]}


def paired_observations(clean: pd.DataFrame, pair_seed: int = 314159) -> pd.DataFrame:
    """One outcome-blind pair per experiment; orientation determined by salted stable hashes."""
    rows = []
    for identifier, group in clean.groupby('clickability_test_id', sort=True):
        order = sorted(range(len(group)), key=lambda i: sha256(
            f'{pair_seed}|{identifier}|{group.iloc[i].package_id}'.encode()).digest())
        control, treatment = group.iloc[order[0]], group.iloc[order[1]]
        nc, nt, xc, xt = map(int, (control.n, treatment.n, control.x, treatment.x))
        # A uniform half-count correction is disclosed; no selection on clicks or significance.
        y = np.log((xt + .5) / (nt - xt + .5)) - np.log((xc + .5) / (nc - xc + .5))
        se = np.sqrt(1 / (xt + .5) + 1 / (nt - xt + .5) + 1 / (xc + .5) + 1 / (nc - xc + .5))
        rows.append({'experiment_id': identifier, 'nc': nc, 'nt': nt, 'xc': xc, 'xt': xt,
                     'anchor_ctr': (xc + xt + 1) / (nc + nt + 2), 'log_odds_ratio': y, 'se': se,
                     'variant_count': len(group), 'month': str(group.date.min().to_period('M')),
                     'sparse_pair': min(xc, xt, nc-xc, nt-xt) < 5})
    return pd.DataFrame(rows)
