"""Nominal slab filler cross-section, not a CAM path or structural specification."""
import math
from shapely.geometry import Polygon

def section(width, height, rebate_width, rebate_height):
    values=(width,height,rebate_width,rebate_height)
    if any(type(v) not in (int,float) or not math.isfinite(v) or v<=0 for v in values):
        raise ValueError("Finite positive section dimensions required")
    if 2*rebate_width>=width or rebate_height>=height:
        raise ValueError("Rebates consume the section")
    # Explicit design assumption: symmetric lower corner rebates, no bevel.
    # Catalog fit dimensions alone do not prove this orientation or geometry.
    points=[(rebate_width,0),(width-rebate_width,0),(width-rebate_width,rebate_height),
            (width,rebate_height),(width,height),(0,height),(0,rebate_height),(rebate_width,rebate_height)]
    poly=Polygon(points)
    if not poly.is_valid or not math.isclose(poly.area,width*height-2*rebate_width*rebate_height):
        raise ValueError("Invalid nominal section")
    return poly
