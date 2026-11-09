"""Independent binomial experiments with explicit hypothetical or archive-derived designs.

Latent log-odds changes follow a point-mass/uniform mixture independent of
any evaluated estimator. The empirical variant requires an exact artifact hash.
Aggregate binomial sampling avoids user-level rows.
Truth and observable observations have different types and return paths.
"""

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from math import exp, log
from numbers import Integral
import zlib

import numpy as np
from scipy.special import expit, logit

from src.statistics.binary import BinaryEstimate, estimate_binary


@dataclass(frozen=True)
class SimulationConfig:
    scenario: str
    metric: str
    baseline: float
    interventions: tuple[str, ...]
    seed: int = 20261108
    size: int = 36
    version: str = "hypothetical-ab-v1"
    calibration_id: str | None = None

    def __post_init__(self) -> None:
        if not (0 < self.baseline < 1) or (self.version == "hypothetical-ab-v1" and not 0.01 <= self.baseline <= 0.95):
            raise ValueError("This development generator supports baselines from 0.01 to 0.95.")
        if not self.scenario or not self.metric or not self.interventions:
            raise ValueError("Scenario, metric, and intervention names are required.")
        if any(not isinstance(v, Integral) or isinstance(v, bool) for v in (self.seed, self.size)):
            raise ValueError("Seed and size must be integers.")
        if self.seed < 0 or not 1 <= self.size <= 10000:
            raise ValueError("Require a nonnegative seed and a portfolio size from 1 to 10000.")
        if self.version not in ("hypothetical-ab-v1", "upworthy-paired-ctr-v1"):
            raise ValueError("Unsupported generator version.")
        if self.version == "upworthy-paired-ctr-v1" and (self.scenario != "upworthy_ctr" or not self.calibration_id):
            raise ValueError("Empirical CTR generation requires the matching scenario and an artifact ID.")
        if self.version == "hypothetical-ab-v1" and self.calibration_id is not None:
            raise ValueError("Hypothetical scenarios must not claim a calibration artifact.")

    @property
    def fingerprint(self) -> str:
        return sha256(json.dumps(asdict(self), sort_keys=True).encode()).hexdigest()[:12]


@dataclass(frozen=True)
class ObservedExperiment:
    experiment_id: str
    name: str
    scenario: str
    metric: str
    month: int
    control_n: int
    treatment_n: int
    control_successes: int
    treatment_successes: int
    estimate: BinaryEstimate
    source_variant_count: int = 2


@dataclass(frozen=True)
class ExperimentTruth:
    experiment_id: str
    control_probability: float
    treatment_probability: float
    effect: float


@dataclass(frozen=True)
class SimulationResult:
    observed: tuple[ObservedExperiment, ...]
    truth: tuple[ExperimentTruth, ...]


def generate_portfolio(config: SimulationConfig) -> SimulationResult:
    observed, truth = [], []
    scenario_code = zlib.crc32(config.scenario.encode())
    calibration = None
    if config.version == "upworthy-paired-ctr-v1":
        from src.calibration.artifacts import load_calibration
        calibration = load_calibration(config.calibration_id)
    for index in range(config.size):
        # Separate design, latent-effect, and outcome streams for each experiment.
        streams = np.random.SeedSequence([config.seed, scenario_code, index, 1]).spawn(3)
        design, latent, sampling = (np.random.default_rng(stream) for stream in streams)
        control_n = int(round(exp(design.uniform(log(2500), log(20000)))))
        treatment_n = int(round(control_n * design.uniform(0.8, 1.2)))
        month = int(design.integers(1, 5))
        source_variant_count = 2
        if calibration is None:
            component = int(latent.choice(4, p=[0.25, 0.50, 0.15, 0.10]))
            bounds = ((0.0, 0.0), (-0.10, 0.12), (0.12, 0.30), (-0.30, -0.12))
            delta = float(latent.uniform(*bounds[component]))
            pc = config.baseline
            pt = pc if component == 0 else float(expit(logit(pc) + delta))
        else:
            row = calibration['design_rows'][int(design.integers(len(calibration['design_rows'])))]
            control_n, treatment_n, anchor, source_variant_count = row
            component = int(latent.choice(len(calibration['mixture']['weights']), p=calibration['mixture']['weights']))
            edges = calibration['policy']['edges']
            delta = 0.0 if component == 0 else float(latent.uniform(edges[component-1], edges[component]) * latent.choice([-1, 1]))
            pc, pt = float(expit(logit(anchor)-delta/2)), float(expit(logit(anchor)+delta/2))
        xc = int(sampling.binomial(control_n, pc))
        xt = int(sampling.binomial(treatment_n, pt))
        identifier = f"{config.scenario}-{config.seed}-{index + 1:03d}"
        cycle, name_index = divmod(index, len(config.interventions))
        name = config.interventions[name_index] + (f" · iteration {cycle + 1}" if cycle else "")
        observed.append(ObservedExperiment(identifier, name, config.scenario, config.metric, month,
                                            control_n, treatment_n, xc, xt,
                                            estimate_binary(xc, control_n, xt, treatment_n), source_variant_count))
        truth.append(ExperimentTruth(identifier, pc, pt, pt - pc))
    return SimulationResult(tuple(observed), tuple(truth))


def generate_observed(config: SimulationConfig) -> tuple[ObservedExperiment, ...]:
    """UI/estimator boundary: return only observations; discard generated truth."""
    return generate_portfolio(config).observed
