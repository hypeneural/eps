from __future__ import annotations

from typing import Any

from epscad.schema import ValidationMessage
from epscad.validators.common import as_number, get_path, is_production_like


def validate_router(spec: dict[str, Any]) -> list[ValidationMessage]:
    messages: list[ValidationMessage] = []
    production_like = is_production_like(spec)
    required_paths = [
        "tool.kind",
        "tool.diameter_mm",
        "tool.effective_kerf_mm",
        "tool.flute_length_mm",
        "tool.max_depth_per_pass_mm",
        "cut.depth.z_safe_mm",
        "cut.depth.final_depth_z",
        "cut.depth.pass_depth_mm",
        "cut.feed.xy_mm_min",
        "cut.feed.z_mm_min",
        "cut.feed.spindle_rpm",
    ]
    for path in required_paths:
        value = get_path(spec, path)
        if value in (None, ""):
            messages.append(ValidationMessage("error", "router_required_field_missing", f"{path} is required", path))
        elif value == "confirmar" and production_like:
            messages.append(ValidationMessage("error", "router_confirmar_blocks_production", f"{path} must be confirmed", path))

    pass_depth = as_number(get_path(spec, "cut.depth.pass_depth_mm"))
    max_pass = as_number(get_path(spec, "tool.max_depth_per_pass_mm"))
    if pass_depth is not None and max_pass is not None and pass_depth > max_pass:
        messages.append(ValidationMessage("error", "router_pass_depth_too_deep", "pass_depth_mm exceeds tool.max_depth_per_pass_mm", "cut.depth.pass_depth_mm"))

    final_depth = as_number(get_path(spec, "cut.depth.final_depth_z"))
    flute = as_number(get_path(spec, "tool.flute_length_mm"))
    if final_depth is not None and flute is not None and final_depth > flute:
        level = "error" if production_like else "warning"
        messages.append(ValidationMessage(level, "router_flute_length_short", "flute_length_mm is shorter than final_depth_z", "tool.flute_length_mm"))

    stock_z = as_number(get_path(spec, "material.stock.thickness_z"))
    if final_depth is not None and stock_z is not None and final_depth > stock_z:
        level = "error" if production_like else "warning"
        messages.append(ValidationMessage(level, "router_depth_exceeds_stock", "final_depth_z exceeds stock thickness_z", "cut.depth.final_depth_z"))
    return messages
