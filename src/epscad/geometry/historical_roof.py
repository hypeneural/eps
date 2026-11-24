"""Review-only recovery of a roof cross-section from historical LINE drawings."""
from math import isfinite
from pathlib import Path
import ezdxf
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union
from epscad.geometry.roof import RoofGeometry
from epscad.templates.tp40 import offset_polyline
from epscad.schema import Point

def recover_upper_profile(path, *, left, right, top, length, gauge=0.43, tolerance=1e-5):
    """Explicit bounds in CAD coordinates. Upper envelope, NOT the original toolpath.
    Only horizontal/monotone-X LINE profiles with supported vertical transitions.
    No automatic selection of stock edges or production approval.
    """
    if not all(isfinite(v) for v in (left,right,top,length,gauge)) or right<=left or length<=0 or not 0<gauge<=5:
        raise ValueError("Invalid explicit review dimensions")
    doc=ezdxf.readfile(Path(path))
    entities=list(doc.modelspace())
    if not entities or any(e.dxftype()!="LINE" for e in entities):
        raise ValueError("Only LINE drawings are supported by this recovery method")
    if doc.header.get("$INSUNITS",0) not in (0,4):
        raise ValueError("Only mm or unspecified units; confirm units independently")
    lines=[]
    for e in entities:
        a,b=e.dxf.start,e.dxf.end
        if abs(a.z)>tolerance or abs(b.z)>tolerance:
            raise ValueError("Non-planar geometry")
        coords=[(round(p.x,5),round(p.y,5)) for p in (a,b)]
        if not all(isfinite(v) for p in coords for v in p):
            raise ValueError("Non-finite geometry")
        if coords[0]!=coords[1]:
            lines.append(LineString(coords))
    source=unary_union(lines)
    # Noded crossings and original vertices define intervals with a single linear upper envelope.
    parts=list(source.geoms) if hasattr(source,"geoms") else [source]
    spans=[(a,b) for part in parts for a,b in zip(part.coords,list(part.coords)[1:]) if abs(a[0]-b[0])>tolerance]
    xs=sorted({round(left,5),round(right,5)}|{p[0] for a,b in spans for p in (a,b) if left<p[0]<right})
    def y(a,b,x): return a[1]+(b[1]-a[1])*(x-a[0])/(b[0]-a[0])
    points=[]
    for x0,x1 in zip(xs,xs[1:]):
        mid=(x0+x1)/2
        candidates=[(a,b) for a,b in spans if min(a[0],b[0])-tolerance<=mid<=max(a[0],b[0])+tolerance]
        if not candidates:
            raise ValueError("Gap in source profile")
        a,b=max(candidates,key=lambda ab:y(*ab,mid))
        segment=[(x0,round(y(a,b,x0),5)),(x1,round(y(a,b,x1),5))]
        for pt in segment:
            if not points or pt!=points[-1]:
                points.append(pt)
    interface=LineString(points)
    if interface.difference(source.buffer(tolerance)).length>tolerance:
        raise ValueError("Recovered envelope contains unsupported transition")
    # Normalize the product only; retain source origin in the caller's report.
    base=min(p[1] for p in points)
    line=[(x-left,y-base) for x,y in points]
    ceiling=top-base
    if ceiling<=max(y for x,y in line):
        raise ValueError("Flat top must be above interface")
    # Provide nominal complementary material below the interface with a visible stock margin.
    # Margin is a visualization assumption, not a physical measurement.
    stock_bottom=-max(1.,gauge*2)
    below=offset_polyline([Point(x,y) for x,y in line],-gauge)
    core=Polygon(line+[(right-left,ceiling),(0,ceiling)])
    complement=Polygon(line+[(right-left,stock_bottom),(0,stock_bottom)])
    metal=Polygon(line+[(p.x,p.y) for p in reversed(below)])
    if any(not p.is_valid or p.area<=0 for p in (core,complement,metal)) or core.intersection(metal).area>1e-5:
        raise ValueError("Invalid nominal recovered solid")
    report={"status":"draft","source_dxf_version":doc.dxfversion,"source_units":doc.header.get("$INSUNITS",0),"source_entity_count":len(entities),"raw_line_length":sum(l.length for l in lines),"unique_line_length":source.length,"interface_length":interface.length,"source_bounds":{"left":left,"right":right,"top":top},"profile_points_mm":line,"width_mm":right-left,"height_mm":ceiling,"min_thickness_mm":ceiling-max(y for x,y in line),"area_mm2":core.area,"length_mm_assumed":length,"metal_gauge_mm_assumed":gauge,"complement_bottom_mm_assumed":stock_bottom,"production_confirmed":False}
    return RoofGeometry(core,complement,metal,length,gauge),report
