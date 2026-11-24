"""One-command offline TP40 review plus optional original evidence verification."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from epscad.loader import load_yaml
from epscad.geometry.roof_review import build_reference
from epscad.geometry.evidence_zip import inspect_zip
from epscad.exporters.roof_3d import write_roof_assets
from epscad.visual.review_drawing import write_section

CYCLES_VIEWS = (
    ("24_eps_core.glb", "30_eps_perspective_cycles.png", "perspective"),
    ("23_assembly_reference.glb", "31_section_front_cycles.png", "section_front"),
    ("23_assembly_reference.glb", "32_microgroove_detail_cycles.png", "microgroove_detail"),
    ("23_assembly_reference.glb", "33_assembly_cycles.png", "assembly"),
    ("23_assembly_reference.glb", "34_exploded_cycles.png", "exploded"),
    ("24_eps_core.glb", "35_texture_closeup_cycles.png", "texture_closeup"),
)


def find_blender(spec):
    if not spec:
        return None
    if spec != "auto":
        return spec
    found = shutil.which("blender")
    if not found and sys.platform == "win32":
        roots = sorted(Path("C:/Program Files/Blender Foundation").glob("Blender */blender.exe"), reverse=True)
        found = str(roots[0]) if roots else None
    return found


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, default=ROOT / "outputs" / "tp40_base_lisa_review")
    p.add_argument("--length", type=float, default=1000)
    p.add_argument("--thickness", type=float, default=31)
    p.add_argument("--gauge", type=float, default=0.43)
    p.add_argument("--evidence", type=Path, help="Optional original factory ZIP, kept outside Git")
    p.add_argument("--blender", default=None, help="Optional Blender executable or 'auto'")
    p.add_argument("--samples", type=int, default=64, help="Cycles samples when Blender is enabled (1..512)")
    a = p.parse_args()
    out = a.output.resolve()
    if out.exists():
        p.error("Output must be a new directory; preserve earlier review")
    evidence = a.evidence
    default_evidence = ROOT / "private_evidence" / "MACROS_CNC_V.zip"
    if evidence is None and default_evidence.is_file():
        evidence = default_evidence
    spec = load_yaml(ROOT / "catalogs/roof_profiles/tp40_980_microgroove_review.yaml")
    params = dict(spec["geometry"])
    params["min_thickness_mm"] = a.thickness
    roof, report = build_reference(params, length=a.length, gauge=a.gauge)
    report["reference_id"] = spec["id"]
    report["geometry"] = params
    report["source_kind"] = "normalized_reference"
    if evidence is not None:
        if not evidence.is_file():
            p.error("Evidence ZIP not found")
        # Compare at the baseline thickness even if the requested review changes thickness.
        baseline, _ = build_reference(spec["geometry"], length=a.length, gauge=a.gauge)
        report["historical_evidence"] = inspect_zip(
            evidence, width=report["width_mm"], length=a.length, gauge=a.gauge, expected_roof=baseline
        )
        report["source_kind"] = "normalized_reference_verified_against_local_archive"
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".eps-review-", dir=out.parent) as tmp:
        stage = Path(tmp) / "review"
        stage.mkdir()
        write_roof_assets(roof, stage, "draft")
        write_section(roof, report, stage / "29_section_review.png")
        blender = find_blender(a.blender)
        report["render_backend"] = "CPU_illustrative"
        report["quality_renders"] = []
        if blender:
            for model, name, view in CYCLES_VIEWS:
                subprocess.run(
                    [
                        sys.executable,
                        str(ROOT / "scripts/render_quality.py"),
                        "--input",
                        str(stage / model),
                        "--output",
                        str(stage / name),
                        "--blender",
                        blender,
                        "--samples",
                        str(a.samples),
                        "--view",
                        view,
                    ],
                    check=True,
                )
                report["quality_renders"].append({"view": view, "source": model, "file": name})
            report["render_backend"] = "CPU_and_Cycles_uninspected"
        elif a.blender == "auto":
            report["render_note"] = "Blender not found; CPU preview generated"
        (stage / "review.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        (stage / "LEIA-ME.txt").write_text(
            "REVISAO NOMINAL - NAO PRODUCAO\n"
            "STL mm; GLB m; chapa e comprimento de referencia. Nenhum DXF/TAP. Validar fisicamente antes de fabricar.\n",
            encoding="utf-8",
        )
        inventory = sorted(stage.iterdir())
        if any(f.suffix.lower() in (".dxf", ".tap", ".nc", ".gcode") for f in inventory):
            raise ValueError("Machine file in review")
        hashes = stage / "SHA256SUMS.txt"
        hashes.write_text(
            "".join(f"{hashlib.sha256(f.read_bytes()).hexdigest()}  {f.name}\n" for f in inventory),
            encoding="utf-8",
        )
        archive = stage / "TP40_REVISAO.zip"
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as z:
            for f in inventory + [hashes]:
                z.write(f, f.name)
        with zipfile.ZipFile(archive) as z:
            if z.testzip() is not None or set(z.namelist()) != {f.name for f in inventory + [hashes]}:
                raise ValueError("Review archive failed validation")
            for f in inventory + [hashes]:
                if z.read(f.name) != f.read_bytes():
                    raise ValueError("Review archive content mismatch")
        stage.rename(out)
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
