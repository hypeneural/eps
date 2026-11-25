"""Independent modal Mach3 TAP parser, candidate readback validator, and offline trajectory simulator.

Read-only analytical/visual tool. Never executes CNC hardware, never alters controller settings,
and never approves a program for physical fabrication.
"""
from collections import Counter
from decimal import Decimal
import hashlib
import math
from pathlib import Path
import re
from PIL import Image, ImageDraw

WORD = re.compile(r"([A-Z])([+-]?(?:\d+(?:\.\d*)?|\.\d+))")
ALLOWED_G = {
    Decimal(x)
    for x in ("0", "1", "2", "3", "4", "17", "20", "21", "40", "49", "54", "55", "56", "57", "58", "59", "61", "64", "80", "90", "91", "90.1", "91.1", "94")
}
ALLOWED_M = {Decimal(x) for x in ("3", "5", "30")}


def _arc_points(start, end, center, cw, steps=24):
    """Discretize a planar XY arc for offline geometry metrics and visual preview."""
    x0, y0 = start
    x1, y1 = end
    cx, cy = center
    r0 = math.hypot(x0 - cx, y0 - cy)
    r1 = math.hypot(x1 - cx, y1 - cy)
    if r0 < 1e-6 or abs(r0 - r1) > max(0.25, 0.02 * max(r0, r1)):
        raise ValueError(f"Inconsistent arc radii r0={r0:.4f} r1={r1:.4f} for center {center}")
    a0 = math.atan2(y0 - cy, x0 - cx)
    a1 = math.atan2(y1 - cy, x1 - cx)
    if cw:
        sweep = a0 - a1
        if sweep <= 1e-9:
            sweep += 2 * math.pi
        angles = [a0 - sweep * (i / steps) for i in range(steps + 1)]
    else:
        sweep = a1 - a0
        if sweep <= 1e-9:
            sweep += 2 * math.pi
        angles = [a0 + sweep * (i / steps) for i in range(steps + 1)]
    pts = [(cx + r0 * math.cos(a), cy + r0 * math.sin(a)) for a in angles]
    pts[0] = start
    pts[-1] = end
    return pts, r0 * sweep


def _collinear_overlap_mm(segments, tol=1e-3):
    """Measure total collinear overlap length across linear segments (e.g. repeated Y=0 passes)."""
    # Group horizontal/vertical/general segments by normalized line equation (nx, ny, d)
    groups = {}
    for seg in segments:
        if seg["kind"] != "LINE":
            continue
        x0, y0 = seg["start"]
        x1, y1 = seg["end"]
        dx, dy = x1 - x0, y1 - y0
        length = math.hypot(dx, dy)
        if length <= tol:
            continue
        # Unit direction with canonical sign
        ux, uy = dx / length, dy / length
        if ux < -tol or (abs(ux) <= tol and uy < 0):
            ux, uy = -ux, -uy
        nx, ny = -uy, ux
        dist = nx * x0 + ny * y0
        key = (round(nx, 3), round(ny, 3), round(dist, 2))
        t0 = ux * x0 + uy * y0
        t1 = ux * x1 + uy * y1
        groups.setdefault(key, []).append((min(t0, t1), max(t0, t1)))

    overlap = 0.0
    overlapped_intervals = []
    for key, ivs in groups.items():
        if len(ivs) < 2:
            continue
        raw_sum = sum(b - a for a, b in ivs)
        merged = []
        for a, b in sorted(ivs):
            if not merged or a > merged[-1][1] + tol:
                merged.append([a, b])
            else:
                merged[-1][1] = max(merged[-1][1], b)
        union_sum = sum(b - a for a, b in merged)
        diff = max(0.0, raw_sum - union_sum)
        if diff > tol:
            overlap += diff
            overlapped_intervals.append({"line": key, "overlap_mm": round(diff, 3)})
    return round(overlap, 3), overlapped_intervals


