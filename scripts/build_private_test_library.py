"""Build a strictly local, offline HTML test library uniting factory historical TAPs,
planned CAM candidates (TP40 + Lajotas) and the consolidated physical homologation sheet.

NEVER deploy this directory to the public portal (https://eps.etijucas.com.br).
"""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
import shutil
import sys
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from epscad.build import build_job
from epscad.cam.slab_planner import SLAB_CATALOG, build_slab_trial_spec, plan_slab_section
from epscad.exporters.mach3_tap import canonical, ordered_points, sha
from epscad.exporters.tap_simulator import render_tap_simulation
from epscad.loader import load_yaml


def _slab_parsed(plan: dict) -> dict:
    pts = plan["points_mm"]
    segs = [
        {"block": (i + 1) * 5, "kind": "LINE", "start": a, "end": b, "points": [a, b],
         "length_mm": round(((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5, 4), "backtrack_x": False}
        for i, (a, b) in enumerate(zip(pts, pts[1:]))
    ]
    return {
        "sha256": sha(canonical(pts)),
        "metrics": {**plan["metrics"], "arc_count": 0, "rapid_count": 0, "omitted_axis_moves": 0, "grouped_m_blocks": 0, "collinear_overlap_mm": 0.0},
        "modal": {"units": "mm", "plane": "G17", "distance_mode": "G90", "ij_mode": None, "path_control": "CONFIRMAR",
                  "work_offset": "CONFIRMAR", "feed_mode": "G94", "feed_mm_min": "CONFIRMAR", "spindle_s": "CONFIRMAR", "dwells": ["CONFIRMAR"], "m_sequence": [3, 5, 30]},
        "warnings": ["secao_xy_invertida_aguardando_parametros_presenciais"],
        "segments": segs,
    }


def build_private_library(handoff_dir: Path, historical_dir: Path, evidence_json: Path, output_dir: Path) -> dict:
    handoff_dir, historical_dir, evidence_json, output_dir = map(Path, (handoff_dir, historical_dir, evidence_json, output_dir))
    if output_dir.exists():
        raise FileExistsError("Choose a fresh private library directory")
    output_dir.mkdir(parents=True)

    handoff = json.loads((handoff_dir / "RESUMO_5_MODELOS.json").read_text(encoding="utf-8"))
    hist = json.loads((historical_dir / "historical_catalog_draft.json").read_text(encoding="utf-8"))
    ev = json.loads(evidence_json.read_text(encoding="utf-8"))

    # Copy previews locally for self-contained offline viewing
    (output_dir / "previews_cam").mkdir()
    (output_dir / "previews_hist").mkdir()
    (output_dir / "preserved_taps").mkdir()
    (output_dir / "slab_plans").mkdir()

    # Build approvals.TEMPLATE.json for prepare_mach3_batch.py (all trial_authorized=False!)
    approvals_tpl = {}
    cam_rows = []
    for m in handoff["models"]:
        slug = f"{m['portal_id']}-{m['revision']}"
        src_png = handoff_dir / slug / "simulacao_trajetoria.png"
        dst_png = output_dir / "previews_cam" / f"{slug}.png"
        shutil.copy2(src_png, dst_png)
        approvals_tpl[slug] = {
            "trial_authorized": False,
            "path_sha256": m["path_sha256"],
            "project_sha256": m["project_sha256"],
        }
        cam_rows.append({**m, "preview_rel": f"previews_cam/{slug}.png"})


    # Build the 4 slab CAM plans + simulations
    slab_cat = load_yaml(SLAB_CATALOG)
    slab_rows = []
    for vid in sorted(slab_cat["variants"]):
        plan = plan_slab_section(vid)
        spec = build_slab_trial_spec(plan)
        job = build_job(spec)
        if job.has_errors:
            raise ValueError(f"Slab plan invalid: {vid}")
        pts = ordered_points(job)
        png = output_dir / "slab_plans" / f"{vid}_sim.png"
        render_tap_simulation(_slab_parsed(plan), png, title=f"Lajota CAM XY: {vid} (Z={plan['extrusion_length_z_mm']:g} mm)",
                              stock_bbox=(0.0, 0.0, plan["nominal_width_mm"], plan["nominal_height_mm"]))
        slug=vid+"-r01"
        project=output_dir/"slab_plans"/slug/"projeto_trajetoria.yaml"
        project.parent.mkdir()
        project.write_text(yaml.safe_dump(spec,sort_keys=False,allow_unicode=False),encoding="utf-8")
        approvals_tpl[slug]={"trial_authorized":False,"path_sha256":sha(canonical(pts)),"project_sha256":sha(project.read_bytes())}
        slab_rows.append({**plan, **approvals_tpl[slug], "preview_rel": f"slab_plans/{vid}_sim.png"})
    (output_dir/"approvals.TEMPLATE.json").write_text(json.dumps(approvals_tpl,indent=2,ensure_ascii=False),encoding="utf-8")

    # Copy all 34 preserved original TAPs + previews (strictly local!)
    hist_rows = []
    for p in hist["programs"]:
        tap_src = historical_dir / p["preserved_file"]
        tap_dst = output_dir / "preserved_taps" / Path(p["preserved_file"]).name
        shutil.copy2(tap_src, tap_dst)
        prev_src = historical_dir / p["preview_image"]
        prev_dst = output_dir / "previews_hist" / Path(p["preview_image"]).name
        shutil.copy2(prev_src, prev_dst)
        hist_rows.append({
            **p,
            "tap_rel": f"preserved_taps/{tap_dst.name}",
            "preview_rel": f"previews_hist/{prev_dst.name}",
            "is_tp40_base_lisa": p["sha256"] == "a58fa27df80124b33520cc97a42a755f36c3d57443cf85c08f5776bf31e9bcb3",
        })

    # Render clean offline local HTML dashboard
    def esc(x):
        return html.escape(str(x))

    xml_obs = ev["xml_observed"]
    pst_obs = ev["pst_observed"]
    cam_html = "".join(
        f"<div class='card'><img src='{esc(r['preview_rel'])}' alt='{esc(r['name'])}'>"
        f"<div class='body'><span class='badge warn'>CANDIDATO CAM · SEM TAP PUBLICO</span>"
        f"<h3>{esc(r['name'])}</h3>"
        f"<p><strong>{r['nominal_dimensions_mm']['width_mm']:g} × {r['nominal_dimensions_mm']['height_mm']:g} mm</strong> · "
        f"{r['trajectory_metrics']['segment_count']} segs · {r['trajectory_metrics']['total_length_mm']:.1f} mm · -X: {r['trajectory_metrics']['backtrack_x_count']}</p>"
        f"<p class='mono'>path_sha256: {esc(r['path_sha256'][:16])}…<br>project_sha256: {esc(r['project_sha256'][:16])}…</p>"
        f"<p class='note'>Histórico: {esc(r['historical_match'] or 'Nenhum exato')}</p></div></div>"
        for r in cam_rows
    )
    slab_html = "".join(
        f"<div class='card'><img src='{esc(r['preview_rel'])}' alt='{esc(r['variant_id'])}'>"
        f"<div class='body'><span class='badge blue'>LAJOTA EPS · SECAO XY INVERTIDA</span>"
        f"<h3>{esc(r['variant_id'])}</h3>"
        f"<p><strong>XY {r['nominal_width_mm']:g} × {r['nominal_height_mm']:g} mm</strong> · Bloco Z: {r['extrusion_length_z_mm']:g} mm · Rebaixo: {r['assumed_rebate_mm'][0]:g}×{r['assumed_rebate_mm'][1]:g} mm</p>"
        f"<p class='mono'>path_sha256: {esc(r['path_sha256'][:16])}… · {r['metrics']['segment_count']} segs · {r['metrics']['total_length_mm']:.1f} mm</p></div></div>"
        for r in slab_rows
    )
    hist_html = "".join(
        f"<tr class='{'highlight' if r['is_tp40_base_lisa'] else ''}'>"
        f"<td><strong>{esc(r['historical_filename'])}</strong>{' <span class=\"badge ok\">EXATO BASE LISA 1063 B</span>' if r['is_tp40_base_lisa'] else ''}</td>"
        f"<td>{esc(r['family_inferred_structural'])}</td>"
        f"<td>{r['observed_tap_bbox_mm']['width']:.1f} × {r['observed_tap_bbox_mm']['height']:.1f} mm</td>"
        f"<td>{r['observed_metrics']['segment_count']} (arcos: {r['observed_metrics']['arc_count']}, -X: {r['observed_metrics']['backtrack_x_count']})</td>"
        f"<td class='mono'>{esc(r['sha256'][:14])}…</td>"
        f"<td><a href='{esc(r['preview_rel'])}' target='_blank'>Simulação</a> · <a href='{esc(r['tap_rel'])}' download='{esc(r['historical_filename'])}'>TAP Original ({r['byte_size']} B)</a></td></tr>"
        for r in hist_rows
    )

    page = f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Biblioteca Privada de Testes Mach3 CNC_V | Iso Nunes (USO INTERNO)</title>
<style>
body{{font-family:system-ui,-apple-system,sans-serif;background:#f4f6f7;color:#1b2730;margin:0;line-height:1.45}}
header{{background:#1b2730;color:#fff;padding:18px 28px;border-bottom:4px solid #cc240c}}
header small{{color:#ffd27d;font-weight:700;letter-spacing:.04em}}
main{{max-width:1320px;margin:24px auto;padding:0 20px 60px}}
.banner{{background:#fff3cd;border:1px solid #d99b00;padding:14px 18px;border-radius:10px;margin-bottom:22px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(360px,1fr));gap:16px;margin-bottom:28px}}
.card{{background:#fff;border:1px solid #d4dde2;border-radius:10px;overflow:hidden}}
.card img{{width:100%;display:block;border-bottom:1px solid #e6ecef}}
.body{{padding:14px 16px}}
.badge{{display:inline-block;font-size:11px;font-weight:700;padding:3px 8px;border-radius:999px;margin-bottom:6px}}
.badge.warn{{background:#fff3cd;color:#7a4f00}}.badge.blue{{background:#e6f0f7;color:#14496d}}.badge.ok{{background:#dcf5e7;color:#125c39}}
.mono{{font-family:ui-monospace,Consolas,monospace;font-size:12px;color:#41545f}}
.note{{font-size:13px;color:#51656d}}
table{{width:100%;border-collapse:collapse;background:#fff;border:1px solid #d4dde2;font-size:13px}}
th,td{{padding:9px 10px;border-bottom:1px solid #e6ecef;text-align:left}}
th{{background:#edf1f3}}
tr.highlight{{background:#f0faf4}}
.cols{{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:26px}}
.box{{background:#fff;border:1px solid #d4dde2;border-radius:10px;padding:16px}}
@media(max-width:860px){{.cols{{grid-template-columns:1fr}}}}
</style></head><body>
<header><small>AMBIENTE PRIVADO LOCAL · NUNCA PUBLICAR NO PORTAL PUBLICO</small><h1>Iso Nunes — Biblioteca Privada de Testes Mach3 (CNC_V)</h1></header>
<main>
<div class="banner"><strong>AVISO OPERACIONAL:</strong> Os arquivos abaixo são <strong>históricos originais da fábrica</strong> e <strong>candidatos CAM em pré-teste</strong>. Nenhum item desta página está homologado para publicação comercial automática. Teste presencial sempre com energia do fio isolada primeiro.</div>

<h2>1. Ficha Consolidada — Evidência Recuperada vs. Lacunas Físicas Reais</h2>
<div class="cols">
  <div class="box"><h3>Já recuperado documentalmente (não perguntar novamente)</h3>
    <ul>
      <li><strong>Perfil:</strong> <code>{esc(xml_obs['Profile'])}</code> (Windows 7 Pro 32-bit, filtro <code>*.tap</code>)</li>
      <li><strong>CNC_V.xml:</strong> <code>DwellinMilli={esc(xml_obs['DwellinMilli'])}</code> (segundos), <code>SoftLimit={esc(xml_obs['SoftLimit'])}</code>, <code>INIT={esc(xml_obs['INIT'])}</code>, <code>M30SpinOff={esc(xml_obs['M30SpinOff'])}</code>, <code>NoSpindle={esc(xml_obs['NoSpindle'])}</code>, <code>PWM={esc(xml_obs['PWM'])}</code>, <code>SpinCW={esc(xml_obs['SpinCW'])}</code>, <code>SpinDelayCW={esc(xml_obs['SpinDelayCW'])}</code></li>
      <li><strong>Macros:</strong> <code>m3.m1s</code> = <code>{esc(ev['macro_observed']['m3.m1s'])}</code> · <code>m5.m1s</code> = <code>{esc(ev['macro_observed']['m5.m1s'])}</code></li>
      <li><strong>isopor.pst / {ev['unique_taps']} TAPs históricos:</strong> <code>F600</code>, <code>S300</code>, <code>G4 P3</code> (observação documental, não limite autorizado)</li>
    </ul>
  </div>
  <div class="box"><h3>Apenas o que realmente falta confirmar presencialmente</h3>
    <ol>{''.join(f'<li>{esc(x)}</li>' for x in ev['pending_physical'])}</ol>
    <p class="mono">Gerar lote apos confirmar:<br>python scripts/prepare_mach3_batch.py --handoff outputs/private_trial_handoff_5models --slab-library outputs/private_test_library --profile local_scara_snapshot.yaml --contract local_trial_contract.json --approvals approvals.json --output outputs/lote_tap</p>
  </div>
</div>

<h2>2. Cinco Candidatos CAM TP40 ({len(cam_rows)} modelos do portal)</h2>
<div class="grid">{cam_html}</div>

<h2>3. Quatro Referências de Lajotas EPS — Planejamento CAM XY ({len(slab_rows)} modelos)</h2>
<div class="grid">{slab_html}</div>

<h2>4. Biblioteca Privada dos {len(hist_rows)} Programas Originais da Fábrica (MACROS_CNC_V.zip)</h2>
<table><thead><tr><th>Arquivo Original</th><th>Família</th><th>BBox XY</th><th>Segmentos</th><th>SHA-256 (preservado)</th><th>Ações Locais</th></tr></thead>
<tbody>{hist_html}</tbody></table>
</main></body></html>"""
    (output_dir / "index.html").write_text(page, encoding="utf-8")
    summary = {"purpose": "private_local_test_library_only", "public_allowed": False, "cam_tp40_count": len(cam_rows),
               "slab_cam_count": len(slab_rows), "historical_tap_count": len(hist_rows)}
    (output_dir / "library_manifest.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--handoff", type=Path, required=True)
    p.add_argument("--historical", type=Path, required=True)
    p.add_argument("--evidence", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    res = build_private_library(a.handoff, a.historical, a.evidence, a.output)
    print(f"PRIVATE LOCAL TEST LIBRARY READY: {a.output.resolve()} ({res})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
