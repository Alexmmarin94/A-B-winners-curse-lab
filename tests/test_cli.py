"""A saved configuration must replay the same observable portfolio through the CLI."""

from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import sys

from app.scenarios import SCENARIOS
from src.simulation.engine import SimulationConfig, generate_observed


def test_configuration_replay(tmp_path):
    scenario = SCENARIOS[0]
    config = SimulationConfig(scenario.key, scenario.metric, scenario.proposed_baseline,
                              scenario.interventions, seed=77)
    source = tmp_path / "config.json"
    target = tmp_path / "observed.json"
    source.write_text(json.dumps(asdict(config)), encoding="utf-8")
    subprocess.run([sys.executable, "-m", "scripts.generate_portfolio", "--config", str(source),
                    "--output", str(target)], check=True, capture_output=True,
                   cwd=Path(__file__).resolve().parents[1])
    payload = json.loads(target.read_text())
    assert payload["observed"] == [asdict(item) for item in generate_observed(config)]
    assert payload["fingerprint"] == config.fingerprint
    assert "truth" not in payload
    assert "treatment_probability" not in target.read_text()
