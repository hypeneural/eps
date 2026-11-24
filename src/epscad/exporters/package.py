from __future__ import annotations

import hashlib
import json
import tempfile
import zipfile
from pathlib import Path

import yaml

from epscad.exporters.dxf_r12 import write_dxf_r12
from epscad.exporters.pdf_job import write_pdf_job
from epscad.exporters.png_preview import write_preview_png
from epscad.schema import CutJobResult
from epscad.validators.common import DXF_STATUSES
GENERATED_FILENAMES = {
    "00_README_OPERADOR.txt",
    "01_preview.svg",
    "01_preview.png",
    "02_ordem_corte_eps.pdf",
    "02_ordem_corte_eps.render.png",
    "03_cutpaths_r12.dxf",
    "04_cutpaths_2007.dxf",
    "05_project.locked.yaml",
    "06_manifest.json",
    "08_cam_import_notes.txt",
    "09_freecad_preview.FCStd",
    "10_validation_report.json",
    "11_hashes.sha256",
    "12_package_for_machine.zip",
    "20_eps_core_mm.stl",
    "21_eps_complement_mm.stl",
    "22_metal_reference_mm.stl",
    "23_assembly_reference.glb",
    "24_eps_core.glb",
    "25_eps_material.png",
    "26_render_eps.png",
    "27_render_assembly.png",
    "28_eps_normal.png",
    "29_section_review.png",
    "30_eps_perspective_cycles.png",
    "31_section_front_cycles.png",
    "33_assembly_cycles.png",
    "34_exploded_cycles.png",
    "35_texture_closeup_cycles.png",
}

CATALOG_CYCLES_VIEWS = (
    ("cycles_perspective", "24_eps_core.glb", "30_eps_perspective_cycles.png", "perspective"),
    ("cycles_section_front", "23_assembly_reference.glb", "31_section_front_cycles.png", "section_front"),
    ("cycles_assembly", "23_assembly_reference.glb", "33_assembly_cycles.png", "assembly"),
    ("cycles_exploded", "23_assembly_reference.glb", "34_exploded_cycles.png", "exploded"),
    ("cycles_texture", "24_eps_core.glb", "35_texture_closeup_cycles.png", "texture_closeup"),
)


def _find_blender(spec: str | None) -> str | None:
    if not spec:
        return None
    if spec != "auto":
        return spec
    import shutil, sys
    found = shutil.which("blender")
    if not found and sys.platform == "win32":
        roots = sorted(Path("C:/Program Files/Blender Foundation").glob("Blender */blender.exe"), reverse=True)
        found = str(roots[0]) if roots else None
    return found


