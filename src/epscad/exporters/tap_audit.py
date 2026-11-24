"""Read-only inventory of the factory's historical dialect. Not an interpreter or authorization."""
from collections import Counter
from decimal import Decimal
import hashlib
from pathlib import PurePosixPath
import re
import zipfile

WORD=re.compile(r"([A-Z])([+-]?(?:\d+(?:\.\d*)?|\.\d+))")
ALLOWED_G={Decimal(x) for x in ("1","2","3","4","21","80","90","91","90.1","91.1","17","94","40","49","61","64")}
ALLOWED_M={Decimal(x) for x in ("3","5","30")}

def audit(data):
    if len(data)>2_000_000:
        raise ValueError("TAP exceeds audit limit")
    codes=Counter()
    axes={}
    nlines=0
    previous_n=-1
    for raw in data.decode("ascii").splitlines():
        line=re.sub(r"\s+","",raw.upper())
        if not line: continue
        words=WORD.findall(line)
        if "".join(a+b for a,b in words)!=line or not words or words[0][0]!="N":
            raise ValueError("Unsupported block syntax")
        number=Decimal(words[0][1])
        if number!=int(number) or number<=previous_n:
            raise ValueError("Invalid line numbering")
        previous_n=number
        nlines+=1
        for a,b in words[1:]:
            v=Decimal(b)
            if a in "GM":
                if v not in (ALLOWED_G if a=="G" else ALLOWED_M):
                    raise ValueError("Unsupported command")
                codes[a+str(v.normalize()) if v<10 else a+format(v,"f")]+=1
            elif a in "XYZIJFSP":
                if a=="Z" and v!=0: raise ValueError("Nonzero Z unsupported")
                axes.setdefault(a,[]).append(v)
            else:
                raise ValueError("Unsupported word")
    if not nlines: raise ValueError("Empty TAP")
    return {"sha256":hashlib.sha256(data).hexdigest(),"blocks":nlines,
            "codes":dict(codes),"words":{k:{"min":float(min(v)),"max":float(max(v))} for k,v in axes.items()},
            "absolute_mode_explicit":"G90" in codes,"ij_mode_explicit":"G90.1" in codes or "G91.1" in codes,
            "production_approved":False}

def audit_zip(path):
    reports=[]
    with zipfile.ZipFile(path) as z:
        entries=[i for i in z.infolist() if not i.is_dir()]
        if len(entries)>1000 or sum(i.file_size for i in entries)>20_000_000:
            raise ValueError("Archive exceeds audit limits")
        for item in entries:
            name=PurePosixPath(item.filename.replace(chr(92),"/")).name
            if not name.lower().endswith(".tap"): continue
            if item.file_size>2_000_000: raise ValueError("Oversize member")
            reports.append({"name":name,**audit(z.read(item))})
    if not reports: raise ValueError("No TAP files")
    return {"files":len(reports),"unique":len({x["sha256"] for x in reports}),"programs":reports,"production_approved":False}
