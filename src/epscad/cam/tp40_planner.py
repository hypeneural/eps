"""Dedicated 2D hot-wire CAM trajectory planners for TP40 EPS families.

Strictly separates nominal CAD geometry, thermal compensation (currently 0.0 mm
until measured on physical coupons), and ordered wire cutting trajectories.
Never converts STL/GLB meshes into cutting paths and never approves production.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from epscad.exporters.tap_simulator import parse_tap_modal
from epscad.loader import load_yaml

ROOT = Path(__file__).resolve().parents[3]
CATALOG_DIR = ROOT / "catalogs" / "roof_profiles"

PORTAL_MODELS: tuple[dict[str, Any], ...] = (
    {
        "portal_id": "tp40-base-lisa",
        "revision": "r01",
        "name": "TP40 Base lisa",
        "catalog_id": "tp40_980_microgroove_review",
        "family": "tp40_base_lisa_microgroove",
        "min_thickness_mm": 31.0,
        "length_mm": 1000.0,
        "historical_match": "telha tp 40 base lisa.tap",
        "historical_match_kind": "exact_geometry_family",
    },
    {
        "portal_id": "tp40-base-lisa-50mm",
        "revision": "r01",
        "name": "TP40 Base lisa 50 mm",
        "catalog_id": "tp40_980_microgroove_review",
        "family": "tp40_base_lisa_microgroove",
        "min_thickness_mm": 50.0,
        "length_mm": 1000.0,
        "historical_match": "telha tp 40 base lisa.tap",
        "historical_match_kind": "parametric_thickness_variant_only",
    },
    {
        "portal_id": "tp40-980-sks-30mm",
        "revision": "r01",
        "name": "TP40/980 Comercial 30 mm (Ref. SKS)",
        "catalog_id": "tp40_980_sks",
        "family": "tp40_commercial_continuous",
        "min_thickness_mm": 30.0,
        "length_mm": 1000.0,
        "historical_match": None,
        "historical_match_kind": "none_exact_commercial_reference",
        "historical_nearest_note": "Sem TAP exato; brastelha isonunes.tap (980x35) e TP40 palhoca.tap (980x37) possuem degrau central no vale e altura diferente.",
    },
    {
        "portal_id": "tp40-980-sks-50mm",
        "revision": "r01",
        "name": "TP40/980 Comercial 50 mm (Ref. SKS)",
        "catalog_id": "tp40_980_sks",
        "family": "tp40_commercial_continuous",
        "min_thickness_mm": 50.0,
        "length_mm": 1000.0,
        "historical_match": None,
        "historical_match_kind": "none_exact_commercial_reference",
        "historical_nearest_note": "Sem TAP exato; telha tp 40 5 cm.tap (980x55) tem degrau central 55x5 mm no vale e faixa Y=[20..55], distinta da referencia SKS 980x86.",
    },
    {
        "portal_id": "tp40-1020-isoeste-30mm",
        "revision": "r01",
        "name": "TP40/1020 Comercial 30 mm (Ref. Isoeste)",
        "catalog_id": "tp40_1020_isoeste",
        "family": "tp40_commercial_continuous",
        "min_thickness_mm": 30.0,
        "length_mm": 1000.0,
        "historical_match": None,
        "historical_match_kind": "none_exact_commercial_reference",
        "historical_nearest_note": "Sem TAP exato; Telha TR40.tap (1018x38, passo 252) e telha TR40 PERFEITO.tap (1007.5x41.5) sao familia 4 ondas distinta da Isoeste 1020x70 (passo 255).",
    },
)


def _r(value: float) -> float:
    return round(float(value), 4)


def _metrics_for_points(points: list[tuple[float, float]]) -> dict[str, Any]:
    segs = [(a, b) for a, b in zip(points, points[1:]) if math.hypot(b[0] - a[0], b[1] - a[1]) > 1e-9]
    lens = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in segs]
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    backtracks = sum(1 for a, b in segs if b[0] < a[0] - 1e-4)
    return {
        "point_count": len(points),
        "segment_count": len(segs),
        "total_length_mm": round(sum(lens), 4),
        "min_segment_mm": round(min(lens), 4) if lens else 0.0,
        "max_segment_mm": round(max(lens), 4) if lens else 0.0,
        "backtrack_x_count": backtracks,
        "start_mm": list(points[0]),
        "end_mm": list(points[-1]),
        "bbox_mm": {
            "x_min": round(min(xs), 4),
            "x_max": round(max(xs), 4),
            "y_min": round(min(ys), 4),
            "y_max": round(max(ys), 4),
            "width": round(max(xs) - min(xs), 4),
            "height": round(max(ys) - min(ys), 4),
        },
    }


def plan_tp40_base_lisa(
    *,
    min_thickness_mm: float = 31.0,
    strategy: str = "continuous_clean",
    lead_in_x_mm: float = 5.0,
    left_trim_gap_mm: float = 1.0,
    kerf_offset_mm: float = 0.0,
) -> dict[str, Any]:
    """Plan 2D hot-wire trajectory for TP40 Base lisa with 48x2 mm microgrooves.

    Strategies:
    - ``continuous_clean``: Zero-overlap single-pass +X wire path starting at (0,0),
      eliminating the 820 mm Y=0 double-burn and 21 -X returns (requires pre-squared
      bottom/left EPS block face at Y=0, X=0).
    - ``historical_pocket``: Exact forensic reconstruction of factory
      ``telha tp 40 base lisa.tap`` (50 segments, 5 mm lead-in + 1 mm left trim loop
      + 5 closed scrap pockets with 21 -X returns and 820 mm Y=0 overlaps).
    """
    if kerf_offset_mm != 0.0:
        raise ValueError("Non-zero thermal kerf compensation requires measured coupon data")
    if strategy not in ("continuous_clean", "historical_pocket"):
        raise ValueError(f"Unsupported TP40 Base lisa strategy: {strategy!r}")

    spec = load_yaml(CATALOG_DIR / "tp40_980_microgroove_review.yaml")
    g = spec["geometry"]
    pitch = float(g["pitch_mm"])
    periods = int(g["periods"])
    rib = float(g["rib_height_mm"])
    ramp = float(g["ramp_run_mm"])
    crest = float(g["crest_span_mm"])
    gw = float(g["groove_width_mm"])
    gd = float(g["groove_depth_mm"])
    valley = float(g["valley_width_mm"])
    shoulder = (crest - gw) / 2.0
    cavity_span = 2.0 * ramp + crest
    total_h = rib + float(min_thickness_mm)

    points: list[tuple[float, float]] = []

    def add(x: float, y: float) -> None:
        pt = (_r(x), _r(y))
        if not points or points[-1] != pt:
            points.append(pt)

    if strategy == "continuous_clean":
        add(0.0, 0.0)
        for k in range(periods):
            x0 = k * pitch
            add(x0 + ramp, rib)
            add(x0 + ramp + shoulder, rib)
            add(x0 + ramp + shoulder, rib - gd)
            add(x0 + ramp + shoulder + gw, rib - gd)
            add(x0 + ramp + shoulder + gw, rib)
            add(x0 + ramp + crest, rib)
            add(x0 + cavity_span, 0.0)
            add(x0 + cavity_span + valley, 0.0)
        add(periods * pitch, total_h)
        stock_x = periods * pitch
        notes = [
            "Trajetoria continua +X sem sobreposicao (0.0 mm) e sem retornos -X.",
            "Exige bloco EPS previamente esquadrejado na base (Y=0) e face esquerda (X=0).",
            "Menor segmento = profundidade da microdobra (2.0 mm); exige min_segment_mm <= 2.0 confirmado.",
            "Compensacao termica = 0.0 mm (centro do fio) ate medicao de kerf em corpo de prova.",
        ]
    else:
        x_base = float(lead_in_x_mm) + float(left_trim_gap_mm)
        add(0.0, 0.0)
        add(lead_in_x_mm, 0.0)
        add(lead_in_x_mm, total_h)
        add(x_base, total_h)
        add(x_base, 0.0)
        for k in range(periods):
            xl = x_base + k * pitch
            xr = xl + cavity_span
            if k == 0:
                add(xl + ramp, rib)
                add(xl + ramp + shoulder, rib)
                add(xl + ramp + shoulder, rib - gd)
                add(xl + ramp + shoulder + gw, rib - gd)
                add(xl + ramp + shoulder + gw, rib)
                add(xl + ramp + crest, rib)
                add(xr, 0.0)
                add(xl, 0.0)
                add(xl + pitch, 0.0)
            else:
                add(xr, 0.0)
                add(xr - ramp, rib)
                add(xr - ramp - shoulder, rib)
                add(xr - ramp - shoulder, rib - gd)
                add(xr - ramp - shoulder - gw, rib - gd)
                add(xr - ramp - shoulder - gw, rib)
                add(xr - ramp - crest, rib)
                add(xl, 0.0)
                add(xl + pitch, 0.0)
        add(x_base + periods * pitch, total_h)
        stock_x = x_base + periods * pitch
        notes = [
            "Reconstrucao forense 1:1 da logica de bolsos fechados de telha tp 40 base lisa.tap.",
            "Inclui entrada 5 mm, laco lateral de 1 mm, 21 retornos -X e 820 mm de sobreposicao colinear em Y=0.",
            "Compensacao termica = 0.0 mm (centro do fio) ate medicao de kerf em corpo de prova.",
        ]

    return {
        "family": "tp40_base_lisa_microgroove",
        "catalog_id": spec["id"],
        "strategy": strategy,
        "nominal_width_mm": periods * pitch,
        "nominal_height_mm": total_h,
        "min_thickness_mm": float(min_thickness_mm),
        "kerf_offset_mm": 0.0,
        "recommended_min_stock_mm": {"length_x": _r(stock_x), "height_y": _r(total_h), "thickness_z": 1000.0},
        "points_mm": points,
        "metrics": _metrics_for_points(points),
        "notes": notes,
    }


def plan_tp40_commercial_continuous(
    catalog_id: str,
    *,
    min_thickness_mm: float | None = None,
    kerf_offset_mm: float = 0.0,
) -> dict[str, Any]:
    """Plan continuous +X hot-wire trajectory for commercial TP40 references (SKS / Isoeste).

    Starts at (0,0), rises vertically to valley height (min_thickness_mm), cuts all
    symmetric trapezoidal waves continuously in +X with zero overlaps and zero -X returns,
    and exits vertically to (panel_width_mm, 0). The lower cut piece sits flat on Y=0 with
    exact nominal thickness and total height.
    """
    if kerf_offset_mm != 0.0:
        raise ValueError("Non-zero thermal kerf compensation requires measured coupon data")
    ref = load_yaml(CATALOG_DIR / f"{catalog_id}.yaml")
    p = ref["profile"]
    pitch = float(p["pitch_mm"])
    n_waves = int(p["n_waves"])
    rib = float(p["profile_height_mm"])
    crest = float(p["crest_width_mm"])
    valley = float(p["valley_width_mm"])
    panel_w = float(p["panel_width_mm"])
    tmin = float(p["min_thickness_mm"] if min_thickness_mm is None else min_thickness_mm)
    ramp = (pitch - crest - valley) / 2.0
    if ramp <= 0:
        raise ValueError("Invalid trapezoidal ramp")

    y_low = tmin
    y_high = tmin + rib
    points: list[tuple[float, float]] = [(0.0, 0.0), (0.0, _r(y_low))]
    x = 0.0
    half_v = valley / 2.0
    for i in range(n_waves):
        if i == 0:
            x += half_v
            points.append((_r(x), _r(y_low)))
        x += ramp
        points.append((_r(x), _r(y_high)))
        x += crest
        points.append((_r(x), _r(y_high)))
        x += ramp
        points.append((_r(x), _r(y_low)))
        x += valley if i < n_waves - 1 else half_v
        points.append((_r(x), _r(y_low)))
    points.append((_r(panel_w), 0.0))

    return {
        "family": "tp40_commercial_continuous",
        "catalog_id": ref["id"],
        "strategy": "continuous_wavy_base_flat",
        "nominal_width_mm": panel_w,
        "nominal_height_mm": y_high,
        "min_thickness_mm": tmin,
        "kerf_offset_mm": 0.0,
        "recommended_min_stock_mm": {"length_x": _r(panel_w), "height_y": _r(y_high + 20.0), "thickness_z": 1000.0},
        "points_mm": points,
        "metrics": _metrics_for_points(points),
        "notes": [
            f"Referencia comercial simplificada ({ref.get('manufacturer', catalog_id)}); sem microdobras modeladas.",
            "Trajetoria continua +X com origem em (0,0), subida vertical para espessura minima e saida vertical em Y=0.",
            "Peca resultante abaixo da linha de corte repousa plana em Y=0 com altura total nominal exata.",
            "Compensacao termica = 0.0 mm (centro do fio) ate medicao de kerf em corpo de prova.",
        ],
    }


def plan_portal_model(portal_id: str, *, base_lisa_strategy: str = "continuous_clean") -> dict[str, Any]:
    meta = next((m for m in PORTAL_MODELS if m["portal_id"] == portal_id), None)
    if meta is None:
        raise ValueError(f"Unknown portal model: {portal_id!r}")
    if meta["family"] == "tp40_base_lisa_microgroove":
        plan = plan_tp40_base_lisa(min_thickness_mm=meta["min_thickness_mm"], strategy=base_lisa_strategy)
    else:
        plan = plan_tp40_commercial_continuous(meta["catalog_id"], min_thickness_mm=meta["min_thickness_mm"])
    return {**meta, "plan": plan}


def build_trial_project_spec(model_bundle: dict[str, Any]) -> dict[str, Any]:
    """Build a validated_geometry YAML spec (production_confirmed=False) ready for prepare_mach3_trial.py."""
    plan = model_bundle["plan"]
    stock = plan["recommended_min_stock_mm"]
    min_seg = min(2.0, plan["metrics"]["min_segment_mm"])
    return {
        "project": {
            "id": f"{model_bundle['portal_id']}-{model_bundle['revision']}-trial",
            "name": f"{model_bundle['name']} - Trajetoria de Teste Local (Nao Homologado)",
            "unit": "mm",
            "status": "validated_geometry",
            "source": {
                "kind": "manual_text",
                "scale_confirmed": True,
                "dimensions_confirmed": True,
                "production_confirmed": False,
            },
        },
        "machine": {
            "profile": "scara_hotwire_eps",
            "process_type": "hotwire_2d",
            "output_format": "dxf_r12",
            "cam_bridge": "Mach3_Direct_Trial",
            "controller_hint": "CNC_V",
        },
        "material": {
            "type": "EPS",
            "density": "confirmar",
            "stock": {
                "length_x": float(stock["length_x"]),
                "height_y": float(stock["height_y"]),
                "thickness_z": float(stock["thickness_z"]),
            },
        },
        "process": {
            "hotwire": {
                "wire_mode": "line_hotwire",
                "wire_count": "confirmar",
                "effective_kerf_mm": "confirmar",
                "lead_in_mm": 0,
                "lead_out_mm": 0,
                "min_segment_mm": float(min_seg),
                "min_radius_mm": "confirmar",
            },
            "feed": {
                "xy_mm_min": "confirmar",
                "slow_curve_mm_min": "confirmar",
            },
        },
        "cut": {
            "template": "profile_2d",
            "origin": "lower_left",
            "cut_plane": "XY",
            "safe_margin_mm": 0,
            "compensation": "centerline",
            "avoid_duplicate_cuts": True,
            "template_params": {
                "closed": False,
                "points": [[x, y] for x, y in plan["points_mm"]],
            },
        },
        "outputs": {
            "dxf": False,
            "svg_preview": True,
            "pdf_job": False,
            "manifest": True,
            "gcode": {"enabled": False},
        },
    }


def compare_plan_vs_historical(plan: dict[str, Any], historical_tap_bytes: bytes | None) -> dict[str, Any]:
    """Compare planned trajectory metrics & vertices against an optional historical factory TAP."""
    pm = plan["metrics"]
    if historical_tap_bytes is None:
        return {
            "has_historical_reference": False,
            "planned_metrics": pm,
            "historical_metrics": None,
            "differences": ["Nenhum programa TAP historico corresponde exatamente a este perfil comercial."],
        }
    hist = parse_tap_modal(historical_tap_bytes)
    hm = hist["metrics"]
    h_pts = [tuple(hist["segments"][0]["start"])] + [tuple(s["end"]) for s in hist["segments"]]
    p_pts = [tuple(p) for p in plan["points_mm"]]
    exact_vertex_diff = None
    if len(h_pts) == len(p_pts):
        dists = [math.hypot(a[0] - b[0], a[1] - b[1]) for a, b in zip(p_pts, h_pts)]
        exact_vertex_diff = {
            "point_count": len(p_pts),
            "max_error_mm": round(max(dists), 6),
            "rms_error_mm": round(math.sqrt(sum(d * d for d in dists) / len(dists)), 6),
        }
    diffs = []
    dx = round(pm["bbox_mm"]["width"] - hm["bbox_mm"]["width"], 4)
    dy = round(pm["bbox_mm"]["height"] - hm["bbox_mm"]["height"], 4)
    dl = round(pm["total_length_mm"] - hm["total_length_mm"], 4)
    if abs(dx) > 1e-4 or abs(dy) > 1e-4:
        diffs.append(f"Delta BBox XY: dX={dx:+.3f} mm, dY={dy:+.3f} mm")
    if abs(dl) > 1e-4:
        diffs.append(f"Delta comprimento de percurso: {dl:+.3f} mm ({pm['total_length_mm']:.1f} vs {hm['total_length_mm']:.1f} mm)")
    if pm["backtrack_x_count"] != hm["backtrack_x_count"]:
        diffs.append(f"Retornos -X: planejado={pm['backtrack_x_count']} vs historico={hm['backtrack_x_count']}")
    if hm["collinear_overlap_mm"] > 0.01:
        diffs.append(f"Historico possui {hm['collinear_overlap_mm']:.1f} mm de sobreposicao colinear em Y=0")
    if hist["warnings"]:
        diffs.append("Avisos modais corrigidos pelo novo pos-processador: " + ", ".join(hist["warnings"]))
    return {
        "has_historical_reference": True,
        "historical_sha256": hist["sha256"],
        "planned_metrics": pm,
        "historical_metrics": hm,
        "historical_modal": hist["modal"],
        "historical_warnings": hist["warnings"],
        "exact_vertex_diff": exact_vertex_diff,
        "differences": diffs,
    }
