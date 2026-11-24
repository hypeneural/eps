"""Generate a real nominal TP40 review and static gallery, without network."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--logo",type=Path)
    a=p.parse_args()
    out=a.output.resolve()
    if out.exists():
        p.error("Choose a fresh output directory")
    out.mkdir(parents=True)
    # No factory originals needed; prepare_tp40 may optionally read local evidence.
    subprocess.run([sys.executable,str(ROOT/"scripts/prepare_tp40.py"),"--output",str(out/"tp40")],check=True)
    registry=out/"registry.json"
    registry.write_text(json.dumps([{"id":"eps-tp40-001","revision":"r01","name":"TP40 - Base lisa","category":"Telhas","source":"tp40","public_authorized":True}],indent=2),encoding="utf-8")
    args=[sys.executable,str(ROOT/"scripts/build_gallery.py"),"--registry",str(registry),"--output",str(out/"site")]
    if a.logo:
        args+=["--logo",str(a.logo)]
    subprocess.run(args,check=True)
    print("Open:",out/"site/index.html")
if __name__=="__main__":
    main()
