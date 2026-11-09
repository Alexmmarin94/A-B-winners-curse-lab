"""Export observable experiments from a versioned scenario; never exports hidden truth."""

import argparse
from dataclasses import asdict
import json
from pathlib import Path

from app.scenarios import SCENARIO_BY_KEY
from app.configuration import make_config, simulation_status
from src.simulation.engine import SimulationConfig, generate_observed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=SCENARIO_BY_KEY, default="retention")
    parser.add_argument("--seed", type=int, default=20261108)
    parser.add_argument("--config", type=Path, help="Replay a configuration downloaded from the UI.")
    parser.add_argument("--output", type=Path, default=Path(".local/portfolio.json"))
    args = parser.parse_args()
    if args.config:
        data = json.loads(args.config.read_text(encoding="utf-8"))
        data["interventions"] = tuple(data["interventions"])
        config = SimulationConfig(**data)
    else:
        config = make_config(args.scenario, args.seed)
    result = {
        "status": simulation_status(config),
        "config": asdict(config),
        "fingerprint": config.fingerprint,
        "units": "Probability differences; multiply by 100 for percentage points.",
        "observed": [asdict(item) for item in generate_observed(config)],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Exported {config.size} observed experiments to {args.output}; portfolio {config.fingerprint}.")


if __name__ == "__main__":
    main()
