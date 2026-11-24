from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml


def _walk_confirmar(value: Any, prefix: str = "") -> list[str]:
    if isinstance(value, dict):
        out: list[str] = []
        for key, item in value.items():
            out.extend(_walk_confirmar(item, f"{prefix}.{key}" if prefix else str(key)))
        return out
    if isinstance(value, list):
        out = []
        for index, item in enumerate(value):
            out.extend(_walk_confirmar(item, f"{prefix}[{index}]"))
        return out
    return [prefix] if value == "confirmar" else []


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: explain_failed_gate.py <project-or-profile.yaml>")
        return 2
    data = yaml.safe_load(Path(sys.argv[1]).read_text(encoding="utf-8"))
    reasons: list[str] = []
    confirmar = _walk_confirmar(data)
    if confirmar:
        reasons.append(f"{len(confirmar)} campo(s) confirmar bloqueiam producao")
    if isinstance(data, dict) and data.get("profile_locked") is False:
        reasons.append("profile_locked=false bloqueia producao")
    source = data.get("project", {}).get("source", {}) if isinstance(data, dict) else {}
    if source.get("kind") == "image_reference" and not (source.get("scale_confirmed") and source.get("dimensions_confirmed")):
        reasons.append("imagem sem escala/dimensoes confirmadas bloqueia producao")
    gcode = data.get("outputs", {}).get("gcode", {}) if isinstance(data, dict) else {}
    if gcode.get("enabled") is True:
        reasons.append("gcode.enabled=true exige fluxo experimental, golden samples e dry-run")
    if not reasons:
        print("no_obvious_gate_failure")
        return 0
    for reason in reasons:
        print(reason)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
