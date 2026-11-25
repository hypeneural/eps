"""Exercise the actual TAP link in a temporary synthetic test snapshot; never deploy."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from contextlib import ExitStack
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from epscad.loader import load_yaml
from epscad.build import build_job
from epscad.exporters import write_outputs
from epscad.exporters.mach3_tap import FLAGS,sha,canonical
from epscad.publishing.site import build_site,verified_source
from epscad.publishing.tap_release import tap_candidate
from epscad.publishing.deploy import local_inventory

def main():
    with tempfile.TemporaryDirectory(prefix="synthetic-tap-ci-") as d:
        root=Path(d)
        spec=load_yaml(ROOT/"projects/exemplos/001_linha_500mm.yaml")
        spec["project"]["status"]="production_released"
        spec["project"]["source"]["production_confirmed"]=True
        profile=load_yaml(ROOT/"machine_profiles/scara_hotwire_eps.yaml")
        profile["profile_locked"]=True
        profile["work_area"]={"x_max":2000,"y_max":1000,"z_max":200}
        profile["axes"]={k:"synthetic_fixture" for k in profile["axes"]}
        profile["hotwire"].update(wire_count=1,effective_kerf_mm=1.5,min_segment_mm=5,min_radius_mm=2)
        profile["feed"].update(default_xy_mm_min=500,slow_curve_mm_min=250)
        profile["safety"]["production_allowed"]=True
        profile["notes"]={}
        contract={**dict.fromkeys(FLAGS,True),"controller_profile":"CNC_V","feed_mm_min":400,"heat_s":250,
                  "dwell_value":2,"max_heat_s":350,"max_dwell_seconds":5,"dwell_unit":"seconds",
                  "path_control":"G61","work_offset":"G54","machine_profile_sha256":sha(canonical(profile))}
        source=root/"source"
        with ExitStack() as stack:
            for mod in ("epscad.validators.machine_validator","epscad.validators.production_gate","epscad.validators.geometry_validator","epscad.publishing.release","epscad.publishing.tap_release"):
                stack.enter_context(patch(mod+".load_machine_profile",return_value=profile))
            job=build_job(spec)
            if job.has_errors:
                raise ValueError("Synthetic fixture failed")
            write_outputs(job,spec,source)
            _,report,names=verified_source(source)
            data,hashes=tap_candidate(source,report,names,contract)
            registry=root/"registry.json"
            registry.write_text(json.dumps([{"id":"synthetic-test-only","revision":"r01","name":"FIXTURE SINTETICA - NAO USAR NA MAQUINA","category":"Testes","source":str(source),"public_authorized":True,"require_tap":True,"release":{"approved":True,"tap_approved":True,"tap_contract":contract,**hashes}}]),encoding="utf-8")
            site=root/"site"
            item=build_site(registry,site,viewer_dir=root/"no-vendor")[0]
        assert item["machine_sha256"]==sha(data)
        # Deliberately invalidate deploy inventory before opening browser.
        (site/"SYNTHETIC_TEST_ONLY_DO_NOT_DEPLOY.txt").write_text("CI only. Never operate hardware.",encoding="utf-8")
        try:
            local_inventory(site)
        except ValueError:
            pass
        else:
            raise AssertionError("Synthetic snapshot must not be deployable")
        subprocess.run([sys.executable,str(ROOT/"scripts/check_gallery_browser.py"),"--site",str(site),"--screenshots",str(root/"shots")],check=True)
    print("Synthetic TAP browser download test passed; temporary fixture removed")
if __name__=="__main__":
    main()
