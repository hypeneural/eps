"""Nominal solids derived from the same TP40 profile used by the cut template."""
from dataclasses import dataclass
from math import isfinite
from shapely.geometry import Polygon
from epscad.templates.tp40 import parse_params, profile_points, offset_polyline

@dataclass(frozen=True)
class RoofGeometry:
    core: Polygon
    complement: Polygon
    metal: Polygon
    length_mm: float
    metal_thickness_mm: float

def build_roof_geometry(spec):
    params, errors = parse_params(spec)
    if params is None or errors:
        raise ValueError("Invalid TP40 geometry")
    stock = spec["material"]["stock"]
    top = float(stock["height_y"])
    length = float(stock["thickness_z"])
    gauge = float(spec["cut"]["template_params"].get("metal_thickness_mm", 0.43))
    if not all(isfinite(v) and v > 0 for v in (length, gauge)) or gauge > 5:
        raise ValueError("Invalid extrusion length or metal gauge")
    points = profile_points(params, top)
    line = [(p.x, p.y) for p in points]
    below = [(p.x, p.y) for p in offset_polyline(points, -gauge)]
    x0, x1 = line[0][0], line[-1][0]
    core = Polygon(line + [(x1, top), (x0, top)])
    complement = Polygon(line + [(x1, 0), (x0, 0)])
    metal = Polygon(line + below[::-1])
    for name, shape in (("core", core), ("complement", complement), ("metal", metal)):
        if not shape.is_valid or shape.area <= 0:
            raise ValueError(f"Invalid {name} polygon")
    if core.intersection(metal).area > 1e-6:
        raise ValueError("Metal intersects nominal EPS")
    return RoofGeometry(core, complement, metal, length, gauge)
