"""Generate all reviewed local trial TAPs in one pass, with per-model hash authorization.
Does not publish or change machine/profile approval. Individual failures are recorded.
"""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from epscad.cam.tp40_planner import PORTAL_MODELS
from epscad.build import build_job
from epscad.loader import load_yaml
from epscad.exporters.mach3_tap import canonical,sha,ordered_points,FLAGS,KEYS,number
from prepare_mach3_trial import prepare_trial

def plan_rows(handoff,slab_library=None):
    rows=[]
    models=list(PORTAL_MODELS)
    if slab_library is not None:
        from epscad.cam.slab_planner import SLAB_CATALOG
        for vid in sorted(load_yaml(SLAB_CATALOG)["variants"]):
            models.append({"portal_id":vid,"revision":"r01","name":vid,"slab":True})
    for meta in models:
        slug=meta["portal_id"]+"-"+meta["revision"]
        project=(Path(slab_library)/"slab_plans"/slug if meta.get("slab") else handoff/slug)/"projeto_trajetoria.yaml"
        row={"id":slug,"name":meta["name"],"project":project}
        try:
            job=build_job(load_yaml(project))
            row.update(path_sha256=sha(canonical(ordered_points(job))),project_sha256=sha(project.read_bytes()))
        except Exception as exc:
            row["error"]=str(exc)
        rows.append(row)
    return rows

def bind_reviewed_contract(profile, contract, destination):
    """Bind a human-reviewed, previously unbound contract to its actual snapshot.
    No confirmation, measured value or approval is invented or modified.
    A changed, previously bound profile requires a fresh review.
    """
    profile_data=load_yaml(profile)
    record=json.loads(Path(contract).read_text(encoding="utf-8"))
    if set(record)!={"purpose","operator_trial_authorized","contract"} or record["purpose"]!="local_supervised_trial" or record["operator_trial_authorized"] is not True:
        raise ValueError("A reviewed local trial contract with explicit authorization is required")
    c=record["contract"]
    if set(c)!=KEYS or not all(c.get(k) is True for k in FLAGS):
        raise ValueError("Review the eight contract confirmations before binding")
    if (profile_data.get("id"),profile_data.get("unit"),profile_data.get("process_type"))!=("scara_hotwire_eps","mm","hotwire_2d"):
        raise ValueError("Expected the measured SCARA profile")
    for group,keys in (("work_area",("x_max","y_max","z_max")),("hotwire",("wire_count","effective_kerf_mm","min_segment_mm")),("feed",("default_xy_mm_min",))):
        for k in keys:
            number(profile_data.get(group,{}).get(k),group+"."+k)
    if type(profile_data["hotwire"]["wire_count"]) is not int:
        raise ValueError("wire_count must be a positive integer")
    if c["controller_profile"]!="CNC_V" or c["dwell_unit"] not in ("seconds","milliseconds") or c["path_control"] not in ("G61","G64") or c["work_offset"] not in ("G54","G55","G56","G57","G58","G59"):
        raise ValueError("Review controller and modal settings")
    for k in ("feed_mm_min","heat_s","max_heat_s","dwell_value","max_dwell_seconds"):
        number(c[k],k,k in ("dwell_value","max_dwell_seconds"))
    expected=sha(canonical(profile_data))
    if c["machine_profile_sha256"] not in (expected,"","CALCULAR_COM_sha(canonical(profile))_APOS_PREENCHER_SNAPSHOT"):
        raise ValueError("Previously bound contract differs from profile; require a new review")
    c["machine_profile_sha256"]=expected
    destination=Path(destination)
    with destination.open("x",encoding="utf-8") as f:
        json.dump(record,f,indent=2,ensure_ascii=False)
    return expected

def batch(handoff,profile,contract,approvals,output,slab_library=None):
    handoff,profile,contract,approvals,output=map(Path,(handoff,profile,contract,approvals,output))
    if output.exists(): raise ValueError("Choose a new output directory")
    profile_digest=sha(canonical(load_yaml(profile)))
    record=json.loads(contract.read_text(encoding="utf-8"))
    if record.get("contract",{}).get("machine_profile_sha256")!=profile_digest:
        raise ValueError("Contract is not bound to this profile. After human review use --bind-reviewed-contract to create a new bound contract; do not use TEMPLATE files directly.")
    approved=json.loads(approvals.read_text(encoding="utf-8"))
    if not isinstance(approved,dict): raise ValueError("Expected per-model approval mapping")
    output.mkdir(parents=True)
    results=[]
    for row in plan_rows(handoff,slab_library):
        project=row.pop("project")
        result=dict(row,status="blocked")
        if "error" not in row:
            a=approved.get(row["id"],{})
            if not isinstance(a,dict) or a.get("trial_authorized") is not True or any(a.get(k)!=row[k] for k in ("path_sha256","project_sha256")):
                result["error"]="Missing explicit approval of this exact project and path"
            else:
                try:
                    report=prepare_trial(project,profile,contract,output/row["id"])
                    result.update(status="trial_generated",tap=str(Path(row["id"])/report["machine_file"]),tap_sha256=report["tap_sha256"])
                except Exception as exc:
                    result["error"]=str(exc)
        results.append(result)
    report={"purpose":"private_trial_batch","production_approved":False,"public_authorized":False,"models":results}
    (output/"batch_report.json").write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--handoff",type=Path)
    p.add_argument("--bind-reviewed-contract",type=Path,metavar="NEW_JSON",help="Bind an explicitly reviewed, previously unbound contract to the measured profile; no TAP generated by this option")
    p.add_argument("--list",action="store_true")
    p.add_argument("--slab-library",type=Path,help="Optional private library containing the four saved slab projects")
    p.add_argument("--profile",type=Path)
    p.add_argument("--contract",type=Path)
    p.add_argument("--approvals",type=Path)
    p.add_argument("--output",type=Path)
    a=p.parse_args()
    if a.bind_reviewed_contract:
        if not a.profile or not a.contract or a.list:
            p.error("Binding requires --profile and --contract, without --list")
        print("Contract bound:",bind_reviewed_contract(a.profile,a.contract,a.bind_reviewed_contract))
        return 0
    if not a.handoff:
        p.error("--handoff required for listing or generating")
    if a.list:
        rows=plan_rows(a.handoff,a.slab_library)
        print(json.dumps([{k:v for k,v in r.items() if k!="project"} for r in rows],indent=2,ensure_ascii=False))
        return int(any("error" in r for r in rows))
    if not all((a.profile,a.contract,a.approvals,a.output)):
        p.error("Batch needs --profile --contract --approvals --output")
    result=batch(a.handoff,a.profile,a.contract,a.approvals,a.output,a.slab_library)
    print(json.dumps(result,indent=2,ensure_ascii=False))
    return int(any(r["status"]!="trial_generated" for r in result["models"]))
if __name__=="__main__":
    raise SystemExit(main())
