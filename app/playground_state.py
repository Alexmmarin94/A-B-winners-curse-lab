"""Session logic separated from Streamlit widgets for repeatable interaction tests."""

from dataclasses import asdict, dataclass, field, replace

import numpy as np

from src.evaluation.launches import LaunchSummary, summarize_launches
from src.simulation.engine import ObservedExperiment, SimulationConfig, generate_observed
from src.models.normal_normal import PosteriorEstimate
from src.models.artifacts import load_model, correct_observations


@dataclass
class Playground:
    config: SimulationConfig
    observed: tuple[ObservedExperiment, ...]
    order: tuple[int, ...]
    batch: int = 0
    reviewed: set[str] = field(default_factory=set)
    selections: dict[str, bool] = field(default_factory=dict)
    summary: LaunchSummary | None = None
    summary_invalidated: bool = False
    corrections: dict[str, PosteriorEstimate] | None = None
    unsupported: dict[str, str] = field(default_factory=dict)
    correction_model: dict | None = None
    revealed_effects: dict[str, float] | None = None
    stage_error: str | None = None
    ever_revealed: bool = False
    locked_batches: tuple[int, ...] = ()
    selection_version: int = 2

    @classmethod
    def create(cls, config: SimulationConfig) -> "Playground":
        # Five stable candidate batches leave two interchangeable batches even after
        # three rounds are locked. Shuffle changes candidates, never their outcomes.
        config = replace(config, size=max(45, ((config.size+8)//9)*9))
        observed = generate_observed(config)
        order = tuple(int(i) for i in np.random.default_rng(
            np.random.SeedSequence([config.seed, 7189])).permutation(config.size))
        return cls(config, observed, order)

    @property
    def batches(self) -> int:
        return (len(self.observed) + 8) // 9

    def batch_items(self, batch: int) -> tuple[ObservedExperiment, ...]:
        return tuple(self.observed[i] for i in self.order[batch * 9:(batch + 1) * 9])

    @property
    def current_ids(self) -> set[str]:
        return {item.experiment_id for item in self.batch_items(self.batch)}

    @property
    def active_ids(self) -> set[str]:
        return self.current_ids | {item.experiment_id for batch in self.locked_batches
                                  for item in self.batch_items(batch)}

    @property
    def can_add_more(self) -> bool:
        return len(self.locked_batches) < 3

    def invalidate(self) -> None:
        self.summary_invalidated = self.summary_invalidated or self.summary is not None
        self.summary = None
        self.clear_correction()

    def clear_correction(self) -> None:
        self.corrections = None
        self.unsupported = {}
        self.correction_model = None
        self.revealed_effects = None
        self.stage_error = None

    def visible(self) -> tuple[ObservedExperiment, ...]:
        items = self.batch_items(self.batch)
        for item in items:
            key = item.experiment_id
            if key not in self.reviewed:
                self.invalidate()
                self.reviewed.add(key)
                self.selections[key] = item.estimate.effect > 0 and item.estimate.significant
        return items

    def shuffle(self) -> None:
        for key in self.current_ids:
            self.selections[key] = False
        self._next_batch()

    def _next_batch(self) -> None:
        candidates = [(self.batch + step) % self.batches for step in range(1, self.batches)]
        self.batch = next(batch for batch in candidates if batch not in self.locked_batches)
        self.invalidate()
        for item in self.batch_items(self.batch):
            self.reviewed.add(item.experiment_id)
            self.selections[item.experiment_id] = item.estimate.effect > 0 and item.estimate.significant

    def add_more(self) -> bool:
        if not self.can_add_more:
            return False
        self.visible()
        self.locked_batches += (self.batch,)
        self._next_batch()
        return True

    def select(self, key: str, value: bool) -> None:
        if key not in self.reviewed or key not in self.current_ids:
            raise ValueError("Only the current batch is editable; saved rounds are locked.")
        if self.selections[key] != value:
            self.selections[key] = value
            self.invalidate()

    def analyze(self) -> None:
        self.clear_correction()
        self.summary = summarize_launches(self.observed, self.reviewed & self.active_ids, self.selections)
        self.summary_invalidated = False

    def correct(self) -> None:
        if self.summary is None or not self.summary.selected_ids:
            raise ValueError("Analyze at least one selected treatment before applying a correction.")
        artifact = load_model(self.config)
        corrections, unsupported = correct_observations(self.observed, self.summary.selected_ids, artifact)
        self.correction_model = artifact
        self.corrections, self.unsupported = corrections, unsupported
        self.revealed_effects = None
        self.stage_error = None

    def reveal(self) -> None:
        if self.summary is None or self.corrections is None:
            raise ValueError("Apply the correction before revealing truth.")
        # Called only on explicit reveal. Verify replay before exposing any true effect.
        from src.simulation.engine import generate_portfolio
        replay = generate_portfolio(self.config)
        if replay.observed != self.observed:
            raise ValueError("Generator replay differs from the reviewed portfolio; truth was not revealed.")
        chosen = set(self.summary.selected_ids)
        self.revealed_effects = {item.experiment_id: item.effect for item in replay.truth
                                 if item.experiment_id in chosen}
        self.ever_revealed = True
        self.stage_error = None

    def snapshot(self) -> dict:
        if self.summary is None:
            raise ValueError("Analyze launches before exporting a snapshot.")
        payload = {"config": asdict(self.config), "summary": asdict(self.summary),
                   "observed": [asdict(item) for item in self.observed if item.experiment_id in self.summary.reviewed_ids],
                   "selection": {"version": self.selection_version, "current_batch": self.batch,
                                 "locked_batches": list(self.locked_batches), "order": list(self.order),
                                 "seen_ids": sorted(self.reviewed)},
                   "units": "Effects and intervals are probability differences; multiply by 100 for percentage points."}
        if self.corrections is not None:
            payload['correction_model_id'] = self.correction_model['artifact_id']
            payload['corrections'] = {key: asdict(value) for key, value in self.corrections.items()}
            payload['unsupported_corrections'] = self.unsupported
        if self.revealed_effects is not None:
            payload['revealed_effects'] = dict(self.revealed_effects)
        return payload


def restore_playground(previous) -> Playground:
    """Rebind a hot-reloaded session to current classes without losing stage progress."""
    from src.statistics.binary import BinaryEstimate
    data = asdict(previous)
    data['config'] = SimulationConfig(**data['config'])
    data['observed'] = tuple(ObservedExperiment(**{
        **item, 'estimate': BinaryEstimate(**item['estimate'])}) for item in data['observed'])
    if 'selection_version' not in data:
        # Preserve old choices as saved rounds instead of silently deleting them.
        data['locked_batches'] = tuple(batch for batch in range((len(data['observed'])+8)//9)
            if batch != data['batch'] and any(data['observed'][i].experiment_id in data['reviewed']
                for i in data['order'][batch*9:(batch+1)*9]))
        data['selection_version'] = 2
    if len(data['observed']) < 45:
        config = replace(data['config'], size=45)
        extended = generate_observed(config)
        if extended[:len(data['observed'])] != data['observed']:
            raise ValueError('Cannot extend this session without changing its observed experiments.')
        data['order'] = tuple(data['order']) + tuple(range(len(data['observed']),45))
        data['observed'], data['config'] = extended, config
    if data.get('summary') is not None:
        data['summary'] = LaunchSummary(**data['summary'])
    if data.get('corrections') is not None:
        data['corrections'] = {key: PosteriorEstimate(**value) for key, value in data['corrections'].items()}
    return Playground(**data)