def parse_tap_modal(data, *, default_ij_mode="incremental"):
    """Independently interpret modal Mach3 G-code state without executing machine control."""
    if isinstance(data, str):
        data = data.encode("ascii")
    if len(data) > 2_000_000:
        raise ValueError("TAP exceeds modal parser limit")
    if default_ij_mode not in ("incremental", "absolute"):
        raise ValueError("default_ij_mode must be 'incremental' or 'absolute'")

    codes = Counter()
    warnings = []
    blocks = 0
    previous_n = -1

    # Active modal state
    units = None
    plane = None
    distance_mode = None
    ij_mode = None
    motion = None
    path_control = None
    work_offset = None
    feed_mode = None
    feed = None
    spindle = None
    dwells = []
    m_sequence = []
    grouped_m_blocks = 0
    omitted_axis_moves = 0
    rapid_moves = 0
    arc_moves = 0

    x = 0.0
    y = 0.0
    z = 0.0
    segments = []
    all_pts = []

    for raw in data.decode("ascii").splitlines():
        line = re.sub(r"\s+", "", raw.upper())
        if not line:
            continue
        words = WORD.findall(line)
        if "".join(a + b for a, b in words) != line or not words or words[0][0] != "N":
            raise ValueError("Unsupported block syntax: " + raw)
        n_val = Decimal(words[0][1])
        if n_val != int(n_val) or n_val <= previous_n:
            raise ValueError("Invalid line numbering")
        previous_n = n_val
        blocks += 1

        blk_g = []
        blk_m = []
        coords = {}
        for a, b in words[1:]:
            v = Decimal(b)
            if a == "G":
                if v not in ALLOWED_G:
                    raise ValueError(f"Unsupported G-code G{b}")
                key = "G" + (str(v.normalize()) if v < 10 else format(v, "f"))
                codes[key] += 1
                blk_g.append(v)
                if v in (Decimal("0"), Decimal("1"), Decimal("2"), Decimal("3")):
                    motion = int(v)
                elif v == Decimal("17"):
                    plane = "G17"
                elif v == Decimal("20"):
                    units = "inch"
                elif v == Decimal("21"):
                    units = "mm"
                elif v == Decimal("90"):
                    distance_mode = "G90"
                elif v == Decimal("91"):
                    distance_mode = "G91"
                elif v == Decimal("90.1"):
                    ij_mode = "G90.1"
                elif v == Decimal("91.1"):
                    ij_mode = "G91.1"
                elif v in (Decimal("61"), Decimal("64")):
                    path_control = f"G{int(v)}"
                elif v in (Decimal("54"), Decimal("55"), Decimal("56"), Decimal("57"), Decimal("58"), Decimal("59")):
                    work_offset = f"G{int(v)}"
                elif v == Decimal("94"):
                    feed_mode = "G94"
            elif a == "M":
                if v not in ALLOWED_M:
                    raise ValueError(f"Unsupported M-code M{b}")
                key = f"M{int(v)}"
                codes[key] += 1
                blk_m.append(int(v))
                m_sequence.append(int(v))
            elif a == "F":
                feed = float(v)
            elif a == "S":
                spindle = float(v)
            elif a in ("X", "Y", "Z", "I", "J", "P"):
                if a == "Z" and v != 0:
                    raise ValueError("Nonzero Z unsupported")
                coords[a] = float(v)
            else:
                raise ValueError(f"Unsupported word {a}{b}")

        if len(blk_m) > 1:
            grouped_m_blocks += 1

        if Decimal("4") in blk_g:
            if "P" not in coords:
                raise ValueError("G4 dwell missing P parameter")
            dwells.append(coords["P"])

        has_xy = any(k in coords for k in ("X", "Y", "I", "J"))
        if has_xy:
            if motion is None:
                raise ValueError("Axis coordinates without active motion mode")
            if ("X" in coords) ^ ("Y" in coords):
                omitted_axis_moves += 1
            if distance_mode == "G91":
                nx = x + coords.get("X", 0.0)
                ny = y + coords.get("Y", 0.0)
            else:
                nx = coords.get("X", x)
                ny = coords.get("Y", y)
            start = (round(x, 6), round(y, 6))
            end = (round(nx, 6), round(ny, 6))
            if not all_pts:
                all_pts.append(start)
            if motion == 0:
                rapid_moves += 1
                length = math.hypot(end[0] - start[0], end[1] - start[1])
                if length > 1e-9:
                    segments.append({"block": int(n_val), "kind": "RAPID", "start": start, "end": end, "points": [start, end], "length_mm": round(length, 4), "backtrack_x": end[0] < start[0] - 1e-4})
                    all_pts.append(end)
            elif motion == 1:
                length = math.hypot(end[0] - start[0], end[1] - start[1])
                if length > 1e-9:
                    segments.append({"block": int(n_val), "kind": "LINE", "start": start, "end": end, "points": [start, end], "length_mm": round(length, 4), "backtrack_x": end[0] < start[0] - 1e-4})
                    all_pts.append(end)
            elif motion in (2, 3):
                arc_moves += 1
                eff_ij = ij_mode or ("G91.1" if default_ij_mode == "incremental" else "G90.1")
                ci = coords.get("I", 0.0)
                cj = coords.get("J", 0.0)
                center = (start[0] + ci, start[1] + cj) if eff_ij == "G91.1" else (ci, cj)
                pts, arc_len = _arc_points(start, end, center, cw=(motion == 2))
                segments.append({
                    "block": int(n_val),
                    "kind": "ARC_CW" if motion == 2 else "ARC_CCW",
                    "start": start,
                    "end": end,
                    "center": (round(center[0], 4), round(center[1], 4)),
                    "points": pts,
                    "length_mm": round(arc_len, 4),
                    "backtrack_x": end[0] < start[0] - 1e-4,
                })
                all_pts.extend(pts[1:])
            x, y = nx, ny

    if not blocks:
        raise ValueError("Empty TAP")

    if distance_mode is None:
        warnings.append("implicit_distance_mode_missing_G90")
    if arc_moves > 0 and ij_mode is None:
        warnings.append("implicit_ij_mode_on_arcs")
    if grouped_m_blocks > 0:
        warnings.append("grouped_m_codes_in_single_block")
    if rapid_moves > 0:
        warnings.append("rapid_g0_moves_present")

    overlap_mm, overlap_details = _collinear_overlap_mm(segments)
    if overlap_mm > 0.01:
        warnings.append("collinear_overlapped_passes")
    backtracks = sum(1 for s in segments if s["backtrack_x"])
    if backtracks > 0:
        warnings.append("negative_x_return_moves")

    xs = [p[0] for p in all_pts] or [0.0]
    ys = [p[1] for p in all_pts] or [0.0]
    seg_lens = [s["length_mm"] for s in segments] or [0.0]

    return {
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
        "blocks": blocks,
        "codes": dict(codes),
        "modal": {
            "units": units,
            "plane": plane,
            "distance_mode": distance_mode,
            "ij_mode": ij_mode,
            "path_control": path_control,
            "work_offset": work_offset,
            "feed_mode": feed_mode,
            "feed_mm_min": feed,
            "spindle_s": spindle,
            "dwells": dwells,
            "m_sequence": m_sequence,
        },
        "metrics": {
            "segment_count": len(segments),
            "arc_count": arc_moves,
            "rapid_count": rapid_moves,
            "omitted_axis_moves": omitted_axis_moves,
            "grouped_m_blocks": grouped_m_blocks,
            "backtrack_x_count": backtracks,
            "collinear_overlap_mm": overlap_mm,
            "total_length_mm": round(sum(seg_lens), 4),
            "min_segment_mm": round(min(seg_lens), 4),
            "max_segment_mm": round(max(seg_lens), 4),
            "start_mm": list(segments[0]["start"]) if segments else [0.0, 0.0],
            "end_mm": list(segments[-1]["end"]) if segments else [0.0, 0.0],
            "bbox_mm": {
                "x_min": round(min(xs), 4),
                "x_max": round(max(xs), 4),
                "y_min": round(min(ys), 4),
                "y_max": round(max(ys), 4),
                "width": round(max(xs) - min(xs), 4),
                "height": round(max(ys) - min(ys), 4),
            },
        },
        "overlap_details": overlap_details,
        "warnings": warnings,
        "segments": segments,
        "production_approved": False,
    }


