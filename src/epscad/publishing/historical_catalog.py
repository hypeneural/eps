"""Private read-only catalog of historical TAPs. Preserve bytes, never approve execution."""
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import re
import zipfile
from epscad.exporters.tap_simulator import parse_tap_modal, render_tap_simulation

def inventory(source):
    source = Path(source)
    groups = {}
    total = 0
    def add(name, data):
        nonlocal total
        total += 1
        if total > 5000 or len(data) > 2_000_000:
            raise ValueError("Historical inventory exceeds limits")
        h = hashlib.sha256(data).hexdigest()
        row = groups.setdefault(h, {"sha256": h, "data": data, "aliases": []})
        row["aliases"].append(name.replace("\\", "/"))
    if source.is_dir():
        for p in sorted(source.rglob("*")):
            if p.is_file() and not p.is_symlink() and p.suffix.lower() == ".tap":
                if p.stat().st_size > 2_000_000:
                    raise ValueError("Oversized historical TAP")
                add(p.relative_to(source).as_posix(), p.read_bytes())
    else:
        with zipfile.ZipFile(source) as z:
            for info in z.infolist():
                if not info.is_dir() and info.filename.lower().endswith(".tap"):
                    if info.file_size > 2_000_000:
                        raise ValueError("Oversized historical TAP")
                    add(info.filename, z.read(info))
    if not groups:
        raise ValueError("No historical TAPs found")
    return total, groups

def project_history(data, slug, name, sha):
    parsed = parse_tap_modal(data)
    if parsed["modal"]["units"] != "mm" or parsed["modal"]["distance_mode"] not in (None, "G90"):
        raise ValueError("Unsupported historical coordinate mode")
    if any(s["kind"] == "RAPID" for s in parsed["segments"]):
        raise ValueError("Rapid motion needs a dedicated visual event model")
    parts, distance = [], 0.0
    for s in parsed["segments"]:
        for a, b in zip(s["points"], s["points"][1:]):
            length = math.dist(a, b)
            if not math.isfinite(length):
                raise ValueError("Invalid historical trajectory")
            if length <= 1e-9:
                continue
            distance += length
            parts.append({"block": s["block"], "start": a, "end": b,
                          "kind": s["kind"], "end_distance_mm": distance})
    if not parts:
        raise ValueError("Empty historical trajectory")
    return parsed, {"schema": 1, "model": slug, "name": name, "tap_sha256": sha,
                    "units": "mm", "distance_mm": distance, "bbox": parsed["metrics"]["bbox_mm"],
                    "segments": parts, "regions": {"demonstrable": False, "physical_separation_confirmed": False},
                    "historical": True, "warnings": parsed["warnings"],
                    "wire_visualization": "schematic_parallel_pair", "physical_spacing_mm": None,
                    "production_approved": False, "execution_authorized": False}

def build_historical_catalog(source, stage, env, logo_name):
    total, groups = inventory(source)
    rows = []
    for sha, entry in sorted(groups.items()):
        aliases = sorted(set(entry["aliases"]), key=str.casefold)
        name = Path(aliases[0]).stem
        lower = " ".join(aliases).casefold()
        category = ("Auxiliares" if "esquadro" in lower or "linha reta" in lower else
                    "Arquivados" if "nao utilizados" in lower or "não utilizados" in lower else
                    "Telhas" if re.search(r"telha|tp\s?\d|tr\s?\d|rt\s?\d", lower) else "Outros")
        slug = "historico-" + sha
        folder = stage / slug
        folder.mkdir()
        filename = slug + "-NAO-EXECUTAR.tap"
        (folder / filename).write_bytes(entry["data"])
        row = {"id": slug, "display_name": name, "category": category, "filename": filename,
               "file": slug+"/"+filename, "sha256": sha, "bytes": len(entry["data"]),
               "aliases": aliases, "copies": len(entry["aliases"]), "historical": True,
               "production_approved": False, "execution_authorized": False}
        try:
            parsed, visual = project_history(entry["data"], slug, name, sha)
            render_tap_simulation(parsed, folder/"simulacao.png", title=name)
            (folder/"simulacao.json").write_text(json.dumps(visual, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
            bb = visual["bbox"]
            row.update(preview=slug+"/simulacao.png", animation=slug+"/simulacao.html",
                       animation_data=slug+"/simulacao.json", width_mm=bb["width"], height_mm=bb["height"],
                       total_length_mm=round(visual["distance_mm"], 1), segment_count=len(visual["segments"]),
                       arc_count=parsed["metrics"]["arc_count"], warnings=visual["warnings"])
            (folder/"simulacao.html").write_text(env.get_template("cut_animation.html").render(m=row, logo_name=logo_name), encoding="utf-8")
        except (ValueError, UnicodeError, ArithmeticError) as exc:
            for filename_tmp in ("simulacao.png", "simulacao.json", "simulacao.html"):
                (folder/filename_tmp).unlink(missing_ok=True)
            row["visual_error"] = str(exc)[:200]
        rows.append(row)
    rows.sort(key=lambda m: (m["category"], m["display_name"].casefold(), m["sha256"]))
    result = {"source_files": total, "unique_files": len(rows), "duplicates": total-len(rows),
              "animations": sum(bool(m.get("animation")) for m in rows), "models": rows}
    (stage/"historicos.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    (stage/"historicos.html").write_text(env.get_template("historical_catalog.html").render(history=result, logo_name=logo_name), encoding="utf-8")
    return result
