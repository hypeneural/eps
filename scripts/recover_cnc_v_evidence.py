"""Recover documented settings, not physical confirmations, from local factory backup."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import xml.etree.ElementTree as ET
import zipfile

def digest(data):
    return hashlib.sha256(data).hexdigest()

def inspect_backup(path):
    with zipfile.ZipFile(path) as z:
        entries=[i for i in z.infolist() if not i.is_dir()]
        if len(entries)>1000 or sum(i.file_size for i in entries)>30_000_000:
            raise ValueError("Backup exceeds inspection limits")
        def unique(name):
            found=[i for i in entries if PurePosixPath(i.filename.replace("\\","/")).name.casefold()==name.casefold()]
            if not found: raise ValueError("Missing "+name)
            values={digest(z.read(i)):z.read(i) for i in found}
            if len(values)!=1: raise ValueError("Conflicting copies: "+name)
            return next(iter(values.values()))
        xml=unique("CNC_V.xml")
        if re.search(br"<!DOCTYPE|<!ENTITY",xml,re.I):
            raise ValueError("XML declarations not supported")
        pref=ET.fromstring(xml).find("Preferences")
        if pref is None or pref.findtext("Profile")!="CNC_V":
            raise ValueError("Not the CNC_V profile")
        keys=("Profile","DwellinMilli","SoftLimit","M0Max","M0Min","M1Max","M1Min","M2Max","M2Min","INIT","InitAllResets","M30SpinOff","NoSpindle","PWM","SpinCW","SpinDelayCW")
        settings={k:pref.findtext(k) for k in keys}
        pst=unique("isopor.pst")
        macros={name:unique(name) for name in ("m3.m1s","m5.m1s")}
        programs={}
        for i in entries:
            if i.filename.lower().endswith(".tap"):
                b=z.read(i)
                programs.setdefault(digest(b),b)
        counts={"F":{},"S":{},"G4_P":{}}
        for data in programs.values():
            s=data.decode("ascii",errors="replace").upper()
            for k,pattern in (("F",r"F([0-9.]+)"),("S",r"S([0-9.]+)"),("G4_P",r"G0?4\s*P([0-9.]+)")):
                for value in set(re.findall(pattern,s)):
                    counts[k][value]=counts[k].get(value,0)+1
        text=pst.decode("latin1")
        observed={"feed_mm_min":re.findall(r"(?m)^F([0-9.]+)\s*$",text),
                  "spindle_s":re.findall(r"(?m)^S([0-9.]+)\s*$",text),
                  "dwell_value":re.findall(r"(?m)^G0?4\s+P([0-9.]+)\s*$",text),
                  "dwell_unit":{"0":"seconds","1":"milliseconds"}.get(settings["DwellinMilli"])}
        return {"purpose":"documentary_evidence_only","production_approved":False,
                "archive_sha256":digest(Path(path).read_bytes()),"xml_sha256":digest(xml),
                "pst_sha256":digest(pst),"macro_sha256":{k:digest(v) for k,v in macros.items()},
                "xml_observed":settings,"pst_observed":observed,"unique_taps":len(programs),
                "program_observations":counts,
                "macro_observed":{k:v.decode("ascii",errors="replace").strip() for k,v in macros.items()},
                "pending_physical":["usable travel and origin","wire count and kerf","minimum segment","permitted feed and heat limits","physical I/O and end behavior","stock and ordered path per model","current modal/work offset confirmation"],
                "warning":"Archived settings are not current physical measurements or approval. No profile or flags modified."}
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("backup",type=Path)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    report=inspect_backup(a.backup)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open("x",encoding="utf-8") as f:
        json.dump(report,f,indent=2,ensure_ascii=False)
    print("Recovered documentary evidence:",a.output)
if __name__=="__main__":
    main()
