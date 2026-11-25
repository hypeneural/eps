"""Read-only visual projection of the exact private review TAP, not a controller."""
import hashlib
import math
from epscad.exporters.tap_simulator import parse_tap_modal

BANNER = b"(OFFLINE REVIEW ONLY - NOT APPROVED FOR MACHINE EXECUTION)\r\n"


def _same_pt(a, b, tol=1e-6):
    return abs(a[0] - b[0]) <= tol and abs(a[1] - b[1]) <= tol


def _dedup_ring(points, tol=1e-6):
    ring = []
    for p in points:
        pt = [round(float(p[0]), 4), round(float(p[1]), 4)]
        if not ring or not _same_pt(ring[-1], pt, tol):
            ring.append(pt)
    if len(ring) > 1 and _same_pt(ring[0], ring[-1], tol):
        ring.pop()
    return ring


def _poly_area(points):
    if len(points) < 3:
        return 0.0
    total = 0.0
    n = len(points)
    for i in range(n):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % n]
        total += x1 * y2 - x2 * y1
    return abs(total) * 0.5


def _demonstrable_regions(segments, bbox, overlap_mm):
    """Compute exact nominal XY bbox partition only when geometrically demonstrable."""
    base_fail = {"demonstrable": False, "physical_separation_confirmed": False}
    width = float(bbox.get("width", 0.0))
    height = float(bbox.get("height", 0.0))
    if not segments or width <= 1e-6 or height <= 1e-6:
        return {**base_fail, "reason": "degenerate_bbox"}
    if float(overlap_mm or 0.0) > 1e-6:
        return {**base_fail, "reason": "collinear_overlap"}

    pts = [list(segments[0]["start"])]
    for idx, seg in enumerate(segments):
        a, b = seg["start"], seg["end"]
        if idx > 0 and not _same_pt(segments[idx - 1]["end"], a, 1e-5):
            return {**base_fail, "reason": "discontinuous_path"}
        if b[0] < a[0] - 1e-6:
            return {**base_fail, "reason": "non_monotone_x"}
        pts.append(list(b))

    x_min, x_max = float(bbox["x_min"]), float(bbox["x_max"])
    y_min, y_max = float(bbox["y_min"]), float(bbox["y_max"])
    if abs(pts[0][0] - x_min) > 1e-4 or abs(pts[-1][0] - x_max) > 1e-4:
        return {**base_fail, "reason": "does_not_span_x_bounds"}

    # Trim boundary-only vertical runs on x=x_min and x=x_max so closed rings have no spikes.
    first_idx = 0
    while first_idx + 1 < len(pts) and abs(pts[first_idx + 1][0] - x_min) <= 1e-6:
        first_idx += 1
    last_idx = len(pts) - 1
    while last_idx - 1 > first_idx and abs(pts[last_idx - 1][0] - x_max) <= 1e-6:
        last_idx -= 1
    core = pts[first_idx : last_idx + 1]
    if len(core) < 2:
        return {**base_fail, "reason": "insufficient_span_vertices"}

    lower = _dedup_ring([[x_min, y_min]] + core + [[x_max, y_min]])
    upper = _dedup_ring([[x_min, y_max]] + core + [[x_max, y_max]])
    lower_area = _poly_area(lower)
    upper_area = _poly_area(upper)
    bbox_area = width * height
    if lower_area <= 1e-3 or upper_area <= 1e-3:
        return {**base_fail, "reason": "single_sided_profile"}
    if abs((lower_area + upper_area) - bbox_area) > max(0.05, bbox_area * 1e-4):
        return {**base_fail, "reason": "area_partition_mismatch"}

    return {
        "demonstrable": True,
        "kind": "x_monotone_bbox_partition",
        "lower_region_xy": lower,
        "upper_region_xy": upper,
        "lower_area_mm2": round(lower_area, 2),
        "upper_area_mm2": round(upper_area, 2),
        "bbox_area_mm2": round(bbox_area, 2),
        "physical_separation_confirmed": False,
    }


def animation_data(data, slug, name, expected_sha):
    if hashlib.sha256(data).hexdigest() != expected_sha or not data.startswith(BANNER):
        raise ValueError("Animation source is not the verified review TAP")
    # The strict parser consumes numbered blocks, not the review banner.
    parsed = parse_tap_modal(data[len(BANNER):])
    if parsed["modal"]["units"] != "mm" or parsed["modal"]["distance_mode"] != "G90":
        raise ValueError("Animation requires explicit absolute millimetres")
    if not parsed["segments"] or any(s["kind"] != "LINE" for s in parsed["segments"]):
        raise ValueError("Review animation V1 supports linear review TAPs only")
    segments, total = [], 0.0
    for seg in parsed["segments"]:
        a, b = seg["start"], seg["end"]
        length = math.dist(a, b)
        if not math.isfinite(length) or length <= 0:
            raise ValueError("Invalid animation segment")
        total += length
        segments.append({"block": seg["block"], "start": a, "end": b,
                         "end_distance_mm": total})
    bbox = parsed["metrics"]["bbox_mm"]
    overlap = parsed["metrics"].get("collinear_overlap_mm", 0.0)
    return {
        "schema": 1,
        "model": slug,
        "name": name,
        "tap_sha256": expected_sha,
        "units": "mm",
        "distance_mm": total,
        "bbox": bbox,
        "segments": segments,
        "regions": _demonstrable_regions(segments, bbox, overlap),
        "wire_visualization": "schematic_parallel_pair",
        "physical_spacing_mm": None,
        "production_approved": False,
        "execution_authorized": False,
    }
