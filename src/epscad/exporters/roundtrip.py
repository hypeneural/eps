"""Independent ezdxf readback for emitted cutting geometry."""
from collections import Counter
from math import atan2,degrees,hypot,isfinite
import ezdxf

def _xy(p):
    return tuple(round(float(v),5) for v in (p[0],p[1]))

def _line(a,b):
    return tuple(sorted((_xy(a),_xy(b))))

def verify_roundtrip(job,path):
    try:
        doc=ezdxf.readfile(path)
        if doc.dxfversion!="AC1009" or doc.audit().has_errors:
            return False
        expected=Counter()
        actual=Counter()
        for cut in job.paths:
            for s in cut.segments:
                kind=s.kind.upper()
                a=(s.start.x,s.start.y)
                b=(s.end.x,s.end.y)
                if kind=="LINE":
                    key=_line(a,b)
                else:
                    c=(s.center.x,s.center.y)
                    r=round(hypot(a[0]-c[0],a[1]-c[1]),5)
                    key=(_xy(c),r)
                    if kind=="ARC":
                        angles=[round(degrees(atan2(p[1]-c[1],p[0]-c[0]))%360,5)%360 for p in (a,b)]
                        key+=tuple(angles if s.ccw else angles[::-1])
                expected[(kind,s.layer,key)]+=1
        for e in doc.modelspace():
            kind=e.dxftype()
            if kind=="LINE":
                if e.dxf.start.z!=0 or e.dxf.end.z!=0:
                    return False
                key=_line(e.dxf.start,e.dxf.end)
            elif kind in ("ARC","CIRCLE"):
                if e.dxf.center.z!=0 or not isfinite(e.dxf.radius) or e.dxf.radius<=0:
                    return False
                key=(_xy(e.dxf.center),round(e.dxf.radius,5))
                if kind=="ARC":
                    key+=(round(e.dxf.start_angle%360,5)%360,round(e.dxf.end_angle%360,5)%360)
            else:
                return False
            actual[(kind,e.dxf.layer,key)]+=1
        return bool(expected) and expected==actual
    except (ValueError,TypeError,AttributeError,OSError,ezdxf.DXFError):
        return False
