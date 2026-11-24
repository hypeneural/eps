"""Offline modal TAP parser and visual trajectory simulator (read-only; never executes CNC)."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from epscad.exporters.tap_simulator import parse_tap_modal, render_tap_simulation


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("tap", type=Path)
    p.add_argument("--ij-mode", choices=("incremental", "absolute"), default="incremental")
    p.add_argument("--output-png", type=Path)
    p.add_argument("--output-json", type=Path)
    p.add_argument("--title", default="")
    a = p.parse_args()
    parsed = parse_tap_modal(a.tap.read_bytes(), default_ij_mode=a.ij_mode)
    if a.output_png:
        render_tap_simulation(parsed, a.output_png, title=a.title or a.tap.name)
    summary = {k: v for k, v in parsed.items() if k != "segments"}
    if a.output_json:
        a.output_json.parent.mkdir(parents=True, exist_ok=True)
        a.output_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    else:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
