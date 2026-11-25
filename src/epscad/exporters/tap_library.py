"""Controlled local staging importer for historical factory TAP programs.

Preserves original bytes and SHA-256 hashes, parses modal trajectories, generates offline
simulation previews, classifies coarse historical families without inferring nominal specs from
filenames, and requires explicit per-item human confirmation before any future portal publication.
Never publishes automatically.
"""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import unicodedata
import zipfile

from epscad.exporters.tap_simulator import parse_tap_modal, render_tap_simulation


def _slug(name):
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii").lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:48] or "programa"


def classify_family(filename, parsed):
    """Conservative structural classification; never invents physical dimensions."""
    low = unicodedata.normalize("NFKD", filename).encode("ascii", "ignore").decode("ascii").lower()
    m = parsed["metrics"]
    if m["arc_count"] > 0:
        return "telha_ondulada_arco"
    if "base lisa" in low:
        return "telha_base_lisa_retornos"
    if "bidirecional" in low or "bideirecional" in low:
        return "laje_bidirecional"
    if "modelada" in low:
        return "laje_modelada"
    if any(k in low for k in ("tp40", "tp 40", "tr40", "brastelha")):
        return "telha_tp40_trapezoidal"
    if any(k in low for k in ("rt 25", "rt25", "tp25", "tr25", "rt 35", "tp35", "tp.35", "telha")):
        return "telha_trapezoidal_outra"
    if any(k in low for k in ("linha reta", "esquadro")) or m["segment_count"] <= 4:
        return "esquadro_ou_linha"
    return "outro"


def stage_historical_archive(archive_path, output_dir, *, default_ij_mode="incremental"):
    """Import unique historical TAPs into a local review staging folder (never public)."""
    archive_path = Path(archive_path).resolve()
    output_dir = Path(output_dir).resolve()
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError("Choose a fresh empty staging output directory")
    preserved_dir = output_dir / "preserved_taps"
    previews_dir = output_dir / "previews"
    preserved_dir.mkdir(parents=True, exist_ok=True)
    previews_dir.mkdir(parents=True, exist_ok=True)

    seen_sha = {}
    records = []
    with zipfile.ZipFile(archive_path) as z:
        entries = [i for i in z.infolist() if not i.is_dir()]
        if len(entries) > 1000 or sum(i.file_size for i in entries) > 20_000_000:
            raise ValueError("Archive exceeds controlled import limits")
        for info in sorted(entries, key=lambda x: x.filename.lower()):
            raw_name = PurePosixPath(info.filename.replace("\\", "/")).name
            if not raw_name.lower().endswith(".tap"):
                continue
            if info.file_size > 2_000_000:
                raise ValueError("Oversize TAP member: " + raw_name)
            data = z.read(info)
            digest = hashlib.sha256(data).hexdigest()
            if digest in seen_sha:
                seen_sha[digest]["duplicate_paths"].append(info.filename)
                continue

            parsed = parse_tap_modal(data, default_ij_mode=default_ij_mode)
            stem = _slug(Path(raw_name).stem)
            item_id = f"hist-{stem}-{digest[:6]}"
            preserved_name = f"{item_id}.tap"
            preview_name = f"{item_id}_sim.png"

            # Preserve exact original bytes unmodified
            (preserved_dir / preserved_name).write_bytes(data)
            render_tap_simulation(parsed, previews_dir / preview_name, title=f"Historico: {raw_name}")

            rec = {
                "staging_id": item_id,
                "origin": "historical_factory_archive",
                "historical_filename": raw_name,
                "archive_member_path": info.filename,
                "duplicate_paths": [],
                "preserved_file": f"preserved_taps/{preserved_name}",
                "preview_image": f"previews/{preview_name}",
                "sha256": digest,
                "byte_size": len(data),
                "family_inferred_structural": classify_family(raw_name, parsed),
                "observed_tap_bbox_mm": parsed["metrics"]["bbox_mm"],
                "observed_metrics": {k: v for k, v in parsed["metrics"].items() if k != "bbox_mm"},
                "observed_modal": parsed["modal"],
                "audit_warnings": parsed["warnings"],
                # Explicit human sign-off fields (NEVER auto-filled or inferred from filename)
                "verified_part_name": None,
                "verified_category": None,
                "verified_nominal_dimensions_mm": None,
                "verified_stock_mm": None,
                "specs_verified_physically": False,
                "operator_confirmed": False,
                "public_authorized": False,
                "production_approved": False,
                "revision": None,
                "reviewer_notes": "",
            }
            seen_sha[digest] = rec
            records.append(rec)

    if not records:
        raise ValueError("No TAP files found in archive")

    manifest = {
        "purpose": "local_historical_staging_only",
        "archive_name": archive_path.name,
        "archive_sha256": hashlib.sha256(archive_path.read_bytes()).hexdigest(),
        "total_unique_programs": len(records),
        "family_counts": {fam: sum(1 for r in records if r["family_inferred_structural"] == fam) for fam in sorted({r["family_inferred_structural"] for r in records})},
        "policy": "Original bytes preserved unmodified. Never infer nominal dimensions from filenames. Every item requires individual human verification and explicit disclosure authorization before any portal publication.",
        "programs": records,
    }
    (output_dir / "historical_catalog_draft.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_dir / "SIGN_OFF_REQUIRED.txt").write_text(
        "STAGING LOCAL DE ARQUIVOS HISTORICOS — NAO PUBLICAR AUTOMATICAMENTE.\n"
        "Conferir cada preview em previews/, confirmar medidas fisicas reais, associar familia/revisao\n"
        "e obter autorizacao explicita de divulgacao e homologacao antes de cadastrar no portal.\n",
        encoding="utf-8",
    )
    return manifest
