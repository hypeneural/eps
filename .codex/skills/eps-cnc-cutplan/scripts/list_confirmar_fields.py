from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml


def _walk(value: Any, prefix: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            child = f"{prefix}.{key}" if prefix else str(key)
            found.extend(_walk(item, child))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(_walk(item, f"{prefix}[{index}]"))
    elif value == "confirmar":
        found.append(prefix)
    return found


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: list_confirmar_fields.py <project.yaml>")
        return 2
    path = Path(sys.argv[1])
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    fields = _walk(data)
    if not fields:
        print("confirmar_fields=0")
        return 0
    print(f"confirmar_fields={len(fields)}")
    for field in fields:
        print(field)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
