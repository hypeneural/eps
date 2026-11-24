"""Restricted local postprocessor, separate from legacy DXF package.
No defaults for machine behavior; not a CAM planner. Only one continuous LINE path.
"""
import hashlib
import json
import math

VERSION="mach3-linear-v1"
FLAGS=("io_mapping_confirmed","origin_confirmed","modal_state_confirmed",
       "thermal_parameters_confirmed","limits_confirmed","ordered_path_confirmed",
       "program_end_confirmed","starting_position_confirmed")
KEYS=set(FLAGS)|{"controller_profile","feed_mm_min","heat_s","dwell_value",
                 "dwell_unit","path_control","work_offset","machine_profile_sha256",
                 "max_heat_s","max_dwell_seconds"}

def sha(data): return hashlib.sha256(data).hexdigest()
def canonical(value): return json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")

def number(x,name,zero=False):
    if isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) or x<0 or (not zero and x==0):
        raise ValueError("Invalid "+name)
    return float(x)

ALLOWED_CUT_LAYERS={"CUT","CUT_OUTSIDE"}
ALLOWED_CUT_OPERATIONS={"cut","straight_cut","profile_cut","profile_2d","tp40_core"}

def ordered_points(job):
    if job.has_errors or job.unit!="mm" or job.process_type!="hotwire_2d" or len(job.paths)!=1:
        raise ValueError("Requires one validated continuous hotwire path")
    if (job.metadata or {}).get("tp40",{}).get("cut_mode")=="core_outline":
        raise ValueError("Reference outline mode cannot be exported as a cutting trajectory")
    path=job.paths[0]
    if not path.segments or path.operation not in ALLOWED_CUT_OPERATIONS:
        raise ValueError("Missing cut path")
    points=[]
    for s in path.segments:
        if s.kind!="LINE" or s.layer not in ALLOWED_CUT_LAYERS:
            raise ValueError("Only LINE CUT segments supported; arcs and reference geometry are blocked")
        a,b=[(number(p.x,"X",True),number(p.y,"Y",True)) for p in (s.start,s.end)]
        if s.start.z!=0 or s.end.z!=0 or a==b or (points and points[-1]!=a):
            raise ValueError("Nonplanar, zero or discontinuous path")
        if not points: points.append(a)
        points.append(b)
    if points[0]!=(0.,0.):
        raise ValueError("Path must start at confirmed work origin; no automatic positioning")
    return points

def render_tap(job,profile,contract):
    if job.production_status!="production_released" or job.machine_profile!="scara_hotwire_eps" or profile.get("profile_locked") is not True or profile.get("safety",{}).get("production_allowed") is not True:
        raise ValueError("Real machine and project production gates not confirmed")
    if set(contract)!=KEYS or not all(contract.get(k) is True for k in FLAGS):
        raise ValueError("Explicit reviewed Mach3 contract required")
    if contract["controller_profile"]!="CNC_V" or contract["machine_profile_sha256"]!=sha(canonical(profile)):
        raise ValueError("Mach3 profile approval mismatch")
    if contract["dwell_unit"] not in ("seconds","milliseconds") or contract["path_control"] not in ("G61","G64") or contract["work_offset"] not in ("G54","G55","G56","G57","G58","G59"):
        raise ValueError("Invalid confirmed modal settings")
    feed=number(contract["feed_mm_min"],"feed")
    if feed>number(profile["feed"]["default_xy_mm_min"],"profile feed"):
        raise ValueError("Feed exceeds confirmed profile")
    heat=number(contract["heat_s"],"heat")
    dwell=number(contract["dwell_value"],"dwell",True)
    dwell_seconds=dwell if contract["dwell_unit"]=="seconds" else dwell/1000
    if heat>number(contract["max_heat_s"],"confirmed heat limit") or dwell_seconds>number(contract["max_dwell_seconds"],"confirmed dwell limit",True):
        raise ValueError("Thermal settings exceed reviewed contract")
    points=ordered_points(job)
    xmax=number(profile["work_area"]["x_max"],"X limit")
    ymax=number(profile["work_area"]["y_max"],"Y limit")
    minimum=number(profile["hotwire"]["min_segment_mm"],"minimum segment")
    if any(x>xmax or y>ymax for x,y in points):
        raise ValueError("Path outside confirmed work area")
    # Reject quantization that changes continuity or minimum segment.
    q=[(round(x,4),round(y,4)) for x,y in points]
    if any(x>xmax or y>ymax for x,y in q) or any(math.dist(a,b)<minimum for a,b in zip(q,q[1:])):
        raise ValueError("Segment below confirmed minimum")
    # No homing, offset modification, rapid repositioning or automatic machine access.
    def word(value):
        s=f"{value:.8f}".rstrip("0").rstrip(".") or "0"
        if float(s)!=value:
            raise ValueError("Unsupported numeric precision")
        return s
    lines=["G21 G17 G90 G94 G40 G49 G80",contract["work_offset"],contract["path_control"],
           "S"+word(heat),"F"+word(feed),"M3","G4 P"+word(dwell)]
    # No implicit move to origin; operator must verify physical starting position.
    lines.extend("G1 X%.4f Y%.4f"%p for p in q[1:])
    lines.extend(["M5","M30"])
    payload=("\r\n".join("N%d %s"%((i+1)*5,line) for i,line in enumerate(lines))+"\r\n").encode("ascii")
    from epscad.exporters.tap_simulator import validate_candidate_tap
    validate_candidate_tap(payload,points,profile,contract)
    return payload

def approval_hashes(job,profile,contract):
    data=render_tap(job,profile,contract)
    return data,{"tap_sha256":sha(data),"tap_contract_sha256":sha(canonical(contract)),
                 "tap_path_sha256":sha(canonical(ordered_points(job))),"tap_postprocessor":VERSION}
