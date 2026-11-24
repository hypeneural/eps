from __future__ import annotations

from typing import Any

from epscad.schema import ValidationMessage
from epscad.validators.common import DXF_STATUSES, is_production_like


def validate_tp40(spec: dict[str, Any]) -> list[ValidationMessage]:
    """Gate do template TP40: medidas nominais nao liberam DXF."""
    cut = spec.get("cut", {}) or {}
    if cut.get("template") != "tp40_core":
        return []
    params = cut.get("template_params", {}) or {}
    if params.get("profile_confirmed") is True:
        return []
    status = str(spec.get("project", {}).get("status", "draft"))
    blocking = status in DXF_STATUSES or is_production_like(spec)
    return [
        ValidationMessage(
            "error" if blocking else "warning",
            "tp40_profile_not_confirmed",
            "TP40 profile dimensions are nominal; measure the real panel and set profile_confirmed=true before releasing DXF",
            "cut.template_params.profile_confirmed",
        )
    ]
