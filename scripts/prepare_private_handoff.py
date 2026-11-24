"""Build a strictly local private handoff bundle for supervised Mach3 CNC_V trials.

Never fabricates physical measurements, thermal parameters or human confirmations,
and never places experimental trial files inside the public portal snapshot.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from epscad.build import build_job
from epscad.cam.tp40_planner import (
    PORTAL_MODELS,
    build_trial_project_spec,
    compare_plan_vs_historical,
    plan_portal_model,
    plan_tp40_base_lisa,
)
from epscad.exporters.mach3_tap import canonical, ordered_points, sha
from epscad.exporters.tap_simulator import render_tap_simulation


DOCUMENTED_CNC_V_OBSERVATIONS = {
    "controller_os": "Windows 7 Professional 32-bit (6.1.7601) - observado em backup local",
    "mach3_profile": "CNC_V (filtro *.tap observado no dialogo do controlador)",
    "cnc_v_xml_observations_not_authorized": {
        "INIT": "G80 (InitAllResets=0 -> G90 ausente na inicializacao; nosso pos-processador sempre explicita G90)",
        "DwellinMilli": "0 na copia local (G4 P em segundos; confirmar presencialmente em General Config)",
        "Spindle_IO": "NoSpindle=1, PWM=0, SpinCW=8, SpinDelayCW=1s, M30SpinOff=1 (S300 nao comprova potencia termica)",
        "SoftLimit": "0 na copia local (desativado; confirmar limites fisicos antes de operar)",
    },
    "unconfirmed_parameters_required_for_trial_tap": [
        "work_area.x_max / y_max / z_max reais medidos na SCARA",
        "axes (+X / +Y) e confirmacao presencial da origem (0,0)",
        "hotwire.wire_count, effective_kerf_mm e min_segment_mm <= 2.0 mm (para microdobras da Base lisa)",
        "feed.default_xy_mm_min e feed_mm_min autorizado para teste",
        "heat_s / max_heat_s e mapeamento real de M3/M5/M30 (io_mapping_confirmed, program_end_confirmed)",
        "dwell_unit (seconds vs milliseconds) e dwell_value / max_dwell_seconds confirmados",
        "work_offset (G54..G59) e path_control (G61 vs G64) confirmados",
        "operator_trial_authorized=true e todas as 8 flags de confirmacao presencial",
    ],
}


def _find_historical_tap(evidence_zips: list[Path], filename: str | None) -> bytes | None:
    if not filename:
        return None
    target = filename.casefold()
    for zp in evidence_zips:
        if not zp.is_file():
            continue
        with zipfile.ZipFile(zp) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                if Path(info.filename.replace("\\", "/")).name.casefold() == target:
                    return zf.read(info.filename)
    return None


def _synthetic_parsed_for_simulation(plan: dict) -> dict:
    """Build a non-executable geometry-only dict compatible with render_tap_simulation."""
    pts = plan["points_mm"]
    segs = []
    for idx, (a, b) in enumerate(zip(pts, pts[1:]), start=1):
        length = ((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5
        segs.append({
            "block": idx * 5,
            "kind": "LINE",
            "start": a,
            "end": b,
            "points": [a, b],
            "length_mm": round(length, 4),
            "backtrack_x": b[0] < a[0] - 1e-4,
        })
    m = plan["metrics"]
    return {
        "sha256": sha(canonical(pts)),
        "metrics": {
            **m,
            "arc_count": 0,
            "rapid_count": 0,
            "omitted_axis_moves": 0,
            "grouped_m_blocks": 0,
            "collinear_overlap_mm": 0.0,
        },
        "modal": {
            "units": "mm",
            "plane": "G17",
            "distance_mode": "G90",
            "ij_mode": None,
            "path_control": "CONFIRMAR",
            "work_offset": "CONFIRMAR",
            "feed_mode": "G94",
            "feed_mm_min": "CONFIRMAR",
            "spindle_s": "CONFIRMAR",
            "dwells": ["CONFIRMAR"],
            "m_sequence": [3, 5, 30],
        },
        "warnings": ["aguardando_parametros_presenciais_para_gerar_TAP"],
        "segments": segs,
    }


def build_private_handoff(output: Path, evidence_zips: list[Path]) -> dict:
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError(f"Output directory must be new: {output}")
    output.mkdir(parents=True)

    summary_rows = []
    all_files: list[Path] = []

    for meta in PORTAL_MODELS:
        bundle = plan_portal_model(meta["portal_id"], base_lisa_strategy="continuous_clean")
        plan = bundle["plan"]
        spec = build_trial_project_spec(bundle)
        job = build_job(spec)
        if job.has_errors:
            raise ValueError(f"Planned trial project failed validation for {meta['portal_id']}: {job.validation}")
        pts = ordered_points(job)
        path_hash = sha(canonical(pts))

        hist_bytes = _find_historical_tap(evidence_zips, meta.get("historical_match"))
        comparison = compare_plan_vs_historical(plan, hist_bytes)

        # For TP40 Base lisa 31 mm, also verify 1:1 forensic reconstruction of legacy pocket path
        forensic_exact = None
        if meta["portal_id"] == "tp40-base-lisa" and hist_bytes is not None:
            hist_plan = plan_tp40_base_lisa(min_thickness_mm=31.0, strategy="historical_pocket")
            forensic_exact = compare_plan_vs_historical(hist_plan, hist_bytes)

        mdir = output / f"{meta['portal_id']}-{meta['revision']}"
        mdir.mkdir(parents=True)

        proj_path = mdir / "projeto_trajetoria.yaml"
        proj_path.write_text(yaml.safe_dump(spec, sort_keys=False, allow_unicode=False), encoding="utf-8")

        sim_png = mdir / "simulacao_trajetoria.png"
        stock = plan["recommended_min_stock_mm"]
        render_tap_simulation(
            _synthetic_parsed_for_simulation(plan),
            sim_png,
            title=f"Planejamento CAM: {meta['name']} ({meta['revision'].upper()})",
            stock_bbox=(0.0, 0.0, stock["length_x"], stock["height_y"]),
        )

        report = {
            "purpose": "private_factory_trial_handoff_only",
            "public_catalog_allowed": False,
            "production_approved": False,
            "trial_tap_generated": False,
            "trial_tap_blocked_reason": "Aguardando preenchimento presencial de local_scara_snapshot.TEMPLATE.yaml e local_trial_contract.TEMPLATE.json (nenhum parametro fisico ou confirmacao foi inventado).",
            "portal_id": meta["portal_id"],
            "revision": meta["revision"],
            "name": meta["name"],
            "catalog_id": meta["catalog_id"],
            "family": meta["family"],
            "strategy": plan["strategy"],
            "nominal_dimensions_mm": {
                "width_mm": plan["nominal_width_mm"],
                "height_mm": plan["nominal_height_mm"],
                "min_thickness_mm": plan["min_thickness_mm"],
                "length_ref_mm": meta["length_mm"],
            },
            "recommended_min_stock_mm": stock,
            "path_sha256": path_hash,
            "project_sha256": sha(proj_path.read_bytes()),
            "trajectory_metrics": plan["metrics"],
            "planner_notes": plan["notes"],
            "historical_match": meta.get("historical_match"),
            "historical_match_kind": meta.get("historical_match_kind"),
            "historical_nearest_note": meta.get("historical_nearest_note"),
            "historical_comparison": comparison,
            "historical_pocket_forensic_check": forensic_exact,
            "unconfirmed_parameters": DOCUMENTED_CNC_V_OBSERVATIONS["unconfirmed_parameters_required_for_trial_tap"],
        }
        rep_json = mdir / "relatorio_trajetoria.json"
        rep_json.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

        rep_txt = mdir / "RELATORIO_OPERADOR.txt"
        rep_txt.write_text(
            f"ENTREGA PRIVADA DE TESTE - NAO HOMOLOGADO PARA PRODUCAO\n"
            f"Modelo: {meta['name']} ({meta['portal_id']}-{meta['revision']})\n"
            f"Dimensoes nominais: {plan['nominal_width_mm']:g} x {plan['nominal_height_mm']:g} mm (EPS min {plan['min_thickness_mm']:g} mm)\n"
            f"Trajetoria planejada: {plan['strategy']} | {plan['metrics']['segment_count']} segs | "
            f"{plan['metrics']['total_length_mm']:.1f} mm | -X={plan['metrics']['backtrack_x_count']} | min_seg={plan['metrics']['min_segment_mm']:.2f} mm\n"
            f"SHA-256 da trajetoria: {path_hash}\n"
            f"Correspondencia historica: {meta.get('historical_match') or 'Nenhuma exata'}\n"
            f"Estado: Trajetoria validada offline; TAP de teste ainda nao gerado ate preenchimento presencial do snapshot SCARA e contrato.\n"
            f"Comando apos confirmacao presencial:\n"
            f"  python scripts/prepare_mach3_trial.py {proj_path.name} --profile ..\\local_scara_snapshot.yaml --contract ..\\local_trial_contract.json --output .\\teste_tap\n",
            encoding="utf-8",
        )
        all_files.extend([proj_path, sim_png, rep_json, rep_txt])
        summary_rows.append(report)

    # Unfilled local templates (ZERO fabricated confirmations or limits)
    snap_tpl = output / "local_scara_snapshot.TEMPLATE.yaml"
    snap_tpl.write_text(
        "# Preencha SOMENTE com medicoes reais feitas na SCARA da fabrica.\n"
        "# Salve como local_scara_snapshot.yaml (nunca publique este arquivo no Git ou portal).\n"
        "id: scara_hotwire_eps\n"
        "unit: mm\n"
        "process_type: hotwire_2d\n"
        "profile_locked: false\n"
        "safety:\n"
        "  production_allowed: false\n"
        "work_area:\n"
        "  x_max: CONFIRMAR_PRESENCIALMENTE\n"
        "  y_max: CONFIRMAR_PRESENCIALMENTE\n"
        "  z_max: CONFIRMAR_PRESENCIALMENTE\n"
        "hotwire:\n"
        "  wire_count: CONFIRMAR_PRESENCIALMENTE\n"
        "  effective_kerf_mm: CONFIRMAR_PRESENCIALMENTE\n"
        "  min_segment_mm: CONFIRMAR_PRESENCIALMENTE\n"
        "feed:\n"
        "  default_xy_mm_min: CONFIRMAR_PRESENCIALMENTE\n",
        encoding="utf-8",
    )

    contract_tpl = output / "local_trial_contract.TEMPLATE.json"
    contract_tpl.write_text(
        json.dumps(
            {
                "purpose": "local_supervised_trial",
                "operator_trial_authorized": False,
                "contract": {
                    "controller_profile": "CNC_V",
                    "machine_profile_sha256": "CALCULAR_COM_sha(canonical(profile))_APOS_PREENCHER_SNAPSHOT",
                    "work_offset": "CONFIRMAR_G54_A_G59",
                    "path_control": "CONFIRMAR_G61_OU_G64",
                    "dwell_unit": "CONFIRMAR_seconds_OU_milliseconds",
                    "dwell_value": "CONFIRMAR_NUMERO",
                    "max_dwell_seconds": "CONFIRMAR_LIMITE",
                    "feed_mm_min": "CONFIRMAR_NUMERO",
                    "heat_s": "CONFIRMAR_NUMERO",
                    "max_heat_s": "CONFIRMAR_LIMITE",
                    "io_mapping_confirmed": False,
                    "origin_confirmed": False,
                    "modal_state_confirmed": False,
                    "thermal_parameters_confirmed": False,
                    "limits_confirmed": False,
                    "ordered_path_confirmed": False,
                    "program_end_confirmed": False,
                    "starting_position_confirmed": False,
                },
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    manifest = {
        "purpose": "private_factory_trial_handoff_only",
        "public_catalog_allowed": False,
        "models_count": len(summary_rows),
        "documented_cnc_v_observations": DOCUMENTED_CNC_V_OBSERVATIONS,
        "models": summary_rows,
    }
    summary_json = output / "RESUMO_5_MODELOS.json"
    summary_json.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    readme = output / "ENTREGA_PRIVADA_FABRICA.txt"
    readme.write_text(
        "PACOTE PRIVADO DE ENTREGA PARA TESTE SUPERVISIONADO NA FABRICA (CNC_V / Windows 7)\n"
        "===================================================================================\n"
        "AVISO: Este pacote e ESTRITAMENTE PRIVADO/LOCAL. Nunca subir para o portal publico.\n\n"
        "Conteudo para cada um dos 5 modelos cadastrados no portal:\n"
        "  - projeto_trajetoria.yaml (geometria de trajetoria validada, production_confirmed=false)\n"
        "  - simulacao_trajetoria.png (simulacao offline da trajetoria 2D)\n"
        "  - relatorio_trajetoria.json e RELATORIO_OPERADOR.txt (metricas e diferencas historicas)\n\n"
        "Como gerar os arquivos TESTE-NAO-HOMOLOGADO.tap localmente apos medicao na maquina:\n"
        "  1. Copie local_scara_snapshot.TEMPLATE.yaml -> local_scara_snapshot.yaml e preencha os valores medidos.\n"
        "  2. Copie local_trial_contract.TEMPLATE.json -> local_trial_contract.json, preencha os parametros confirmados,\n"
        "     calcule machine_profile_sha256 e marque operator_trial_authorized=true + as 8 confirmacoes presenciais.\n"
        "  3. Execute scripts/prepare_mach3_trial.py para cada projeto_trajetoria.yaml.\n"
        "  4. Faca primeiro o teste a seco no Mach3 (perfil CNC_V) com energia do fio fisicamente isolada.\n"
        "  5. Somente apos aprovacao fisica presencial, use o fluxo de aprovacao por hashes para publicar no portal.\n",
        encoding="utf-8",
    )

    all_files.extend([snap_tpl, contract_tpl, summary_json, readme])
    # Deterministic SHA256SUMS.txt
    sums_path = output / "SHA256SUMS.txt"
    rows = []
    for f in sorted(all_files, key=lambda p: p.relative_to(output).as_posix()):
        rel = f.relative_to(output).as_posix()
        rows.append(f"{hashlib.sha256(f.read_bytes()).hexdigest()}  {rel}")
    sums_path.write_text("\n".join(rows) + "\n", encoding="utf-8")

    # Private ZIP archive (strictly in outputs/, never public)
    zip_path = output / "HANDOFF_PRIVADO_TESTES.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(all_files + [sums_path], key=lambda p: p.relative_to(output).as_posix()):
            zf.write(f, f.relative_to(output).as_posix())
    return manifest


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--evidence", action="append", type=Path, default=[], help="Optional local factory evidence ZIP(s)")
    a = p.parse_args()
    ev = list(a.evidence)
    for default in (ROOT / "private_evidence" / "MACROS_CNC_V.zip", ROOT / "private_evidence" / "isonunes Projetos.zip"):
        if default.is_file() and default not in ev:
            ev.append(default)
    res = build_private_handoff(a.output, ev)
    print(f"PRIVATE HANDOFF READY ({res['models_count']} models, 0 fabricated TAPs): {a.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
