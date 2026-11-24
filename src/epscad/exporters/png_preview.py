from __future__ import annotations

import binascii
import struct
import zlib
from pathlib import Path

from epscad.schema import CutJobResult, PathSegment


BACKGROUND = (255, 255, 255)
CUT = (20, 20, 20)
REFERENCE = (170, 170, 170)
ORIGIN = (220, 40, 40)
AXIS_X = (40, 140, 60)
AXIS_Y = (40, 80, 180)
MARGIN_PX = 40
MAX_DRAWING_PX = 1200
MIN_VIEW_MM = 20.0


def write_preview_png(job: CutJobResult, path: str | Path) -> None:
    view = _view_box(job)
    scale = _scale(view)
    width = max(160, int(round((view["max_x"] - view["min_x"]) * scale)) + 2 * MARGIN_PX)
    height = max(160, int(round((view["max_y"] - view["min_y"]) * scale)) + 2 * MARGIN_PX)
    canvas = _blank(width, height)

    _draw_axes(canvas, view, scale)
    for segment in job.reference_segments:
        _draw_segment(canvas, view, scale, segment, REFERENCE, thickness=1)
    for cut_path in job.paths:
        for segment in cut_path.segments:
            if segment.kind.upper() == "LINE":
                _draw_segment(canvas, view, scale, segment, CUT, thickness=2)

    _write_png(Path(path), canvas)


def _view_box(job: CutJobResult) -> dict[str, float]:
    bbox = job.view_bbox
    min_x = float(bbox["min_x"])
    max_x = float(bbox["max_x"])
    min_y = float(bbox["min_y"])
    max_y = float(bbox["max_y"])
    if max_x - min_x < MIN_VIEW_MM:
        center = (min_x + max_x) / 2
        min_x = center - MIN_VIEW_MM / 2
        max_x = center + MIN_VIEW_MM / 2
    if max_y - min_y < MIN_VIEW_MM:
        center = (min_y + max_y) / 2
        min_y = center - MIN_VIEW_MM / 2
        max_y = center + MIN_VIEW_MM / 2
    return {"min_x": min_x, "min_y": min_y, "max_x": max_x, "max_y": max_y}


def _scale(view: dict[str, float]) -> float:
    width = max(view["max_x"] - view["min_x"], MIN_VIEW_MM)
    height = max(view["max_y"] - view["min_y"], MIN_VIEW_MM)
    return max(0.2, min(6.0, MAX_DRAWING_PX / max(width, height)))


def _blank(width: int, height: int) -> list[bytearray]:
    row = bytearray()
    row.extend(BACKGROUND * width)
    return [bytearray(row) for _ in range(height)]


def _draw_axes(canvas: list[bytearray], view: dict[str, float], scale: float) -> None:
    origin = _to_pixel(view, scale, 0, 0)
    axis_length_mm = min(50.0, max(10.0, (view["max_x"] - view["min_x"]) * 0.15))
    x_axis = _to_pixel(view, scale, axis_length_mm, 0)
    y_axis = _to_pixel(view, scale, 0, axis_length_mm)
    _draw_line(canvas, origin, x_axis, AXIS_X, thickness=2)
    _draw_line(canvas, origin, y_axis, AXIS_Y, thickness=2)
    _draw_disc(canvas, origin, 4, ORIGIN)


def _draw_segment(canvas: list[bytearray], view: dict[str, float], scale: float, segment: PathSegment, color: tuple[int, int, int], thickness: int) -> None:
    start = _to_pixel(view, scale, segment.start.x, segment.start.y)
    end = _to_pixel(view, scale, segment.end.x, segment.end.y)
    _draw_line(canvas, start, end, color, thickness)


def _to_pixel(view: dict[str, float], scale: float, x: float, y: float) -> tuple[int, int]:
    px = int(round(MARGIN_PX + (x - view["min_x"]) * scale))
    py = int(round(MARGIN_PX + (view["max_y"] - y) * scale))
    return px, py


def _draw_line(canvas: list[bytearray], start: tuple[int, int], end: tuple[int, int], color: tuple[int, int, int], thickness: int = 1) -> None:
    x0, y0 = start
    x1, y1 = end
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    error = dx + dy
    while True:
        _draw_disc(canvas, (x0, y0), max(0, thickness - 1), color)
        if x0 == x1 and y0 == y1:
            break
        twice_error = 2 * error
        if twice_error >= dy:
            error += dy
            x0 += sx
        if twice_error <= dx:
            error += dx
            y0 += sy


def _draw_disc(canvas: list[bytearray], center: tuple[int, int], radius: int, color: tuple[int, int, int]) -> None:
    cx, cy = center
    for y in range(cy - radius, cy + radius + 1):
        for x in range(cx - radius, cx + radius + 1):
            if (x - cx) * (x - cx) + (y - cy) * (y - cy) <= radius * radius:
                _set_pixel(canvas, x, y, color)


def _set_pixel(canvas: list[bytearray], x: int, y: int, color: tuple[int, int, int]) -> None:
    if y < 0 or y >= len(canvas) or x < 0 or x * 3 + 2 >= len(canvas[y]):
        return
    offset = x * 3
    canvas[y][offset : offset + 3] = bytes(color)


def _write_png(path: Path, canvas: list[bytearray]) -> None:
    height = len(canvas)
    width = len(canvas[0]) // 3 if height else 0
    raw = b"".join(b"\x00" + bytes(row) for row in canvas)
    chunks = [
        _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)),
        _chunk(b"IDAT", zlib.compress(raw, level=9)),
        _chunk(b"IEND", b""),
    ]
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"".join(chunks))


def _chunk(kind: bytes, data: bytes) -> bytes:
    checksum = binascii.crc32(kind + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", checksum)
