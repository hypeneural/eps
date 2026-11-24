"""Parametric nominal profile with microgrooves; no machine-path generation."""
from math import isfinite
from shapely.geometry import LineString, Polygon
from epscad.geometry.roof import RoofGeometry
from epscad.schema import Point
from epscad.templates.tp40 import offset_polyline

def positive(value, name):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not isfinite(value) or value<=0:
        raise ValueError(f"{name} must be positive and finite")
    return float(value)

def build_reference(geometry, *, length=1000, gauge=.43):
    keys=("pitch_mm","ramp_run_mm","rib_height_mm","crest_span_mm","valley_width_mm","groove_width_mm","groove_depth_mm","min_thickness_mm")
    p,r,h,c,v,g,d,t=[positive(geometry[k],k) for k in keys]
    n=geometry["periods"]
    if isinstance(n,bool) or not isinstance(n,int) or not 1<=n<=100:
        raise ValueError("periods must be an integer 1..100")
    if geometry.get("phase")!="ascending_ramp_first" or abs(2*r+c+v-p)>1e-7 or g>=c or d>=h:
        raise ValueError("Incompatible TP40 module dimensions or phase")
    length=positive(length,"length")
    gauge=positive(gauge,"gauge")
    if gauge>5 or 2*gauge>=min(g,d,(c-g)/2):
        raise ValueError("Reference metal gauge too large for microgroove")
    shoulder=(c-g)/2
    points=[(0.,0.)]
    for i in range(n):
        x=i*p
        points.extend([(x+r,h),(x+r+shoulder,h),(x+r+shoulder,h-d),
                       (x+r+shoulder+g,h-d),(x+r+shoulder+g,h),
                       (x+r+c,h),(x+2*r+c,0.),((i+1)*p,0.)])
    width=n*p
    top=h+t
    interface=LineString(points)
    if not interface.is_simple:
        raise ValueError("Invalid reference interface")
    bottom=-max(1.,gauge*2)
    below=offset_polyline([Point(x,y) for x,y in points],-gauge)
    core=Polygon(points+[(width,top),(0.,top)])
    complement=Polygon(points+[(width,bottom),(0.,bottom)])
    metal=Polygon(points+[(q.x,q.y) for q in reversed(below)])
    if any(not q.is_valid or q.area<=0 for q in (core,complement,metal)) or core.intersection(metal).area>1e-5:
        raise ValueError("Invalid nominal solids")
    expected=n*(p*top-h*(r+c)+g*d)
    if abs(core.area-expected)>1e-5:
        raise ValueError("Analytical section area mismatch")
    return RoofGeometry(core,complement,metal,length,gauge), {
        "status":"draft","machine_export_allowed":False,"production_confirmed":False,
        "profile_points_mm":points,"width_mm":width,"height_mm":top,"min_thickness_mm":t,
        "area_mm2":core.area,"volume_mm3":core.area*length,"interface_length_mm":interface.length,
        "extrusion_length_mm_assumed":length,"metal_gauge_mm_assumed":gauge,"complement_bottom_mm_assumed":bottom}