def validate_candidate_tap(tap_bytes, expected_points, profile, contract):
    """Independent modal readback validator for newly generated Mach3 linear TAP candidates."""
    parsed = parse_tap_modal(tap_bytes)
    modal = parsed["modal"]
    metrics = parsed["metrics"]
    if modal["units"] != "mm" or modal["plane"] != "G17" or modal["distance_mode"] != "G90" or modal["feed_mode"] != "G94":
        raise ValueError("Candidate TAP missing mandatory safe-start modal headers")
    if parsed["codes"].get("G40", 0) < 1 or parsed["codes"].get("G49", 0) < 1 or parsed["codes"].get("G80", 0) < 1:
        raise ValueError("Candidate TAP missing G40/G49/G80 safety cancels")
    if modal["work_offset"] != contract["work_offset"] or modal["path_control"] != contract["path_control"]:
        raise ValueError("Candidate TAP modal offset/path control mismatch")
    if modal["m_sequence"] != [3, 5, 30] or metrics["grouped_m_blocks"] != 0:
        raise ValueError("Candidate TAP must emit clean separate M3 -> M5 -> M30 sequence")
    if metrics["arc_count"] != 0 or metrics["rapid_count"] != 0:
        raise ValueError("Candidate TAP must contain only linear G1 moves")
    if len(modal["dwells"]) != 1 or abs(modal["dwells"][0] - float(contract["dwell_value"])) > 1e-6:
        raise ValueError("Candidate TAP dwell mismatch")
    if abs((modal["feed_mm_min"] or 0.0) - float(contract["feed_mm_min"])) > 1e-6 or abs((modal["spindle_s"] or 0.0) - float(contract["heat_s"])) > 1e-6:
        raise ValueError("Candidate TAP feed/heat mismatch")

    expected = [(round(x, 4), round(y, 4)) for x, y in expected_points]
    rebuilt = [tuple(parsed["segments"][0]["start"])] + [tuple(s["end"]) for s in parsed["segments"]] if parsed["segments"] else []
    if len(rebuilt) != len(expected):
        raise ValueError(f"Candidate TAP readback point count mismatch: {len(rebuilt)} vs {len(expected)}")
    for a, b in zip(rebuilt, expected):
        if math.hypot(a[0] - b[0], a[1] - b[1]) > 1e-4:
            raise ValueError(f"Candidate TAP readback coordinate drift: {a} vs {b}")

    xmax = float(profile["work_area"]["x_max"])
    ymax = float(profile["work_area"]["y_max"])
    bbox = metrics["bbox_mm"]
    if bbox["x_min"] < -1e-6 or bbox["y_min"] < -1e-6 or bbox["x_max"] > xmax + 1e-6 or bbox["y_max"] > ymax + 1e-6:
        raise ValueError("Candidate TAP exceeds confirmed work area on readback")
    if metrics["min_segment_mm"] + 1e-6 < float(profile["hotwire"]["min_segment_mm"]):
        raise ValueError("Candidate TAP segment below confirmed minimum on readback")
    return parsed


