from __future__ import annotations

from typing import Any
from math import isfinite


PRODUCTION_STATUSES = {"cam_ready", "machine_tested", "production_released"}
DXF_STATUSES = {"validated_geometry", "cam_ready", "machine_tested", "production_released"}


def find_confirmar(value: Any, prefix: str = "") -> list[str]:
    if isinstance(value, dict):
        fields: list[str] = []
        for key, item in value.items():
            fields.extend(find_confirmar(item, f"{prefix}.{key}" if prefix else str(key)))
        return fields
    if isinstance(value, list):
        fields = []
        for index, item in enumerate(value):
            fields.extend(find_confirmar(item, f"{prefix}[{index}]"))
        return fields
    return [prefix] if value == "confirmar" else []


def get_path(data: dict[str, Any], dotted: str) -> Any:
    current: Any = data
    for part in dotted.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def as_number(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value) if isfinite(value) else None
    return None


def is_production_like(spec: dict[str, Any]) -> bool:
    status = str(spec.get("project", {}).get("status", "draft"))
    source = spec.get("project", {}).get("source", {})
    return status in PRODUCTION_STATUSES or bool(source.get("production_confirmed"))
