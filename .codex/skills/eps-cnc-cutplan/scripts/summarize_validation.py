from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: summarize_validation.py <validation_report.json>")
        return 2
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    checks = data.get("checks", [])
    errors = [item for item in checks if item.get("level") == "error" or item.get("status") == "fail"]
    warnings = [item for item in checks if item.get("level") == "warning"]
    print(f"checks={len(checks)} errors={len(errors)} warnings={len(warnings)}")
    for item in errors[:20]:
        print(f"ERROR {item.get('code', item.get('name', 'check'))}: {item.get('message', item)}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
