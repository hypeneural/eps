from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from epscad.exporters.dxf_validator import validate_dxf  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate generated DXF against EPS CNC contract.")
    parser.add_argument("dxf", help="Path to DXF file.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = validate_dxf(args.dxf)
    payload = {
        "path": result.path,
        "ok": result.ok,
        "entity_count": result.entity_count,
        "forbidden_entities": result.forbidden_entities,
        "unknown_entities": result.unknown_entities,
        "structural_errors": result.structural_errors,
        "bbox": result.bbox,
    }
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(f"dxf={result.path} ok={result.ok} entities={result.entity_count}")
        if result.forbidden_entities:
            print(f"forbidden={', '.join(result.forbidden_entities)}")
        if result.unknown_entities:
            print(f"unknown={', '.join(result.unknown_entities)}")
        print(f"bbox={result.bbox}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
