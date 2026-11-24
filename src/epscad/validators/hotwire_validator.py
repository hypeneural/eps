from __future__ import annotations

from typing import Any

from epscad.schema import ValidationMessage
from epscad.validators.common import as_number, get_path, is_production_like


def validate_hotwire(spec: dict[str, Any]) -> list[ValidationMessage]:
    messages: list[ValidationMessage] = []
    production_like = is_production_like(spec)
    required_paths = [
        "process.hotwire.wire_mode",
        "process.hotwire.wire_count",
        "process.hotwire.effective_kerf_mm",
        "process.hotwire.min_segment_mm",
        "process.hotwire.min_radius_mm",
        "process.feed.xy_mm_min",
        "process.feed.slow_curve_mm_min",
    ]
    for path in required_paths:
        value = get_path(spec, path)
        if value in (None, ""):
            messages.append(ValidationMessage("error", "hotwire_required_field_missing", f"{path} is required", path))
        elif value == "confirmar" and production_like:
            messages.append(ValidationMessage("error", "hotwire_confirmar_blocks_production", f"{path} must be confirmed", path))
    if production_like:
        messages.extend(_validate_production_numbers(spec))
    return messages


def _validate_production_numbers(spec: dict[str, Any]) -> list[ValidationMessage]:
    messages: list[ValidationMessage] = []
    wire_count = get_path(spec, "process.hotwire.wire_count")
    if not isinstance(wire_count, int) or isinstance(wire_count, bool) or wire_count <= 0:
        messages.append(
            ValidationMessage(
                "error",
                "hotwire_wire_count_invalid",
                "wire_count must be an integer > 0 for production-like states",
                "process.hotwire.wire_count",
            )
        )

    positive_fields = [
        "process.hotwire.effective_kerf_mm",
        "process.hotwire.min_segment_mm",
        "process.feed.xy_mm_min",
        "process.feed.slow_curve_mm_min",
    ]
    non_negative_fields = ["process.hotwire.min_radius_mm"]
    for path in positive_fields:
        value = as_number(get_path(spec, path))
        if value is None or value <= 0:
            messages.append(
                ValidationMessage(
                    "error",
                    "hotwire_numeric_required_for_production",
                    f"{path} must be numeric > 0 for production-like states",
                    path,
                )
            )
    for path in non_negative_fields:
        value = as_number(get_path(spec, path))
        if value is None or value < 0:
            messages.append(
                ValidationMessage(
                    "error",
                    "hotwire_numeric_required_for_production",
                    f"{path} must be numeric >= 0 for production-like states",
                    path,
                )
            )
    return messages
