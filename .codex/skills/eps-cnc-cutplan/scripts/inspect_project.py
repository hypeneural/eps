from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import yaml


def _get(data: dict[str, Any], *keys: str, default: Any = "") -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key, default)
    return current


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: inspect_project.py <project.yaml>")
        return 2
    path = Path(sys.argv[1])
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    profile = _get(data, "machine", "profile")
    schema = {
        "scara_hotwire_eps": "schemas/project_hotwire.schema.json",
        "scara_hotwire_teste": "schemas/project_hotwire.schema.json",
    }.get(str(profile), "unknown")
    summary = {
        "project_id": _get(data, "project", "id"),
        "status": _get(data, "project", "status"),
        "source_kind": _get(data, "project", "source", "kind"),
        "machine_profile": profile,
        "process_type": _get(data, "machine", "process_type"),
        "schema": schema,
        "gcode_enabled": _get(data, "outputs", "gcode", "enabled", default=None),
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
