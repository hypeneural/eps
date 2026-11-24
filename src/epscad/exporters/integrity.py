"""Verify generated manifest/hash inventory. Integrity is not authorization."""
import hashlib
import json
import zipfile
from pathlib import Path
MANIFEST="06_manifest.json"
HASHES="11_hashes.sha256"
PACKAGE="12_package_for_machine.zip"

def verify_directory(directory):
    root=Path(directory)
    manifest=json.loads((root/MANIFEST).read_text(encoding="utf-8"))
    names=list(manifest["files"].values())+[MANIFEST]
    if len(set(names))!=len(names):
        raise ValueError("Duplicate manifest entries")
    for name in names:
        if not isinstance(name,str) or Path(name).name!=name or "/" in name or chr(92) in name or name in (".","..",HASHES,PACKAGE):
            raise ValueError("Invalid manifest path")
    hashes={}
    for row in (root/HASHES).read_text(encoding="utf-8").splitlines():
        digest,name=row.split("  ",1)
        if name in hashes:
            raise ValueError("Duplicate hash entry")
        hashes[name]=digest
    if set(hashes)!=set(names):
        raise ValueError("Manifest/hash inventory mismatch")
    for name in names:
        p=root/name
        if p.is_symlink() or not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=hashes[name]:
            raise ValueError("Integrity failure: "+name)
    machine=[n for n in names if n.lower().endswith((".dxf",".tap",".nc",".gcode"))]
    if any(not n.lower().endswith(".dxf") for n in machine):
        raise ValueError("Direct G-code blocked")
    if machine and (manifest.get("has_errors") or manifest.get("production_status") not in ("validated_geometry","cam_ready","machine_tested","production_released")):
        raise ValueError("Blocked machine file")
    from epscad.exporters.dxf_validator import validate_dxf
    for n in machine:
        if not validate_dxf(root/n).ok:
            raise ValueError("Invalid DXF: "+n)
    return sorted(names+[HASHES])

def verify_zip(directory):
    root=Path(directory)
    names=verify_directory(root)
    with zipfile.ZipFile(root/PACKAGE) as archive:
        if sorted(archive.namelist())!=names or archive.testzip() is not None:
            raise ValueError("ZIP inventory or CRC mismatch")
        for name in names:
            if archive.read(name)!=(root/name).read_bytes():
                raise ValueError("ZIP content mismatch: "+name)
    return names

def rebuild_zip(directory):
    root=Path(directory)
    names=verify_directory(root)
    temp=root/(PACKAGE+".tmp")
    try:
        with zipfile.ZipFile(temp,"w",compression=zipfile.ZIP_DEFLATED) as archive:
            for name in names:
                archive.write(root/name,arcname=name)
        temp.replace(root/PACKAGE)
    finally:
        temp.unlink(missing_ok=True)
    return verify_zip(root)
