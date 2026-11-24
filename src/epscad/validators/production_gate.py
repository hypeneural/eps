from __future__ import annotations

from typing import Any

from epscad.loader import load_machine_profile
from epscad.schema import ValidationMessage
from epscad.validators.common import find_confirmar, is_production_like


def validate_production_gates(spec: dict[str, Any]) -> list[ValidationMessage]:
    messages: list[ValidationMessage] = []
    production_like = is_production_like(spec)
    confirmar = find_confirmar(spec)
    if confirmar:
        level = "error" if production_like else "warning"
        messages.append(
            ValidationMessage(
                level,
                "confirmar_blocks_production",
                f"{len(confirmar)} field(s) are marked confirmar",
                ", ".join(confirmar[:10]),
            )
        )

    source = spec.get("project", {}).get("source", {})
    if source.get("kind") == "image_reference" and not (source.get("scale_confirmed") and source.get("dimensions_confirmed")):
        level = "error" if production_like else "warning"
        messages.append(
            ValidationMessage(
                level,
                "image_reference_locked",
                "image_reference without confirmed scale and dimensions is locked for production",
                "project.source",
            )
        )

    gcode = spec.get("outputs", {}).get("gcode", {})
    if gcode.get("enabled") is True:
        messages.append(ValidationMessage("error", "gcode_blocked_by_default", "G-code is experimental and disabled by default", "outputs.gcode.enabled"))

    if production_like:
        profile_id = str(spec.get("machine", {}).get("profile", ""))
        try:
            profile = load_machine_profile(profile_id)
        except FileNotFoundError:
            profile = {}
        if profile.get("profile_locked") is not True:
            messages.append(ValidationMessage("error", "profile_locked_required", "profile_locked=true is required for production", "machine.profile"))
        profile_confirmar = find_confirmar(profile)
        if profile_confirmar:
            messages.append(
                ValidationMessage(
                    "error",
                    "machine_profile_has_confirmar",
                    f"{len(profile_confirmar)} machine profile field(s) are marked confirmar",
                    ", ".join(profile_confirmar[:10]),
                )
            )
    return messages
