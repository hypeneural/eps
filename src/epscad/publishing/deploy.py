"""Explicit FTPS deployment to a dedicated document root; never plain FTP."""
from ftplib import FTP_TLS, error_perm
from io import BytesIO
from pathlib import Path, PurePosixPath
import json
import os
import re
import ssl
import uuid
from epscad.publishing.site import digest

STATE="portal-state.json"
PATH=re.compile(r"(?:index\.html|catalog\.json|robots\.txt|\.htaccess|assets/[A-Za-z0-9_.-]+|modelos/[a-z0-9-]+/[A-Za-z0-9_.-]+)")
MAX_STATE=2*1024*1024

def validate_state(state):
    if state.get("format")!=1 or not isinstance(state.get("files"),dict) or len(state["files"])>12000:
        raise ValueError("Invalid portal state")
    for name,checksum in state["files"].items():
        if not PATH.fullmatch(name) or any(p in (".","..") for p in PurePosixPath(name).parts) or not re.fullmatch("[0-9a-f]{64}",checksum):
            raise ValueError("Invalid portal inventory")
    return state["files"]

def local_inventory(root):
    root=Path(root)
    files=validate_state(json.loads((root/STATE).read_text(encoding="utf-8")))
    actual={p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    if actual!=set(files)|{STATE}:
        raise ValueError("Unexpected local portal files")
    for name,checksum in files.items():
        p=root/name
        if p.is_symlink() or digest(p.read_bytes())!=checksum:
            raise ValueError("Local portal integrity mismatch: "+name)
    return files

def machine_file(name):
    return name.lower().endswith((".dxf","-producao.zip","/ordem.pdf"))

def check_revision(previous,current):
    for name in previous.keys() & current.keys():
        if machine_file(name) and previous[name]!=current[name]:
            raise ValueError("Use a new revision for changed machine assets: "+name)
    return sorted(previous.keys()-current.keys(),key=lambda p:(not machine_file(p),p))

def read_remote(ftp,name,limit=64*1024*1024):
    data=bytearray()
    def append(block):
        if len(data)+len(block)>limit:
            raise ValueError("Remote file exceeds limit")
        data.extend(block)
    ftp.retrbinary("RETR "+name,append)
    return bytes(data)

def ensure_dirs(ftp,name):
    parts=PurePosixPath(name).parts[:-1]
    root=ftp.pwd()
    try:
        for part in parts:
            try:
                ftp.cwd(part)
            except error_perm:
                ftp.mkd(part)
                ftp.cwd(part)
    finally:
        ftp.cwd(root)

def remote_names(ftp,folder="."):
    return {PurePosixPath(x.rstrip("/")).name for x in ftp.nlst(folder)}-{"",".",".."}

def upload(ftp,name,data):
    ensure_dirs(ftp,name)
    # Temporary remote name is not a published URL; verified before atomic rename.
    temp=str(PurePosixPath(name).with_name(".eps-upload-"+uuid.uuid4().hex))
    try:
        ftp.storbinary("STOR "+temp,BytesIO(data))
        if digest(read_remote(ftp,temp))!=digest(data):
            raise ValueError("Remote upload checksum mismatch: "+name)
        ftp.rename(temp,name)
        if digest(read_remote(ftp,name))!=digest(data):
            raise ValueError("Remote final checksum mismatch: "+name)
    finally:
        try:
            ftp.delete(temp)
        except error_perm:
            pass

def remove(ftp,name):
    path=PurePosixPath(name)
    folder=str(path.parent)
    # Only delete managed inventory paths; do not treat a permission error as success.
    # Missing parent is checked component by component.
    root=ftp.pwd()
    try:
        for part in path.parts[:-1]:
            if part not in remote_names(ftp):
                return
            ftp.cwd(part)
        if path.name in remote_names(ftp):
            ftp.delete(path.name)
        if path.name in remote_names(ftp):
            raise ValueError("Remote revocation failed: "+name)
    finally:
        ftp.cwd(root)

def deploy(root,*,initialize=False,allow_production=False):
    root=Path(root)
    current=local_inventory(root)
    if any(machine_file(n) for n in current) and not allow_production:
        raise ValueError("Production publication requires explicit --allow-production")
    host=os.environ["EPS_FTP_HOST"]
    user=os.environ["EPS_FTP_USER"]
    password=os.environ["EPS_FTP_PASSWORD"]
    remote=os.environ["EPS_FTP_REMOTE_ROOT"]
    if not remote.strip() or not password:
        raise ValueError("Explicit dedicated remote root and password required")
    with FTP_TLS(context=ssl.create_default_context(),timeout=40) as ftp:
        ftp.connect(host,int(os.getenv("EPS_FTP_PORT","21")))
        ftp.login(user,password)
        ftp.prot_p()
        ftp.cwd(remote)
        if STATE in remote_names(ftp):
            previous=validate_state(json.loads(read_remote(ftp,STATE,MAX_STATE)))
        elif initialize:
            # Never take over a populated document root.
            if remote_names(ftp)-{".well-known"}:
                raise ValueError("Initialize only in an empty dedicated portal root")
            previous={}
        else:
            raise ValueError("Portal not initialized; check remote root and use --initialize once")
        stale=check_revision(previous,current)
        # Persist the union before uploading. Interrupted runs can revoke known stale paths.
        pending={"format":1,"files":{**previous,**current}}
        upload(ftp,STATE,json.dumps(pending,sort_keys=True).encode())
        # Revoke machine downloads first, then publish new assets before switching
        # the index. Keep old visual links alive until the new index is ready.
        for name in stale:
            if machine_file(name):
                remove(ftp,name)
        for name in sorted(current,key=lambda n:(n=="index.html",n=="catalog.json",n)):
            # Never trust the previous inventory alone. Skip only after readback.
            if previous.get(name)==current[name]:
                try:
                    if digest(read_remote(ftp,name))==current[name]:
                        continue
                except error_perm:
                    pass
            upload(ftp,name,(root/name).read_bytes())
        for name in stale:
            if not machine_file(name):
                remove(ftp,name)
        upload(ftp,STATE,(root/STATE).read_bytes())
    return len(current)
