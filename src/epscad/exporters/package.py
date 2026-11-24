from __future__ import annotations

import hashlib
import json
import shutil
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
}


def write_outputs(job: CutJobResult, spec: dict, output_dir: str | Path) -> dict[str, str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    _clear_known_outputs(out)
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

    if job.production_status in DXF_STATUSES and not job.has_errors:
        dxf_path = out / "03_cutpaths_r12.dxf"
        write_dxf_r12(job, dxf_path)
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
