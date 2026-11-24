"""Template TP40: miolo de EPS de telha sanduiche com perfil trapezoidal.

Geometria no plano XY do fio quente (o fio percorre o bloco no eixo Z):

* O topo do miolo e plano e coincide com o topo do bloco (y = material.stock.height_y).
* A face inferior copia o perfil trapezoidal TP40 (crista alta / vale baixo).
* Um unico corte ondulado separa o bloco em duas pecas complementares:
  miolo (acima da linha) e contra-forma (abaixo, reaproveitavel).

Sequencia (simetrica): meio vale, [rampa, crista, rampa, vale] x n_waves, com o
ultimo vale pela metade. Largura = n_waves * pitch. Total de segmentos = 4n + 1.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import atan2, degrees, hypot, isfinite
from typing import Any

from epscad.schema import CutPath, PathSegment, Point, ValidationMessage


LAYER_CUT = "CUT_OUTSIDE"
LAYER_REF_STOCK = "REF_STOCK"
LAYER_REF_NOMINAL = "REF_NOMINAL"
CUT_MODES = ("wavy_line", "core_outline")
KERF_KEEP = ("core", "complement")
WIDTH_TOLERANCE_MM = 0.5


@dataclass(frozen=True)
class Tp40Params:
    profile_height_mm: float
    pitch_mm: float
    crest_width_mm: float
    valley_width_mm: float
    n_waves: int
    min_thickness_mm: float
    panel_width_mm: float
    x0_mm: float = 0.0
    cut_mode: str = "wavy_line"
    kerf_keep: str = "core"
    profile_confirmed: bool = False

    @property
    def run_mm(self) -> float:
        return (self.pitch_mm - self.crest_width_mm - self.valley_width_mm) / 2.0

    @property
    def slope_angle_deg(self) -> float:
        return degrees(atan2(self.profile_height_mm, self.run_mm))


def _num(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value) if isfinite(value) else None
    return None


def parse_params(spec: dict[str, Any]) -> tuple[Tp40Params | None, list[ValidationMessage]]:
    raw = (spec.get("cut", {}) or {}).get("template_params", {}) or {}
    stock = (spec.get("material", {}) or {}).get("stock", {}) or {}
    messages: list[ValidationMessage] = []

    def error(code: str, text: str, field: str = "cut.template_params") -> None:
        messages.append(ValidationMessage("error", code, text, field))

    values: dict[str, float] = {}
    for key in ("profile_height_mm", "pitch_mm", "crest_width_mm", "valley_width_mm", "min_thickness_mm"):
        number = _num(raw.get(key))
        if number is None or number <= 0:
            error("tp40_param_invalid", f"{key} must be a number > 0", f"cut.template_params.{key}")
        else:
            values[key] = number
    n_waves = raw.get("n_waves")
    if not isinstance(n_waves, int) or isinstance(n_waves, bool) or not 1 <= n_waves <= 100:
        error("tp40_param_invalid", "n_waves must be an integer from 1 to 100", "cut.template_params.n_waves")
        n_waves = 0
    x0 = _num(raw.get("x0_mm", 0))
    if x0 is None or x0 < 0:
        error("tp40_param_invalid", "x0_mm must be a number >= 0", "cut.template_params.x0_mm")
        x0 = 0.0
    cut_mode = raw.get("cut_mode", "wavy_line")
    if cut_mode not in CUT_MODES:
        error("tp40_param_invalid", f"cut_mode must be one of {CUT_MODES}", "cut.template_params.cut_mode")
    kerf_keep = raw.get("kerf_keep", "core")
    if kerf_keep not in KERF_KEEP:
        error("tp40_param_invalid", f"kerf_keep must be one of {KERF_KEEP}", "cut.template_params.kerf_keep")
    if messages:
        return None, messages

    pitch = values["pitch_mm"]
    run = (pitch - values["crest_width_mm"] - values["valley_width_mm"]) / 2.0
    if run <= 0:
        error("tp40_profile_invalid", "crest_width_mm + valley_width_mm must be < pitch_mm (ramp run must be > 0)")
        return None, messages

    width = n_waves * pitch
    declared = raw.get("panel_width_mm")
    if declared is not None:
        declared_number = _num(declared)
        if declared_number is None or abs(declared_number - width) > WIDTH_TOLERANCE_MM:
            error(
                "tp40_width_mismatch",
                f"panel_width_mm={declared!r} does not match n_waves*pitch_mm={width:g}",
                "cut.template_params.panel_width_mm",
            )

    height_y = _num(stock.get("height_y"))
    if height_y is None:
        error("tp40_stock_required", "material.stock.height_y is required", "material.stock.height_y")
    elif values["profile_height_mm"] + values["min_thickness_mm"] > height_y + 1e-6:
        error(
            "tp40_exceeds_stock_height",
            f"profile_height + min_thickness ({values['profile_height_mm'] + values['min_thickness_mm']:g} mm) exceeds stock height_y {height_y:g} mm",
            "material.stock.height_y",
        )
    if messages:
        return None, messages

    return (
        Tp40Params(
            profile_height_mm=values["profile_height_mm"],
            pitch_mm=pitch,
            crest_width_mm=values["crest_width_mm"],
            valley_width_mm=values["valley_width_mm"],
            n_waves=n_waves,
            min_thickness_mm=values["min_thickness_mm"],
            panel_width_mm=width,
            x0_mm=x0,
            cut_mode=cut_mode,
            kerf_keep=kerf_keep,
            profile_confirmed=raw.get("profile_confirmed") is True,
        ),
        messages,
    )


def profile_points(params: Tp40Params, top_y: float) -> list[Point]:
    """Linha de corte nominal (centerline), da esquerda para a direita."""
    crest_y = top_y - params.min_thickness_mm
    valley_y = crest_y - params.profile_height_mm
    run = params.run_mm
    x = params.x0_mm
    points = [Point(x, valley_y)]
    x += params.valley_width_mm / 2.0
    points.append(Point(x, valley_y))
    for index in range(params.n_waves):
        x += run
        points.append(Point(x, crest_y))
        x += params.crest_width_mm
        points.append(Point(x, crest_y))
        x += run
        points.append(Point(x, valley_y))
        x += params.valley_width_mm if index < params.n_waves - 1 else params.valley_width_mm / 2.0
        points.append(Point(x, valley_y))
    return [Point(round(p.x, 6), round(p.y, 6)) for p in points]


def offset_polyline(points: list[Point], distance: float) -> list[Point]:
    """Offset (miter) de polilinha aberta; distance > 0 desloca para a esquerda do sentido."""
    if len(points) < 2 or distance == 0:
        return list(points)
    normals: list[tuple[float, float]] = []
    for a, b in zip(points, points[1:]):
        length = hypot(b.x - a.x, b.y - a.y)
        if length <= 1e-9:
            raise ValueError("zero-length segment in polyline offset")
        normals.append((-(b.y - a.y) / length, (b.x - a.x) / length))
    result = [Point(points[0].x + distance * normals[0][0], points[0].y + distance * normals[0][1])]
    for index in range(1, len(points) - 1):
        n1, n2 = normals[index - 1], normals[index]
        denom = 1.0 + n1[0] * n2[0] + n1[1] * n2[1]
        if denom < 1e-6:
            raise ValueError("polyline turns back on itself; cannot offset")
        scale = distance / denom
        result.append(Point(points[index].x + scale * (n1[0] + n2[0]), points[index].y + scale * (n1[1] + n2[1])))
    result.append(Point(points[-1].x + distance * normals[-1][0], points[-1].y + distance * normals[-1][1]))
    return [Point(round(p.x, 6), round(p.y, 6), p.z) for p in result]


def _kerf_offset(spec: dict[str, Any], params: Tp40Params) -> tuple[float, list[ValidationMessage]]:
    if (spec.get("cut", {}) or {}).get("compensation") != "thermal_kerf_offset_applied":
        return 0.0, []
    kerf = _num(((spec.get("process", {}) or {}).get("hotwire", {}) or {}).get("effective_kerf_mm"))
    if kerf is None or kerf <= 0:
        return 0.0, [
            ValidationMessage(
                "error",
                "tp40_kerf_required",
                "compensation=thermal_kerf_offset_applied requires numeric effective_kerf_mm > 0",
                "process.hotwire.effective_kerf_mm",
            )
        ]
    # Percurso esquerda->direita: normal esquerda = +Y. Manter o miolo (acima) => fio abaixo da linha nominal.
    half = kerf / 2.0
    return (-half if params.kerf_keep == "core" else half), []


def _top_y(spec: dict[str, Any]) -> float:
    return float(spec["material"]["stock"]["height_y"])


def build_tp40_core(spec: dict[str, Any]) -> tuple[list[CutPath], list[ValidationMessage]]:
    params, messages = parse_params(spec)
    if params is None:
        return [], messages
    top_y = _top_y(spec)
    nominal = profile_points(params, top_y)
    distance, kerf_messages = _kerf_offset(spec, params)
    messages.extend(kerf_messages)
    if kerf_messages:
        return [], messages
    cut_points = offset_polyline(nominal, distance) if distance else nominal

    segments = [PathSegment("LINE", a, b, LAYER_CUT) for a, b in zip(cut_points, cut_points[1:])]
    if params.cut_mode == "core_outline":
        right_top = Point(cut_points[-1].x, top_y)
        left_top = Point(cut_points[0].x, top_y)
        segments.append(PathSegment("LINE", cut_points[-1], right_top, LAYER_CUT))
        segments.append(PathSegment("LINE", right_top, left_top, LAYER_CUT))
        segments.append(PathSegment("LINE", left_top, cut_points[0], LAYER_CUT))
    path = CutPath(id="tp40_core_001", layer=LAYER_CUT, segments=segments, operation="tp40_core")
    return [path], messages


def reference_segments(spec: dict[str, Any]) -> list[PathSegment]:
    """Bloco EPS e linha nominal (se houver compensacao) para preview/PDF. Nunca vao ao DXF."""
    params, _ = parse_params(spec)
    if params is None:
        return []
    stock = spec["material"]["stock"]
    length_x, height_y = float(stock["length_x"]), float(stock["height_y"])
    corners = [Point(0, 0), Point(length_x, 0), Point(length_x, height_y), Point(0, height_y)]
    refs = [PathSegment("LINE", corners[i], corners[(i + 1) % 4], LAYER_REF_STOCK) for i in range(4)]
    distance, _ = _kerf_offset(spec, params)
    if distance:
        nominal = profile_points(params, height_y)
        refs.extend(PathSegment("LINE", a, b, LAYER_REF_NOMINAL) for a, b in zip(nominal, nominal[1:]))
    return refs


def metadata(spec: dict[str, Any]) -> dict[str, Any]:
    params, _ = parse_params(spec)
    if params is None:
        return {}
    distance, _ = _kerf_offset(spec, params)
    top_y = _top_y(spec)
    return {
        "profile_height_mm": params.profile_height_mm,
        "pitch_mm": params.pitch_mm,
        "crest_width_mm": params.crest_width_mm,
        "valley_width_mm": params.valley_width_mm,
        "n_waves": params.n_waves,
        "min_thickness_mm": params.min_thickness_mm,
        "panel_width_mm": params.panel_width_mm,
        "ramp_run_mm": round(params.run_mm, 4),
        "ramp_angle_deg": round(params.slope_angle_deg, 2),
        "core_total_height_mm": params.profile_height_mm + params.min_thickness_mm,
        "cut_line_y_range_mm": [round(top_y - params.min_thickness_mm - params.profile_height_mm, 4), round(top_y - params.min_thickness_mm, 4)],
        "cut_mode": params.cut_mode,
        "kerf_keep": params.kerf_keep,
        "kerf_offset_mm": distance,
        "profile_confirmed": params.profile_confirmed,
    }
