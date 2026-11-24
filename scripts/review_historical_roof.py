"""Recover visual assets only; never generate DXF or TAP from historical evidence."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from epscad.geometry.historical_roof import recover_upper_profile
from epscad.exporters.roof_3d import write_roof_assets

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("dxf",type=Path)
    for key in ("left","right","top","length"):
        p.add_argument("--"+key,required=True,type=float)
    p.add_argument("--gauge",type=float,default=.43)
    p.add_argument("--output",required=True,type=Path)
    a=p.parse_args()
    if a.output.exists() and any(a.output.iterdir()):
        p.error("Choose a new empty output directory")
    roof,report=recover_upper_profile(a.dxf,left=a.left,right=a.right,top=a.top,length=a.length,gauge=a.gauge)
    a.output.mkdir(parents=True,exist_ok=True)
    report["source_sha256"]=hashlib.sha256(a.dxf.read_bytes()).hexdigest()
    files=write_roof_assets(roof,a.output,"draft")
    report["files"]={k:Path(v).name for k,v in files.items()}
    (a.output/"historical_review.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    (a.output/"README.txt").write_text("DRAFT - REVIEW ONLY. No machine file. Dimensions from selected CAD envelope; not a confirmed physical part. Metal and extrusion length are assumptions. Original toolpath not reproduced.\n",encoding="utf-8")
    print(a.output.resolve())
    return 0
if __name__=="__main__":
    raise SystemExit(main())
