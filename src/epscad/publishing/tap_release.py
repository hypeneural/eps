"""Rebuild approved TAP from exact project and local machine contract. Never copy arbitrary TAP."""
from epscad.loader import load_yaml,load_machine_profile
from epscad.build import build_job
from epscad.exporters.mach3_tap import approval_hashes

def tap_candidate(source,report,verified,contract):
    from epscad.publishing.release import candidate_hashes
    from epscad.publishing.site import safe_file
    base=candidate_hashes(source,report,verified)
    spec=load_yaml(safe_file(source,"05_project.locked.yaml"))
    profile=load_machine_profile("scara_hotwire_eps")
    job=build_job(spec)
    data,hashes=approval_hashes(job,profile,contract)
    return data,{**base,**hashes}

def approved_tap(source,report,verified,release):
    if release.get("approved") is not True or release.get("tap_approved") is not True:
        raise ValueError("Explicit TAP approval required")
    data,expected=tap_candidate(source,report,verified,release.get("tap_contract",{}))
    if any(release.get(k)!=v for k,v in expected.items()):
        raise ValueError("TAP approval hashes mismatch")
    return data
