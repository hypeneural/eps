from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from epscad.build import build_job  # noqa: E402
from epscad.loader import load_yaml  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate an EPS CNC project YAML.")
    parser.add_argument("project", help="Path to project YAML.")
    parser.add_argument("--json", action="store_true", help="Print full validation JSON.")
    args = parser.parse_args()

    spec = load_yaml(args.project)
    job = build_job(spec)
    payload = {
        "project_id": job.project_id,
        "machine_profile": job.machine_profile,
        "process_type": job.process_type,
        "production_status": job.production_status,
        "bbox": job.bbox,
        "has_errors": job.has_errors,
        "messages": [vars(item) for item in job.validation],
    }
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(f"project={job.project_id} profile={job.machine_profile} status={job.production_status} errors={job.has_errors}")
        for item in job.validation:
            print(f"{item.level.upper()} {item.code} {item.path}: {item.message}")
    return 1 if job.has_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
