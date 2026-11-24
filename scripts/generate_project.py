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
from epscad.exporters import write_outputs  # noqa: E402
from epscad.loader import load_yaml  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate EPS CNC project package.")
    parser.add_argument("project", help="Path to project YAML.")
    parser.add_argument("--output", default=None, help="Output directory.")
    args = parser.parse_args()

    spec = load_yaml(args.project)
    job = build_job(spec)
    import re
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", job.project_id):
        parser.error("Invalid project id")
    output_dir = Path(args.output) if args.output else ROOT / "outputs" / job.project_id
    files = write_outputs(job, spec, output_dir)
    print(json.dumps({"project": job.project_id, "has_errors": job.has_errors, "output": str(output_dir), "files": files}, indent=2, ensure_ascii=False))
    return 1 if job.has_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
