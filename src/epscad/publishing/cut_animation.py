"""Read-only visual projection of the exact private review TAP, not a controller."""
import hashlib
import math
from epscad.exporters.tap_simulator import parse_tap_modal

BANNER = b"(OFFLINE REVIEW ONLY - NOT APPROVED FOR MACHINE EXECUTION)\r\n"

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
    return {"schema": 1, "model": slug, "name": name, "tap_sha256": expected_sha,
            "units": "mm", "distance_mm": total, "bbox": parsed["metrics"]["bbox_mm"],
            "segments": segments, "wire_visualization": "schematic_parallel_pair",
            "physical_spacing_mm": None, "production_approved": False,
            "execution_authorized": False}
