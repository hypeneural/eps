"""Local-only historical ZIP inspection; never execute or extract archive paths."""
from collections import Counter
import hashlib
from pathlib import Path, PurePosixPath
import tempfile
import zipfile
import ezdxf
from epscad.geometry.historical_roof import recover_upper_profile

MAX_MEMBER=16*1024*1024
MAX_TOTAL=128*1024*1024

def inspect_zip(path, *, width, length, gauge, expected_roof):
    with zipfile.ZipFile(path) as z:
        entries=[i for i in z.infolist() if not i.is_dir()]
        if len(entries)>10000 or sum(i.file_size for i in entries)>MAX_TOTAL:
            raise ValueError("Evidence ZIP exceeds local audit limits")
        counts=Counter()
        hashes={}
        candidates={}
        for i in entries:
            name=PurePosixPath(i.filename.replace(chr(92),"/")).name
            ext=Path(name).suffix.lower()
            if ext not in (".dxf",".tap",".nc",".pst",".xml",".pdf"):
                continue
            if i.file_size>MAX_MEMBER:
                raise ValueError("Evidence member exceeds audit size limit")
            data=z.read(i)
            digest=hashlib.sha256(data).hexdigest()
            counts[ext]+=1
            hashes.setdefault(ext,set()).add(digest)
            if name.casefold()=="telha tp 40 base lisa.dxf":
                candidates[digest]=data
        if len(candidates)!=1:
            raise ValueError("Expected one distinct historical TP40 base lisa DXF; review ZIP manually")
        digest,data=next(iter(candidates.items()))
        with tempfile.TemporaryDirectory() as tmp:
            dxf=Path(tmp)/"source.dxf"
            dxf.write_bytes(data)
            doc=ezdxf.readfile(dxf)
            if doc.header.get("$INSUNITS",0)!=4:
                raise ValueError("Historical DXF must explicitly declare mm")
            entities=list(doc.modelspace())
            if not entities or any(e.dxftype()!="LINE" for e in entities):
                raise ValueError("Historical reference is not a LINE-only drawing")
            coords=[q for e in entities for q in (e.dxf.start,e.dxf.end)]
            right=max(q.x for q in coords)
            left=right-width
            top=max(q.y for q in coords)
            roof,review=recover_upper_profile(dxf,left=left,right=right,top=top,length=length,gauge=gauge)
            delta=roof.core.symmetric_difference(expected_roof.core).area
            if delta>0.01:
                raise ValueError(f"Historical profile differs by {delta:.6f} mm2; explicit review required")
        return {"source_sha256":digest,"archive_entry_count":len(entries),
                "counts":dict(counts),"unique_counts":{k:len(v) for k,v in hashes.items()},
                "comparison_area_mm2":delta,"recovered":review,"physical_fit_confirmed":False}
