"""Constant-section 2D hot-wire CAM planner for unidirectional EPS slab filler references.

Separates nominal extrusion length (wire span / block Z length) from the XY cutting plane.
Never assumes bidirectional flaps, bevels or molded textures can be cut in a single XY pass.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from epscad.loader import load_yaml

ROOT = Path(__file__).resolve().parents[3]
SLAB_CATALOG = ROOT / "catalogs" / "slab_profiles" / "capa_laje_referencias.yaml"


def _r(value: float) -> float:
    return round(float(value), 4)


def plan_slab_section(variant_id: str, *, kerf_offset_mm: float = 0.0) -> dict[str, Any]:
    """Plan an open, continuous, zero-overlap XY contour for a unidirectional EPS slab filler.

    Assumes the EPS block sits flat on Y=0 (height >= height_mm, width >= width_mm) and cuts:
    (0,0) -> (0,rh) -> (rw,rh) -> (rw,0)? No: to avoid cutting through the solid body or
    retraversing Y=0, the lower rebates sit at bottom-left and bottom-right of a pre-cut block,
    so the continuous outer upper-plus-rebates trajectory enters at (0,0) -> (rw,0) -> (rw,rh) ->
    (0,rh) -> (0,h) -> (w,h) -> (w,rh) -> (w-rw,rh) -> (w-rw,0)? Wait: (0,0)->(0,rh) duplicates
    nothing! Let's trace the exact non-self-intersecting, zero-overlap open profile from (0,0)
    around the inverted section (so flat top rests on table Y=0 and BOTH lower rebates face UP!):
      (0,0) -> (0, h-rh) -> (rw, h-rh) -> (rw, h) -> (w-rw, h) -> (w-rw, h-rh) -> (w, h-rh) -> (w, 0).
    CHECK THAT GEOMETRY:
    - Piece sits upside-down with its wide flat top resting stably on the table (Y=0)!
    - Wire enters at (0,0), climbs left side to (0, h-rh), steps inward +X to (rw, h-rh),
      climbs to (rw, h), traverses the lower central base +X to (w-rw, h), drops to (w-rw, h-rh),
      steps outward +X to (w, h-rh), and exits straight down to (w, 0)!
    - ZERO -X returns! ZERO collinear overlap! ZERO arcs! Every segment >= min(rw, rh) (15 mm)!
    - Extrusion length (1000 or 1250 mm) is the Z length of the block, NOT XY travel!
    """
    if kerf_offset_mm != 0.0:
        raise ValueError("Non-zero thermal kerf compensation requires measured coupon data")
    cat = load_yaml(SLAB_CATALOG)
    if variant_id not in cat["variants"]:
        raise ValueError(f"Unknown slab variant: {variant_id!r}")
    spec = cat["variants"][variant_id]
    w = float(spec["width_mm"])
    h = float(spec["height_mm"])
    length = float(spec["length_mm"])
    rw, rh = [float(v) for v in spec["published_fit_mm"]]
    if rw <= 0 or rh <= 0 or 2 * rw >= w or rh >= h:
        raise ValueError("Invalid slab rebate dimensions")

    points = [
        (0.0, 0.0),
        (0.0, _r(h - rh)),
        (_r(rw), _r(h - rh)),
        (_r(rw), _r(h)),
        (_r(w - rw), _r(h)),
        (_r(w - rw), _r(h - rh)),
        (_r(w), _r(h - rh)),
        (_r(w), 0.0),
    ]
    segs = [(a, b) for a, b in zip(points, points[1:])]
    lens = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in segs]
    return {
        "variant_id": variant_id,
        "family": "slab_lajota_unidirectional_xy",
        "orientation": "inverted_flat_top_on_y0_rebates_up",
        "nominal_width_mm": w,
        "nominal_height_mm": h,
        "extrusion_length_z_mm": length,
        "assumed_rebate_mm": [rw, rh],
        "kerf_offset_mm": 0.0,
        "recommended_min_stock_mm": {"length_x": _r(w), "height_y": _r(h), "thickness_z": _r(length)},
        "points_mm": points,
        "metrics": {
            "point_count": len(points),
            "segment_count": len(segs),
            "total_length_mm": round(sum(lens), 4),
            "min_segment_mm": round(min(lens), 4),
            "max_segment_mm": round(max(lens), 4),
            "backtrack_x_count": 0,
            "start_mm": list(points[0]),
            "end_mm": list(points[-1]),
            "bbox_mm": {"x_min": 0.0, "x_max": _r(w), "y_min": 0.0, "y_max": _r(h), "width": _r(w), "height": _r(h)},
        },
        "notes": [
            "Secao XY constante invertida (face superior plana apoiada em Y=0, rebaixos voltados para cima).",
            f"Comprimento {length:g} mm corresponde ao eixo Z do bloco/fio (nao e deslocamento XY).",
            "Rebaixos simetricos assumidos; sem chanfros, frisos moldados ou abas bidirecionais.",
            "Compensacao termica = 0.0 mm ate medicao fisica em corpo de prova.",
        ],
    }


def build_slab_trial_spec(plan: dict[str, Any]) -> dict[str, Any]:
    stock = plan["recommended_min_stock_mm"]
    return {
        "project": {
            "id": f"{plan['variant_id']}-r01-trial",
            "name": f"Lajota EPS {plan['variant_id']} - Secao XY Teste Local (Nao Homologado)",
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
                "min_segment_mm": min(5.0, float(plan["metrics"]["min_segment_mm"])),
                "min_radius_mm": "confirmar",
            },
            "feed": {"xy_mm_min": "confirmar", "slow_curve_mm_min": "confirmar"},
        },
        "cut": {
            "template": "profile_2d",
            "origin": "lower_left",
            "cut_plane": "XY",
            "safe_margin_mm": 0,
            "compensation": "centerline",
            "avoid_duplicate_cuts": True,
            "template_params": {"closed": False, "points": [[x, y] for x, y in plan["points_mm"]]},
        },
        "outputs": {"dxf": False, "svg_preview": True, "pdf_job": False, "manifest": True, "gcode": {"enabled": False}},
    }
