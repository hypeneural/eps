"""Non-executable local path report; never emits G-code or controls hardware."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from epscad.loader import load_yaml
from epscad.build import build_job
from epscad.exporters.mach3_tap import ordered_points,canonical,sha
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("project",type=Path)
    p.add_argument("--output",required=True,type=Path)
    a=p.parse_args()
    job=build_job(load_yaml(a.project))
    points=ordered_points(job)
    report={"purpose":"offline_geometry_only","production_approved":False,"project_id":job.project_id,
            "path_sha256":sha(canonical(points)),"points_mm":points,"bbox_mm":job.bbox,
            "warning":"Not machine instructions. No thermal compensation, stock clearance or physical approval inferred."}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    if a.output.suffix.lower()!=".json": p.error("Output must be JSON")
    with a.output.open("x",encoding="utf-8") as f: json.dump(report,f,indent=2)
if __name__=="__main__": main()
