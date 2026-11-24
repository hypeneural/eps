"""Unified catalog-driven nominal model entry point.

Routes each catalog YAML in catalogs/roof_profiles/ to its exact mathematical
generator so agents never confuse the historical microgroove profile
(tp40_980_microgroove_review) with simplified trapezoidal catalog references
(tp40_980_sks, tp40_1020_isoeste). Never approves production or emits DXF.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG_DIR = ROOT / "catalogs" / "roof_profiles"
sys.path.insert(0, str(ROOT / "src"))
from epscad.loader import load_yaml


def discover_catalogs():
    catalogs = {}
    for path in sorted(CATALOG_DIR.glob("*.yaml")):
        data = load_yaml(path)
        cid = data.get("id") or path.stem
        if "geometry" in data and "profile" not in data:
            kind = "microgroove_review"
            geom = data["geometry"]
            width = geom["pitch_mm"] * geom["periods"]
            default_thickness = geom["min_thickness_mm"]
            default_gauge = (data.get("visual_assumptions") or {}).get("metal_gauge_mm", 0.43)
        elif "profile" in data and "geometry" not in data:
            kind = "trapezoidal_simplified"
            prof = data["profile"]
            width = prof["panel_width_mm"]
            default_thickness = prof["min_thickness_mm"]
            default_gauge = data.get("metal_thickness_mm", 0.43)
        else:
            raise ValueError(f"Ambiguous catalog schema: {path.name}")
        catalogs[cid] = {
            "id": cid,
            "path": path,
            "kind": kind,
            "width_mm": width,
            "default_thickness_mm": default_thickness,
            "default_gauge_mm": default_gauge,
            "status": data.get("status", "reference_only"),
            "limitations": data.get("limitations", ""),
        }
    return catalogs


def main():
    catalogs = discover_catalogs()
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("catalog_id", nargs="?", help="Catalog ID from catalogs/roof_profiles/ (use --list to inspect)")
    p.add_argument("--list", action="store_true", help="List available catalog profiles as JSON and exit")
    p.add_argument("--output", type=Path, default=None, help="Output directory")
    p.add_argument("--length", type=float, default=1000, help="Visual extrusion length in mm (default: 1000)")
    p.add_argument("--thickness", type=float, default=None, help="Minimum EPS thickness in mm (default from catalog)")
    p.add_argument("--gauge", type=float, default=None, help="Reference metal gauge in mm (microgroove_review only)")
    p.add_argument("--evidence", type=Path, default=None, help="Optional private evidence ZIP (microgroove_review only)")
    p.add_argument("--blender", default=None, help="Optional Blender executable or 'auto' (microgroove_review)")
    p.add_argument("--samples", type=int, default=64, help="Cycles samples when Blender is enabled")
    a = p.parse_args()

    if a.list:
        summary = [
            {k: str(v) if isinstance(v, Path) else v for k, v in item.items()}
            for item in catalogs.values()
        ]
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 0

    if not a.catalog_id:
        p.error("Provide a catalog_id or pass --list")
    if a.catalog_id not in catalogs:
        p.error(f"Unknown catalog_id {a.catalog_id!r}; available: {', '.join(sorted(catalogs))}")

    entry = catalogs[a.catalog_id]
    thickness = a.thickness if a.thickness is not None else entry["default_thickness_mm"]

    if entry["kind"] == "microgroove_review":
        cmd = [
            sys.executable,
            str(ROOT / "scripts/prepare_tp40.py"),
            "--length",
            str(a.length),
            "--thickness",
            str(thickness),
            "--gauge",
            str(a.gauge if a.gauge is not None else entry["default_gauge_mm"]),
            "--samples",
            str(a.samples),
        ]
        if a.output is not None:
            cmd.extend(["--output", str(a.output)])
        if a.evidence is not None:
            cmd.extend(["--evidence", str(a.evidence)])
        if a.blender is not None:
            cmd.extend(["--blender", a.blender])
        subprocess.run(cmd, cwd=ROOT, check=True)
        return 0

    cmd = [
        sys.executable,
        str(ROOT / "scripts/new_tp40.py"),
        a.catalog_id,
        "--length",
        str(a.length),
        "--thickness",
        str(thickness),
    ]
    if a.output is not None:
        cmd.extend(["--output", str(a.output)])
    subprocess.run(cmd, cwd=ROOT, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
