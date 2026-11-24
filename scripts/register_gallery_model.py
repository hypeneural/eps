"""Manage the local gallery registry. Does not deploy or approve production."""
import argparse
import json
from pathlib import Path
import os
import re
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from epscad.publishing.site import SLUG,verified_source

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--registry",type=Path,default=ROOT/"portal_local/registry.json")
    sub=p.add_subparsers(dest="action",required=True)
    add=sub.add_parser("add")
    add.add_argument("--id",required=True)
    add.add_argument("--revision",required=True)
    add.add_argument("--name",required=True)
    add.add_argument("--category",default="Telhas")
    add.add_argument("--source",required=True,type=Path)
    add.add_argument("--public-authorized",action="store_true",required=True)
    remove=sub.add_parser("remove")
    remove.add_argument("--id",required=True)
    a=p.parse_args()
    registry=a.registry.resolve()
    if not SLUG.fullmatch(a.id):
        p.error("Invalid model ID")
    records=json.loads(registry.read_text(encoding="utf-8")) if registry.exists() else []
    existing=next((r for r in records if r["id"]==a.id),None)
    if a.action=="remove":
        if existing is None:
            p.error("Model not found")
        records=[r for r in records if r["id"]!=a.id]
    else:
        if not re.fullmatch(r"r[0-9]{2,5}",a.revision):
            p.error("Invalid revision")
        if existing and int(a.revision[1:])<=int(existing["revision"][1:]):
            p.error("New revision must increase")
        status,_,_=verified_source(a.source.resolve())
        if status=="production_released":
            p.error("Production release requires separate explicit DXF hash approval in registry")
        try:
            source=os.path.relpath(a.source.resolve(),registry.parent)
        except ValueError:
            source=str(a.source.resolve())
        records=[r for r in records if r["id"]!=a.id]
        records.append({"id":a.id,"revision":a.revision,"name":a.name,"category":a.category,"source":source,"public_authorized":True})
    registry.parent.mkdir(parents=True,exist_ok=True)
    tmp=registry.with_suffix(".tmp")
    tmp.write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding="utf-8")
    tmp.replace(registry)
    print(registry,"— build and deploy separately")
if __name__=="__main__":
    main()
