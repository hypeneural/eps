"""Read-only publication candidate. Hashes bind human approval, not physical proof."""
import hashlib
import json
from epscad.loader import load_yaml, load_machine_profile
from epscad.build import build_job
from epscad.exporters.roundtrip import verify_roundtrip

def profile_hash(profile):
    data=json.dumps(profile,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode("utf-8")
    return hashlib.sha256(data).hexdigest()

def candidate_hashes(source,report,verified):
    from epscad.publishing.site import safe_file,digest
    dxf="03_cutpaths_r12.dxf"
    locked="05_project.locked.yaml"
    if report.get("production_status")!="production_released" or report.get("package_purpose")!="production" or report.get("unit")!="mm" or report.get("has_errors") is not False or report.get("gcode_enabled") is not False or not {dxf,locked}<=set(verified):
        raise ValueError("Not a verified production package")
    spec=load_yaml(safe_file(source,locked))
    if spec.get("machine",{}).get("profile")!="scara_hotwire_eps" or report.get("machine_profile")!="scara_hotwire_eps":
        raise ValueError("Test machine profile cannot be published for production")
    profile=load_machine_profile("scara_hotwire_eps")
    if profile.get("status")=="test_only" or profile.get("safety",{}).get("production_allowed") is False:
        raise ValueError("Machine profile explicitly disallows production")
    job=build_job(spec)
    if job.has_errors or job.production_status!="production_released" or not verify_roundtrip(job,safe_file(source,dxf)):
        raise ValueError("Released project fails current production gates or DXF readback")
    if spec.get("outputs",{}).get("dxf") is not True or job.metadata.get("tp40",{}).get("cut_mode")=="core_outline":
        raise ValueError("Project does not authorize machine-path DXF")
    return {"dxf_sha256":digest(safe_file(source,dxf).read_bytes()),
            "project_sha256":digest(safe_file(source,locked).read_bytes()),
            "profile_sha256":profile_hash(profile)}
