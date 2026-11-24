"""Inspect a prospective public cutting package; never approve, edit or deploy."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from epscad.publishing.site import verified_source
from epscad.publishing.release import candidate_hashes

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("source",type=Path)
    a=p.parse_args()
    status,report,names=verified_source(a.source)
    if status!="production_released":
        p.error("Only already homologated production packages qualify; no approval was made")
    print(json.dumps({"approved":False,**candidate_hashes(a.source,report,names)},indent=2))
    print("Review with the responsible human. These hashes do not authorize fabrication.",file=sys.stderr)
if __name__=="__main__":
    main()
