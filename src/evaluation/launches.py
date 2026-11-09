"""A descriptive summary, not an estimate of additive business impact."""

from dataclasses import dataclass
from statistics import mean

from src.simulation.engine import ObservedExperiment


@dataclass(frozen=True)
class LaunchSummary:
    reviewed_ids: tuple[str, ...]
    selected_ids: tuple[str, ...]
    mean_reported_effect: float | None


def summarize_launches(observed: tuple[ObservedExperiment, ...], reviewed: set[str],
                       selections: dict[str, bool]) -> LaunchSummary:
    by_id = {item.experiment_id: item for item in observed}
    if not reviewed <= by_id.keys():
        raise ValueError("Reviewed experiments must belong to this portfolio.")
    selected = tuple(sorted(key for key in reviewed if selections.get(key, False)))
    if len({(by_id[key].scenario, by_id[key].metric) for key in reviewed}) > 1:
        raise ValueError("Do not aggregate different scenarios or metrics.")
    return LaunchSummary(tuple(sorted(reviewed)), selected,
                         mean(by_id[key].estimate.effect for key in selected) if selected else None)
