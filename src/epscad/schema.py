from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Point:
    x: float
    y: float
    z: float = 0.0


@dataclass(frozen=True)
class PathSegment:
    kind: str
    start: Point
    end: Point
    layer: str = "CUT"
    # ARC: center + ccw (start->end counter-clockwise when ccw=True).
    # CIRCLE: center + start (a point on the circle).
    center: Point | None = None
    ccw: bool = True


@dataclass
class CutPath:
    id: str
    layer: str
    segments: list[PathSegment] = field(default_factory=list)
    operation: str = "cut"
    note: str = ""


@dataclass
class ValidationMessage:
    level: str
    code: str
    message: str
    path: str = ""


@dataclass
class CutJobResult:
    project_id: str
    project_name: str
    unit: str
    machine_profile: str
    process_type: str
    production_status: str
    source_kind: str
    paths: list[CutPath] = field(default_factory=list)
    validation: list[ValidationMessage] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    # Linhas de referencia (bloco EPS, linha nominal). Nunca vao para o DXF de corte.
    reference_segments: list[PathSegment] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(item.level == "error" for item in self.validation)

    @property
    def bbox(self) -> dict[str, float]:
        points: list[Point] = []
        for path in self.paths:
            for segment in path.segments:
                points.extend([segment.start, segment.end])
        return _bbox_of(points)

    @property
    def view_bbox(self) -> dict[str, float]:
        """BBox de cortes + referencias, usado apenas em preview/PDF."""
        points: list[Point] = []
        for path in self.paths:
            for segment in path.segments:
                points.extend([segment.start, segment.end])
        for segment in self.reference_segments:
            points.extend([segment.start, segment.end])
        return _bbox_of(points)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["bbox"] = self.bbox
        data["has_errors"] = self.has_errors
        return data


def _bbox_of(points: list[Point]) -> dict[str, float]:
    if not points:
        return {"min_x": 0.0, "min_y": 0.0, "max_x": 0.0, "max_y": 0.0, "width": 0.0, "height": 0.0}
    min_x = min(point.x for point in points)
    min_y = min(point.y for point in points)
    max_x = max(point.x for point in points)
    max_y = max(point.y for point in points)
    return {
        "min_x": round(min_x, 4),
        "min_y": round(min_y, 4),
        "max_x": round(max_x, 4),
        "max_y": round(max_y, 4),
        "width": round(max_x - min_x, 4),
        "height": round(max_y - min_y, 4),
    }


def project_schema_for_profile(profile: str) -> Path:
    root = Path(__file__).resolve().parents[2]
    if profile == "scara_hotwire_eps":
        return root / "schemas" / "project_hotwire.schema.json"
    if profile == "scara_hotwire_teste":
        return root / "schemas" / "project_hotwire.schema.json"
    raise ValueError(f"Unsupported machine.profile: {profile or '(empty)'}")
