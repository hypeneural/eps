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
        source = spec.get("project", {}).get("source", {})
        status = spec.get("project", {}).get("status")
        if status in DXF_STATUSES and not (source.get("scale_confirmed") is True and source.get("dimensions_confirmed") is True):
            return [ValidationMessage("error", "tp40_dimensions_not_confirmed", "Confirm scale and dimensions before DXF", "project.source")]
        if status in DXF_STATUSES and params.get("cut_mode") == "core_outline":
            return [ValidationMessage("error", "tp40_outline_review_only", "Closed outline is visualization only", "cut.template_params.cut_mode")]
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
