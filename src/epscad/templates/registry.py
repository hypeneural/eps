from __future__ import annotations

from typing import Any

from epscad.schema import CutPath, PathSegment, Point, ValidationMessage


def build_paths(spec: dict[str, Any]) -> tuple[list[CutPath], list[ValidationMessage]]:
    template = str(spec.get("cut", {}).get("template", ""))
    params = spec.get("cut", {}).get("template_params", {}) or {}
    if template == "straight_cut":
        return _straight_cut(params), []
    if template == "square_test":
        return _square_test(params), []
    if template == "grid_blocks":
        return _grid_blocks(spec), []
    if template == "photo_trace":
        return [], [ValidationMessage("warning", "photo_trace_draft_only", "photo_trace creates draft previews only until scale is confirmed", "cut.template")]
    if template == "profile_2d":
        return _profile_2d(params), []
    if template == "tp40_core":
        from epscad.templates.tp40 import build_tp40_core

        return build_tp40_core(spec)
    return [], [ValidationMessage("error", "template_unsupported", f"Unsupported template={template}", "cut.template")]


def _straight_cut(params: dict[str, Any]) -> list[CutPath]:
    length = float(params.get("length_mm", 500))
    x0 = float(params.get("x0", 0))
    y0 = float(params.get("y0", 0))
    return [
        CutPath(
            id="straight_cut_001",
            layer="CUT_OUTSIDE",
            segments=[PathSegment("LINE", Point(x0, y0), Point(x0 + length, y0), "CUT_OUTSIDE")],
            operation="straight_cut",
        )
    ]


def _square_test(params: dict[str, Any]) -> list[CutPath]:
    width = float(params.get("width_mm", params.get("size_mm", 100)))
    height = float(params.get("height_mm", params.get("size_mm", 100)))
    x0 = float(params.get("x0", 0))
    y0 = float(params.get("y0", 0))
    return [_rectangle("square_test_001", x0, y0, width, height, "CUT_OUTSIDE")]


def _grid_blocks(spec: dict[str, Any]) -> list[CutPath]:
    part = (spec.get("parts") or [{}])[0]
    qty_x = int(part.get("qty_x", 1))
    qty_y = int(part.get("qty_y", 1))
    width = float(part.get("width_x", 100))
    height = float(part.get("height_y", 100))
    segments: list[PathSegment] = []
    for x_index in range(qty_x + 1):
        x = x_index * width
        segments.append(PathSegment("LINE", Point(x, 0), Point(x, qty_y * height), "CUT_SHARED"))
    for y_index in range(qty_y + 1):
        y = y_index * height
        segments.append(PathSegment("LINE", Point(0, y), Point(qty_x * width, y), "CUT_SHARED"))
    return [CutPath(id="grid_blocks_001", layer="CUT_SHARED", segments=segments, operation="grid_blocks")]


def _profile_2d(params: dict[str, Any]) -> list[CutPath]:
    points = params.get("points")
    if not isinstance(points, list) or len(points) < 2:
        return _square_test(params)
    segments: list[PathSegment] = []
    parsed = [Point(float(item[0]), float(item[1])) for item in points]
    for start, end in zip(parsed, parsed[1:]):
        segments.append(PathSegment("LINE", start, end, "CUT_OUTSIDE"))
    if params.get("closed", True):
        segments.append(PathSegment("LINE", parsed[-1], parsed[0], "CUT_OUTSIDE"))
    return [CutPath(id="profile_2d_001", layer="CUT_OUTSIDE", segments=segments, operation="profile_2d")]

def _rectangle(path_id: str, x0: float, y0: float, width: float, height: float, layer: str) -> CutPath:
    p1 = Point(x0, y0)
    p2 = Point(x0 + width, y0)
    p3 = Point(x0 + width, y0 + height)
    p4 = Point(x0, y0 + height)
    return CutPath(
        id=path_id,
        layer=layer,
        segments=[
            PathSegment("LINE", p1, p2, layer),
            PathSegment("LINE", p2, p3, layer),
            PathSegment("LINE", p3, p4, layer),
            PathSegment("LINE", p4, p1, layer),
        ],
        operation="profile_cut",
    )
