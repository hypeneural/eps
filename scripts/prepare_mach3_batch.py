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
from epscad.exporters.mach3_tap import canonical,sha,ordered_points
from prepare_mach3_trial import prepare_trial

def plan_rows(handoff):
    rows=[]
    for meta in PORTAL_MODELS:
        slug=meta["portal_id"]+"-"+meta["revision"]
        project=handoff/slug/"projeto_trajetoria.yaml"
        row={"id":slug,"name":meta["name"],"project":project}
        try:
            job=build_job(load_yaml(project))
            row.update(path_sha256=sha(canonical(ordered_points(job))),project_sha256=sha(project.read_bytes()))
        except Exception as exc:
            row["error"]=str(exc)
        rows.append(row)
    return rows

def batch(handoff,profile,contract,approvals,output):
    handoff,profile,contract,approvals,output=map(Path,(handoff,profile,contract,approvals,output))
    if output.exists(): raise ValueError("Choose a new output directory")
    profile_digest=sha(canonical(load_yaml(profile)))
    record=json.loads(contract.read_text(encoding="utf-8"))
    if record.get("contract",{}).get("machine_profile_sha256")!=profile_digest:
        raise ValueError("Contract is not bound to this profile")
    approved=json.loads(approvals.read_text(encoding="utf-8"))
    if not isinstance(approved,dict): raise ValueError("Expected per-model approval mapping")
    output.mkdir(parents=True)
    results=[]
    for row in plan_rows(handoff):
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
    p.add_argument("--handoff",type=Path,required=True)
    p.add_argument("--list",action="store_true")
    p.add_argument("--profile",type=Path)
    p.add_argument("--contract",type=Path)
    p.add_argument("--approvals",type=Path)
    p.add_argument("--output",type=Path)
    a=p.parse_args()
    if a.list:
        rows=plan_rows(a.handoff)
        print(json.dumps([{k:v for k,v in r.items() if k!="project"} for r in rows],indent=2,ensure_ascii=False))
        return int(any("error" in r for r in rows))
    if not all((a.profile,a.contract,a.approvals,a.output)):
        p.error("Batch needs --profile --contract --approvals --output")
    result=batch(a.handoff,a.profile,a.contract,a.approvals,a.output)
    print(json.dumps(result,indent=2,ensure_ascii=False))
    return int(any(r["status"]!="trial_generated" for r in result["models"]))
if __name__=="__main__":
    raise SystemExit(main())