def render_tap_simulation(parsed, out_png, *, title="", stock_bbox=None):
    """Render an offline 2D engineering simulation PNG of the parsed TAP trajectory."""
    out_png = Path(out_png)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    W, H = 1400, 680
    img = Image.new("RGB", (W, H), "#f7f9fa")
    draw = ImageDraw.Draw(img)

    # Header bar
    draw.rectangle([0, 0, W, 56], fill="#1b2730")
    draw.rectangle([0, 53, W, 56], fill="#cc240c")
    label = (title or f"Simulacao TAP ({parsed['sha256'][:12]})").replace("—", "-").replace("–", "-")
    label_safe = label.encode("latin-1", "replace").decode("latin-1")
    draw.text((22, 18), f"EPS CutPlan | {label_safe}", fill="#ffffff")
    draw.text((W - 390, 18), "SIMULACAO OFFLINE - NAO HOMOLOGADO", fill="#ffd27d")

    # Plot canvas
    px0, py0, px1, py1 = 76, 84, W - 40, H - 116
    draw.rectangle([px0, py0, px1, py1], fill="#ffffff", outline="#cbd5db", width=2)

    bbox = parsed["metrics"]["bbox_mm"]
    xmin, xmax = bbox["x_min"], bbox["x_max"]
    ymin, ymax = bbox["y_min"], bbox["y_max"]
    if stock_bbox:
        xmin = min(xmin, stock_bbox[0])
        ymin = min(ymin, stock_bbox[1])
        xmax = max(xmax, stock_bbox[2])
        ymax = max(ymax, stock_bbox[3])
    span_x = max(xmax - xmin, 10.0)
    span_y = max(ymax - ymin, 10.0)
    pad_x = span_x * 0.05
    pad_y = span_y * 0.14
    vx0, vx1 = xmin - pad_x, xmax + pad_x
    vy0, vy1 = ymin - pad_y, ymax + pad_y

    # Preserve readable aspect ratio (cap extreme distortion for 4000x80 slabs while keeping profile visible)
    avail_w = px1 - px0 - 20
    avail_h = py1 - py0 - 20
    sx = avail_w / (vx1 - vx0)
    sy = avail_h / (vy1 - vy0)
    if sy > sx * 3.5:
        sy = sx * 3.5
    elif sx > sy * 3.5:
        sx = sy * 3.5
    cx_w = (vx0 + vx1) / 2.0
    cy_w = (vy0 + vy1) / 2.0
    cx_p = (px0 + px1) / 2.0
    cy_p = (py0 + py1) / 2.0

    def to_px(x, y):
        return (cx_p + (x - cx_w) * sx, cy_p - (y - cy_w) * sy)

    # Grid lines
    for i in range(6):
        gx = xmin + (xmax - xmin) * i / 5.0
        px, _ = to_px(gx, ymin)
        if px0 <= px <= px1:
            draw.line([(px, py0), (px, py1)], fill="#eef2f4", width=1)
            draw.text((px - 18, py1 + 6), f"{gx:.0f}", fill="#51656d")
    for j in range(5):
        gy = ymin + (ymax - ymin) * j / 4.0
        _, py = to_px(xmin, gy)
        if py0 <= py <= py1:
            draw.line([(px0, py), (px1, py)], fill="#eef2f4", width=1)
            draw.text((14, py - 6), f"{gy:.0f}", fill="#51656d")

    if stock_bbox:
        a = to_px(stock_bbox[0], stock_bbox[3])
        b = to_px(stock_bbox[2], stock_bbox[1])
        draw.rectangle([a[0], a[1], b[0], b[1]], outline="#9aaab3", width=2)

    # Draw trajectory segments
    for seg in parsed["segments"]:
        pts = [to_px(x, y) for x, y in seg["points"]]
        if len(pts) < 2:
            continue
        if seg["kind"] in ("ARC_CW", "ARC_CCW"):
            color = "#6b3fa0"
            width = 3
        elif seg["backtrack_x"]:
            color = "#cc240c"
            width = 3
        elif abs(seg["end"][0] - seg["start"][0]) <= 1e-4:
            color = "#2b7a78"
            width = 2
        else:
            color = "#155875"
            width = 3
        draw.line(pts, fill=color, width=width)
        # Direction arrowhead at midpoint for longer segments
        if seg["length_mm"] >= 15.0:
            p0, p1 = pts[len(pts) // 2 - 1], pts[len(pts) // 2]
            adx, ady = p1[0] - p0[0], p1[1] - p0[1]
            alen = math.hypot(adx, ady)
            if alen >= 8.0:
                ux, uy = adx / alen, ady / alen
                mx, my = (p0[0] + p1[0]) / 2.0, (p0[1] + p1[1]) / 2.0
                tip = (mx + ux * 5, my + uy * 5)
                left = (mx - ux * 5 - uy * 4, my - uy * 5 + ux * 4)
                right = (mx - ux * 5 + uy * 4, my - uy * 5 - ux * 4)
                draw.polygon([tip, left, right], fill=color)

    # Start & End markers
    sp = to_px(*parsed["metrics"]["start_mm"])
    ep = to_px(*parsed["metrics"]["end_mm"])
    draw.ellipse([sp[0] - 6, sp[1] - 6, sp[0] + 6, sp[1] + 6], fill="#176442", outline="#ffffff", width=2)
    draw.ellipse([ep[0] - 6, ep[1] - 6, ep[0] + 6, ep[1] + 6], fill="#cc240c", outline="#ffffff", width=2)

    # Footer metrics & legend
    m = parsed["metrics"]
    md = parsed["modal"]
    draw.rectangle([0, H - 86, W, H], fill="#edf1f3")
    draw.line([(0, H - 86), (W, H - 86)], fill="#cbd5db", width=1)
    draw.text((22, H - 74), f"BBox XY: {bbox['width']:.1f} x {bbox['height']:.1f} mm  |  Comprimento: {m['total_length_mm']:.1f} mm  |  Segs: {m['segment_count']} (Arcos: {m['arc_count']})  |  Retornos -X: {m['backtrack_x_count']}  |  Sobreposicao: {m['collinear_overlap_mm']:.1f} mm", fill="#20323d")
    draw.text((22, H - 52), f"Modal: units={md['units']} dist={md['distance_mode'] or 'IMPLICITO'} ij={md['ij_mode'] or 'IMPLICITO'} F={md['feed_mm_min']} S={md['spindle_s']} P={md['dwells']} M={md['m_sequence']}  |  Avisos: {', '.join(parsed['warnings']) or 'nenhum'}", fill="#51656d")
    draw.text((22, H - 28), "Legenda: [Azul] Corte +X   [Verde-agua] Vertical   [Vermelho] Retorno -X   [Roxo] Arco G2/G3   [Bolinha verde] Inicio   [Bolinha vermelha] Fim", fill="#3d4e57")

    img.save(out_png, "PNG", optimize=True)
    return out_png
