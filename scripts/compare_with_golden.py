from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Placeholder for golden sample comparison.")
    parser.add_argument("sample_dir")
    args = parser.parse_args()
    sample = Path(args.sample_dir)
    if not sample.exists():
        print(f"golden sample directory not found: {sample}", file=sys.stderr)
        return 1
    required = ["exportado.dxf", "medida_real.json"]
    missing = [name for name in required if not (sample / name).exists()]
    if missing:
        print(f"missing golden sample files: {', '.join(missing)}", file=sys.stderr)
        return 1
    print("golden_sample_present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
