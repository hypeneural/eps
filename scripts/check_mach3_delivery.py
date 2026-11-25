"""Strict delivery acceptance, not a machine approval or generator.
Exit nonzero unless all nine current models have matching direct TAP downloads.
Optionally verify the exact snapshot via HTTPS using the existing read-only checker.
"""
import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from epscad.publishing.deploy import local_inventory
from epscad.cam.tp40_planner import PORTAL_MODELS
from epscad.cam.slab_planner import SLAB_CATALOG
from epscad.loader import load_yaml

def expected_ids():
    return {m["portal_id"] for m in PORTAL_MODELS}|set(load_yaml(SLAB_CATALOG)["variants"])

class Links(HTMLParser):
    def __init__(self,html):
        super().__init__()
        self.downloads=[]
        self.feed(html)
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=="a" and "download" in a:
            self.downloads.append(a.get("href",""))

def inspect(site):
    site=Path(site)
    inv=local_inventory(site)
    records=json.loads((site/"catalog.json").read_text(encoding="utf-8"))
    ids=expected_ids()
    by_id={m["id"]:m for m in records}
    if len(by_id)!=len(records):
        raise ValueError("Duplicate model IDs")
    home=Links((site/"index.html").read_text(encoding="utf-8"))
    results=[]
    for model in sorted(ids):
        m=by_id.get(model)
        row={"id":model,"delivered":False}
        if not m:
            row["reason"]="model_missing"
        elif m.get("status")!="production_released" or m.get("machine_format")!="TAP" or not m.get("machine"):
            row["reason"]="approved_TAP_missing"
        else:
            slug=m["slug"]
            machine=m["machine"]
            expected=slug+".tap"
            rel="modelos/"+slug+"/"+machine
            if machine!=expected or rel not in inv:
                row["reason"]="wrong_name_or_missing_file"
            else:
                folder=site/"modelos"/slug
                data=(folder/machine).read_bytes()
                h=hashlib.sha256(data).hexdigest()
                detail=Links((folder/"index.html").read_text(encoding="utf-8"))
                public=Links((folder/"publico.html").read_text(encoding="utf-8"))
                if not data or h!=m.get("machine_sha256") or len(data)!=m.get("machine_bytes") or h!=inv[rel]:
                    row["reason"]="hash_or_size_mismatch"
                elif rel not in home.downloads or machine not in detail.downloads or public.downloads:
                    row["reason"]="incorrect_download_links"
                else:
                    row.update(delivered=True,relative_url=rel,sha256=h,bytes=len(data))
        results.append(row)
    return {"purpose":"delivery_acceptance_not_physical_approval","expected":len(ids),"delivered":sum(r["delivered"] for r in results),"models":results}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--site",required=True,type=Path)
    p.add_argument("--https",action="store_true",help="Also verify exact bytes and headers at official portal")
    a=p.parse_args()
    r=inspect(a.site)
    print(json.dumps(r,ensure_ascii=False,indent=2))
    if r["delivered"]!=r["expected"]:
        return 1
    if a.https:
        subprocess.run([sys.executable,str(ROOT/"scripts/check_gallery_live.py"),"--site",str(a.site)],check=True)
    return 0
if __name__=="__main__":
    raise SystemExit(main())