def write_outputs(job: CutJobResult, spec: dict, output_dir: str | Path, *, blender: str | None = None, samples: int = 64) -> dict[str, str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    _clear_known_outputs(out)
    with tempfile.TemporaryDirectory(prefix='.eps-staging-', dir=out) as tmp:
        files = _write_staged(job, spec, Path(tmp), blender=blender, samples=samples)
        from epscad.exporters.integrity import verify_zip
        verify_zip(tmp)
        for key, value in files.items():
            source = Path(value)
            source.replace(out / source.name)
        return {key: str(out / Path(value).name) for key, value in files.items()}


def _write_staged(job, spec, out, *, blender: str | None = None, samples: int = 64):
    files: dict[str, str] = {}
    project_path = out / "05_project.locked.yaml"
    project_path.write_text(yaml.safe_dump(spec, sort_keys=False, allow_unicode=False), encoding="utf-8")
    files["project"] = str(project_path)

    preview_path = out / "01_preview.svg"
    preview_path.write_text(_svg(job), encoding="utf-8")
    files["svg_preview"] = str(preview_path)

    png_path = out / "01_preview.png"
    write_preview_png(job, png_path)
    files["png_preview"] = str(png_path)

    report_path = out / "10_validation_report.json"
    report_path.write_text(json.dumps(_validation_report(job), indent=2, ensure_ascii=False), encoding="utf-8")
    files["validation_report"] = str(report_path)

    if job.roof_geometry is not None and not job.has_errors:
        from epscad.exporters.roof_3d import write_roof_assets
        files.update(write_roof_assets(job.roof_geometry, out, job.production_status))
        tp40 = job.metadata.get("tp40") or {}
        if tp40:
            from epscad.visual.review_drawing import write_section
            roof = job.roof_geometry
            min_y = min(y for _, y in roof.core.exterior.coords)
            pts = [(round(seg.start.x, 4), round(seg.start.y - min_y, 4)) for p in job.paths for seg in p.segments]
            if job.paths and job.paths[-1].segments:
                end = job.paths[-1].segments[-1].end
                pts.append((round(end.x, 4), round(end.y - min_y, 4)))
            # Shift roof polygons to y>=0 for uniform review drawing
            from shapely.affinity import translate
            from types import SimpleNamespace
            shifted_roof = SimpleNamespace(
                core=translate(roof.core, yoff=-min_y),
                metal=translate(roof.metal, yoff=-min_y),
            )
            sec_report = {
                "width_mm": tp40["panel_width_mm"],
                "height_mm": tp40["core_total_height_mm"],
                "min_thickness_mm": tp40["min_thickness_mm"],
                "area_mm2": round(roof.core.area, 2),
                "extrusion_length_mm_assumed": roof.length_mm,
                "metal_gauge_mm_assumed": (job.metadata.get("roof_3d") or {}).get("metal_thickness_mm", 0.43),
                "geometry": tp40,
                "profile_points_mm": pts,
                "drawing_title": f"{job.project_id.upper()} | SECAO NOMINAL COMERCIAL - REVISAO, NAO CORTE",
                "drawing_footer": "Referencia comercial simplificada em escala XY uniforme. Microdobras, bordas e corte exigem medicao fisica.",
            }
            sec_path = out / "29_section_review.png"
            write_section(shifted_roof, sec_report, sec_path)
            files["section_review"] = str(sec_path)
        blender_exe = _find_blender(blender)
        if blender_exe:
            import subprocess, sys
            render_script = Path(__file__).resolve().parents[3] / "scripts" / "render_quality.py"
            for key, model_file, out_name, view in CATALOG_CYCLES_VIEWS:
                out_png = out / out_name
                subprocess.run(
                    [sys.executable, str(render_script), "--input", str(out / model_file), "--output", str(out_png), "--blender", blender_exe, "--samples", str(samples), "--view", view],
                    check=True,
                )
                files[key] = str(out_png)

    if spec.get("outputs", {}).get("dxf", False) and job.production_status in DXF_STATUSES and not job.has_errors and job.metadata.get("tp40", {}).get("cut_mode") != "core_outline":
        dxf_path = out / "03_cutpaths_r12.dxf"
        write_dxf_r12(job, dxf_path)
        from epscad.exporters.dxf_validator import validate_dxf
        from epscad.exporters.roundtrip import verify_roundtrip
        if not validate_dxf(dxf_path).ok or not verify_roundtrip(job, dxf_path):
            dxf_path.unlink(missing_ok=True)
            raise ValueError("Exported DXF failed validation")
        files["dxf_r12"] = str(dxf_path)

    pdf_path = out / "02_ordem_corte_eps.pdf"
    write_pdf_job(job, spec, pdf_path)
    files["pdf_job"] = str(pdf_path)

    readme_path = out / "00_README_OPERADOR.txt"
    readme_path.write_text(_operator_readme(job), encoding="utf-8")
    files["operator_readme"] = str(readme_path)

    notes_path = out / "08_cam_import_notes.txt"
    notes_path.write_text(_cam_notes(job), encoding="utf-8")
    files["cam_notes"] = str(notes_path)

    manifest_path = out / "06_manifest.json"
    manifest = _manifest(job, files)
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    files["manifest"] = str(manifest_path)

    hashes_path = out / "11_hashes.sha256"
    hashes_path.write_text(_hashes(files), encoding="utf-8")
    files["hashes"] = str(hashes_path)

    zip_path = out / "12_package_for_machine.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in files.values():
            path = Path(file_path)
            archive.write(path, arcname=path.name)
    files["package_zip"] = str(zip_path)
    return files


def _clear_known_outputs(out: Path) -> None:
    for name in GENERATED_FILENAMES:
        path = out / name
        if path.exists() and path.is_file():
            path.unlink()


def _validation_report(job: CutJobResult) -> dict:
    return {
        "project_id": job.project_id,
        "has_errors": job.has_errors,
        "checks": [vars(item) for item in job.validation],
        "bbox": job.bbox,
    }


def _manifest(job: CutJobResult, files: dict[str, str]) -> dict:
    manifest = {
        "unit": job.unit,
        "machine_profile": job.machine_profile,
        "process_type": job.process_type,
        "origin": job.metadata.get("origin", ""),
        "bbox_mm": job.bbox,
        "path_count": len(job.paths),
        "production_status": job.production_status,
        "gcode_enabled": job.metadata.get("gcode_enabled", False),
        "requires_dry_run": True,
        "package_purpose": "production" if job.production_status == "production_released" and not job.has_errors else "review_or_test_only",
        "model_units": {"stl": "mm", "glb": "m"},
        "roof_3d": job.metadata.get("roof_3d"),
        "project_id": job.project_id,
        "profile_source": job.metadata.get("profile_source"),
        "has_errors": job.has_errors,
        "files": {key: Path(value).name for key, value in files.items()},
    }
    if job.process_type == "hotwire_2d":
        hotwire = job.metadata.get("hotwire", {})
        manifest.update(
            {
                "wire_mode": hotwire.get("wire_mode"),
                "wire_count": hotwire.get("wire_count"),
                "effective_kerf_mm": hotwire.get("effective_kerf_mm"),
                "lead_in_mm": hotwire.get("lead_in_mm"),
                "lead_out_mm": hotwire.get("lead_out_mm"),
                "min_segment_mm": hotwire.get("min_segment_mm"),
                "min_radius_mm": hotwire.get("min_radius_mm"),
                "feed_xy_mm_min": hotwire.get("feed_xy_mm_min"),
                "slow_curve_mm_min": hotwire.get("slow_curve_mm_min"),
                "compensation_mode": hotwire.get("compensation_mode"),
            }
        )
    if job.metadata.get("tp40"):
        manifest["template"] = job.metadata.get("template")
        manifest["tp40"] = job.metadata["tp40"]
    return manifest


def _svg(job: CutJobResult) -> str:
    bbox = job.view_bbox
    pad = 20
    width = max(bbox["width"] + 2 * pad, 100)
    height = max(bbox["height"] + 2 * pad, 100)
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="{bbox["min_x"] - pad} {-bbox["max_y"] - pad} {width} {height}">',
        '<g transform="scale(1,-1)" fill="none" stroke="#aaaaaa" stroke-width="0.5">',
    ]
    for segment in job.reference_segments:
        lines.append(f'<line x1="{segment.start.x}" y1="{segment.start.y}" x2="{segment.end.x}" y2="{segment.end.y}" />')
    lines.append("</g>")
    lines.append('<g transform="scale(1,-1)" fill="none" stroke="black" stroke-width="1">')
    for path in job.paths:
        for segment in path.segments:
            lines.append(f'<line x1="{segment.start.x}" y1="{segment.start.y}" x2="{segment.end.x}" y2="{segment.end.y}" />')
    lines.append("</g>")
    lines.append(f'<text x="{bbox["min_x"]}" y="{-bbox["max_y"] - 5}" font-size="10">status: {job.production_status}</text>')
    lines.append("</svg>")
    return "\n".join(lines)


def _operator_readme(job: CutJobResult) -> str:
    return (
        f"Projeto: {job.project_id}\n"
        f"Perfil: {job.machine_profile}\n"
        f"Processo: {job.process_type}\n"
        f"Status: {job.production_status}\n"
        + ("PRODUCAO: conferir autorizacao e dry-run.\n" if job.production_status == "production_released" and not job.has_errors else "NAO LIBERADO PARA PRODUCAO. Conferencia/teste apenas.\n")
        + "STL/GLB/PNG: apenas visualizacao; LazyCam recebe somente o DXF validado.\n"
        +
        "Conferir unidade em mm, origem, escala, bbox e dry-run antes de cortar.\n"
    )


def _cam_notes(job: CutJobResult) -> str:
    return "SCARA/fio quente: conferir escala no LazyCam, origem, perda do fio, velocidade e dry-run no Mach3/EPS.\n"


def _hashes(files: dict[str, str]) -> str:
    rows = []
    for key, file_path in sorted(files.items()):
        path = Path(file_path)
        if not path.exists() or path.name.endswith(".sha256"):
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        rows.append(f"{digest}  {path.name}")
    return "\n".join(rows) + "\n"
