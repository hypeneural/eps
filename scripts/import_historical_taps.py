"""Controlled local importer for historical factory TAP archives (staging + previews only, never publishes)."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from epscad.exporters.tap_library import stage_historical_archive


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("archive", type=Path)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--ij-mode", choices=("incremental", "absolute"), default="incremental")
    a = p.parse_args()
    manifest = stage_historical_archive(a.archive, a.output, default_ij_mode=a.ij_mode)
    print(f"Staged {manifest['total_unique_programs']} unique historical TAPs in {a.output.resolve()} (all unapproved / local only)")
    print("Families:", manifest["family_counts"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
