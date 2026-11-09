"""Resolve explicitly distinct hypothetical and archive-derived configurations."""
from app.scenarios import SCENARIO_BY_KEY
from src.calibration.artifacts import load_calibration
from src.simulation.engine import SimulationConfig


def make_config(key: str, seed: int = 20261108) -> SimulationConfig:
    scenario = SCENARIO_BY_KEY[key]
    if key == "upworthy_ctr":
        artifact = load_calibration()
        return SimulationConfig(key, scenario.metric, artifact['descriptive']['pair_anchor_ctr']['q50'],
                                scenario.interventions, seed=seed, version='upworthy-paired-ctr-v1',
                                calibration_id=artifact['artifact_id'])
    return SimulationConfig(key, scenario.metric, scenario.proposed_baseline, scenario.interventions, seed=seed)


def simulation_status(config: SimulationConfig) -> str:
    if config.calibration_id:
        return "Archive-calibrated synthetic CTR pairs · approximate effect calibration; not historical experiments or known real effects."
    return "Development simulation · Real binomial sampling, hypothetical assumptions. These experiments are not calibrated to Upworthy or to real product outcomes."
