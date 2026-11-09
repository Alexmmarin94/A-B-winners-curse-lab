"""Inventory local archive schemas without using outcomes for model development."""

import argparse
import csv
import hashlib
import json
from pathlib import Path


REQUIRED = {"clickability_test_id", "created_at", "impressions", "clicks"}
RISK_FIELDS = {"problem", "randomization_imbalace_risk", "randomization_imbalance_risk"}


def inspect_file(path: Path) -> dict:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    with path.open(newline="", encoding="utf-8-sig") as source:
        reader = csv.reader(source)
        columns = next(reader)
        row_count = sum(1 for _ in reader)
    return {
        "filename": path.name,
        "bytes": path.stat().st_size,
        "sha256": digest.hexdigest(),
        "rows": row_count,
        "columns": columns,
        "missing_required_columns": sorted(REQUIRED - set(columns)),
        "randomization_risk_columns": sorted(RISK_FIELDS & set(columns)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=Path("raw_data"))
    parser.add_argument("--output", type=Path, default=Path("research/archive_inventory.json"))
    args = parser.parse_args()
    paths = sorted(args.raw_dir.glob("*.csv"))
    if not paths:
        parser.error(f"No CSV files found in {args.raw_dir}")
    report = {
        "schema_version": 1,
        "status": "Inventory only; not a data-quality or calibration report.",
        "files": [inspect_file(path) for path in paths],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Inventoried {len(paths)} files; report: {args.output}")
    if any(file["missing_required_columns"] for file in report["files"]):
        raise SystemExit("Required columns are missing; see the inventory report.")


if __name__ == "__main__":
    main()
