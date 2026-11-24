from __future__ import annotations

from math import hypot
from typing import Any

from epscad.loader import load_machine_profile
from epscad.schema import CutPath, PathSegment, ValidationMessage
from epscad.validators.common import DXF_STATUSES, as_number, get_path


TOLERANCE_MM = 0.001
ROUND_DIGITS = 4


def validate_geometry(
    spec: dict[str, Any],
    paths: list[CutPath],
    machine_profile: dict[str, Any] | None = None,
) -> list[ValidationMessage]:
    messages: list[ValidationMessage] = []
    segments = [segment for path in paths for segment in path.segments]
    if not segments:
        return messages

    messages.extend(_validate_segment_lengths(spec, segments))
    messages.extend(_validate_duplicate_segments(segments))
    bbox = _bbox(segments)
    messages.extend(_validate_stock_bounds(spec, bbox))
    messages.extend(_validate_machine_area(spec, bbox, machine_profile))
    return messages


def _validate_segment_lengths(spec: dict[str, Any], segments: list[PathSegment]) -> list[ValidationMessage]:
    messages: list[ValidationMessage] = []
    min_segment = as_number(get_path(spec, "process.hotwire.min_segment_mm"))
    for index, segment in enumerate(segments):
        length = _segment_length(segment)
        path = f"paths.segments[{index}]"
        if length <= TOLERANCE_MM:
            messages.append(ValidationMessage("error", "geometry_zero_length_segment", "segment length is zero", path))
        elif min_segment is not None and length + TOLERANCE_MM < min_segment:
            messages.append(
                ValidationMessage(
                    "error",
                    "geometry_segment_too_short",
                    f"segment length {length:.4f} mm is shorter than min_segment_mm {min_segment:.4f}",
                    path,
                )
            )
    return messages


def _validate_duplicate_segments(segments: list[PathSegment]) -> list[ValidationMessage]:
    messages: list[ValidationMessage] = []
    seen: dict[tuple[tuple[float, float], tuple[float, float]], int] = {}
    previous: list[tuple[int, PathSegment]] = []
    for index, segment in enumerate(segments):
        key = _normalized_key(segment)
        if key in seen:
            messages.append(
                ValidationMessage(
                    "error",
                    "geometry_duplicate_segment",
                    f"segment duplicates segment {seen[key]}",
                    f"paths.segments[{index}]",
                )
            )
            continue
        seen[key] = index
        for previous_index, other in previous:
            if _collinear_overlap_length(segment, other) > TOLERANCE_MM:
                messages.append(
                    ValidationMessage(
                        "error",
                        "geometry_collinear_overlap",
                        f"segment overlaps collinear segment {previous_index}",
                        f"paths.segments[{index}]",
                    )
                )
                break
        previous.append((index, segment))
    return messages


def _validate_stock_bounds(spec: dict[str, Any], bbox: dict[str, float]) -> list[ValidationMessage]:
    length_x = as_number(get_path(spec, "material.stock.length_x"))
    height_y = as_number(get_path(spec, "material.stock.height_y"))
    if height_y is None:
        height_y = as_number(get_path(spec, "material.stock.width_y"))
    if length_x is None or height_y is None:
        return []
    if _outside_bounds(bbox, length_x, height_y):
        return [
            ValidationMessage(
                "error",
                "geometry_outside_stock",
                f"bbox {bbox} is outside stock {length_x:.4f} x {height_y:.4f} mm",
                "material.stock",
            )
        ]
    return []


def _validate_machine_area(
    spec: dict[str, Any],
    bbox: dict[str, float],
    machine_profile: dict[str, Any] | None,
) -> list[ValidationMessage]:
    profile = machine_profile
    if profile is None:
        profile_id = str(get_path(spec, "machine.profile") or "")
        try:
            profile = load_machine_profile(profile_id)
        except (FileNotFoundError, ValueError):
            return []
    x_max = as_number(get_path(profile, "work_area.x_max"))
    y_max = as_number(get_path(profile, "work_area.y_max"))
    if x_max is None or y_max is None:
        status = str(get_path(spec, "project.status") or "draft")
        if status in DXF_STATUSES:
            return [
                ValidationMessage(
                    "warning",
                    "geometry_machine_area_unverified",
                    "machine work_area X/Y is not numeric; bbox was NOT checked against the real machine area",
                    "machine_profiles.work_area",
                )
            ]
        return []
    if _outside_bounds(bbox, x_max, y_max):
        return [
            ValidationMessage(
                "error",
                "geometry_outside_machine_area",
                f"bbox {bbox} is outside machine area {x_max:.4f} x {y_max:.4f} mm",
                "machine_profiles.work_area",
            )
        ]
    return []


def _segment_length(segment: PathSegment) -> float:
    return hypot(segment.end.x - segment.start.x, segment.end.y - segment.start.y)


def _normalized_key(segment: PathSegment) -> tuple[tuple[float, float], tuple[float, float]]:
    start = (round(segment.start.x, ROUND_DIGITS), round(segment.start.y, ROUND_DIGITS))
    end = (round(segment.end.x, ROUND_DIGITS), round(segment.end.y, ROUND_DIGITS))
    return tuple(sorted((start, end)))  # type: ignore[return-value]


def _bbox(segments: list[PathSegment]) -> dict[str, float]:
    xs = []
    ys = []
    for segment in segments:
        xs.extend([segment.start.x, segment.end.x])
        ys.extend([segment.start.y, segment.end.y])
    return {
        "min_x": round(min(xs), ROUND_DIGITS),
        "min_y": round(min(ys), ROUND_DIGITS),
        "max_x": round(max(xs), ROUND_DIGITS),
        "max_y": round(max(ys), ROUND_DIGITS),
        "width": round(max(xs) - min(xs), ROUND_DIGITS),
        "height": round(max(ys) - min(ys), ROUND_DIGITS),
    }


def _outside_bounds(bbox: dict[str, float], x_max: float, y_max: float) -> bool:
    return (
        bbox["min_x"] < -TOLERANCE_MM
        or bbox["min_y"] < -TOLERANCE_MM
        or bbox["max_x"] > x_max + TOLERANCE_MM
        or bbox["max_y"] > y_max + TOLERANCE_MM
    )


def _collinear_overlap_length(a: PathSegment, b: PathSegment) -> float:
    ax = a.end.x - a.start.x
    ay = a.end.y - a.start.y
    bx0 = b.start.x - a.start.x
    by0 = b.start.y - a.start.y
    bx1 = b.end.x - a.start.x
    by1 = b.end.y - a.start.y
    cross0 = ax * by0 - ay * bx0
    cross1 = ax * by1 - ay * bx1
    if abs(cross0) > TOLERANCE_MM or abs(cross1) > TOLERANCE_MM:
        return 0.0
    if abs(ax) >= abs(ay):
        return _interval_overlap((a.start.x, a.end.x), (b.start.x, b.end.x))
    return _interval_overlap((a.start.y, a.end.y), (b.start.y, b.end.y))


def _interval_overlap(first: tuple[float, float], second: tuple[float, float]) -> float:
    first_min, first_max = sorted(first)
    second_min, second_max = sorted(second)
    return max(0.0, min(first_max, second_max) - max(first_min, second_min))
