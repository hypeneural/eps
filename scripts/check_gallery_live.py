"""Read-only HTTPS check against exact local snapshot; no FTP or deployment."""
import argparse
from pathlib import Path
import sys
from urllib.parse import quote,urlsplit
from urllib.request import Request,urlopen
from urllib.error import HTTPError
import hashlib
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from epscad.publishing.deploy import local_inventory

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--site",required=True,type=Path)
    p.add_argument("--url",default="https://eps.etijucas.com.br")
    p.add_argument("--previous-site",type=Path,help="Compare old snapshot and check removed machine links are inaccessible")
    a=p.parse_args()
    base=a.url.rstrip("/")
    u=urlsplit(base)
    if u.scheme!="https" or not u.hostname or u.username or u.password or u.query or u.fragment:
        p.error("A clean HTTPS URL is required")
    current=local_inventory(a.site)
    def fetch(name):
        target=base+"/"+quote(name,safe="/")
        return urlopen(Request(target,headers={"Cache-Control":"no-cache","Accept-Encoding":"identity","User-Agent":"EPS-Portal-Check/1"}),timeout=25)
    for name,expected in sorted(current.items()):
        if name==".htaccess":
            continue
        with fetch(name) as response:
            final=urlsplit(response.geturl())
            if final.scheme!="https" or final.netloc!=u.netloc:
                raise ValueError("Unexpected HTTPS redirect: "+name)
            sha=hashlib.sha256()
            total=0
            while True:
                block=response.read(65536)
                if not block: break
                total+=len(block)
                if total>(a.site/name).stat().st_size:
                    raise ValueError("Unexpected response size: "+name)
                sha.update(block)
            if sha.hexdigest()!=expected:
                raise ValueError("HTTPS hash mismatch: "+name)
            if name.endswith(".dxf") and "attachment" not in response.headers.get("Content-Disposition","").lower():
                raise ValueError("DXF attachment header missing: "+name)
    if a.previous_site:
        from epscad.publishing.deploy import machine_file
        for name in local_inventory(a.previous_site).keys()-current.keys():
            if not machine_file(name): continue
            try:
                with fetch(name):
                    raise ValueError("Revoked machine file still accessible: "+name)
            except HTTPError as exc:
                if exc.code not in (403,404,410): raise
    # Server control files should not be served.
    try:
        with fetch(".htaccess"):
            raise ValueError("Server exposes .htaccess")
    except HTTPError as exc:
        if exc.code not in (403,404,410): raise
    print("HTTPS bytes and revision checks passed:",base)
if __name__=="__main__":
    main()
