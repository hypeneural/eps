from __future__ import annotations

from typing import Any

from epscad.schema import CutJobResult
from epscad.templates import build_paths
from epscad.validators.geometry_validator import validate_geometry
from epscad.validators import validate_project


def build_job(spec: dict[str, Any]) -> CutJobResult:
    project = spec.get("project", {})
    machine = spec.get("machine", {})
    source = project.get("source", {})
    result = CutJobResult(
        project_id=str(project.get("id", "project")),
        project_name=str(project.get("name", "EPS project")),
        unit=str(project.get("unit", "mm")),
        machine_profile=str(machine.get("profile", "")),
        process_type=str(machine.get("process_type", "")),
        production_status=str(project.get("status", "draft")),
        source_kind=str(source.get("kind", "manual_text")),
    )
    result.validation.extend(validate_project(spec))
    paths, template_messages = build_paths(spec)
    result.paths = paths
    result.validation.extend(template_messages)
    result.validation.extend(validate_geometry(spec, paths))
    result.metadata.update(
        {
            "gcode_enabled": bool(spec.get("outputs", {}).get("gcode", {}).get("enabled", False)),
            "template": spec.get("cut", {}).get("template", ""),
            "origin": spec.get("cut", {}).get("origin", ""),
            "source": source,
        }
    )
    _assign_hotwire_metadata(spec, result)
    if result.metadata.get("template") == "tp40_core":
        from epscad.templates import tp40

        result.metadata["tp40"] = tp40.metadata(spec)
        result.reference_segments = tp40.reference_segments(spec)
    return result


def _assign_hotwire_metadata(spec: dict[str, Any], result: CutJobResult) -> None:
    if result.process_type != "hotwire_2d":
        return
    process = spec.get("process", {})
    hotwire = process.get("hotwire", {})
    feed = process.get("feed", {})
    result.metadata["hotwire"] = {
        "wire_mode": hotwire.get("wire_mode"),
        "wire_count": hotwire.get("wire_count"),
        "effective_kerf_mm": hotwire.get("effective_kerf_mm"),
        "lead_in_mm": hotwire.get("lead_in_mm"),
        "lead_out_mm": hotwire.get("lead_out_mm"),
        "min_segment_mm": hotwire.get("min_segment_mm"),
        "min_radius_mm": hotwire.get("min_radius_mm"),
        "feed_xy_mm_min": feed.get("xy_mm_min"),
        "slow_curve_mm_min": feed.get("slow_curve_mm_min"),
        "compensation_mode": spec.get("cut", {}).get("compensation"),
    }
