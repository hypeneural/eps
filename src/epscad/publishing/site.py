"""Build a fresh, sanitized public snapshot from verified EPS outputs."""
from pathlib import Path
import hashlib
import json
import math
import re
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from PIL import Image
from jinja2 import Environment, FileSystemLoader, select_autoescape
from epscad.exporters.integrity import verify_zip

ROOT=Path(__file__).resolve().parents[3]
PORTAL=ROOT/"portal"
SLUG=re.compile(r"[a-z0-9][a-z0-9-]{0,63}")
MAX_ASSET=32*1024*1024
IMAGE_GROUPS=(
    ("perspectiva", "Perspectiva do EPS", ("30_eps_perspective_cycles.png","30_eps_cycles.png","26_render_eps.png","01_preview.png")),
    ("montagem", "Montagem com chapa", ("33_assembly_cycles.png","31_assembly_cycles.png","27_render_assembly.png")),
    ("secao", "Seção técnica", ("29_section_review.png","31_section_front_cycles.png")),
    ("microdobra", "Detalhe da microdobra", ("32_microgroove_detail_cycles.png",)),
    ("explodida", "Vista explodida", ("34_exploded_cycles.png",)),
    ("textura", "Textura do EPS", ("35_texture_closeup_cycles.png",)),
)
STATUS={"draft":"Em revisão","validated_geometry":"Somente teste","cam_ready":"Em revisão",
        "machine_tested":"Em revisão","production_released":"Liberado para corte"}

def digest(data):
    return hashlib.sha256(data).hexdigest()

def safe_file(root,name):
    if not isinstance(name,str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,100}",name):
        raise ValueError("Invalid asset filename")
    p=root/name
    if p.is_symlink() or not p.is_file() or p.stat().st_size>MAX_ASSET:
        raise ValueError("Missing, linked or oversized asset: "+name)
    return p

def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))

def verified_source(source):
    """Review ZIP must match its hashes and disk files. Never copy original ZIP."""
    if (source/"review.json").exists():
        report=load_json(safe_file(source,"review.json"))
        if report.get("status")!="draft" or report.get("production_confirmed") is not False or report.get("machine_export_allowed") is not False:
            raise ValueError("Invalid review status")
        hashes={}
        for row in safe_file(source,"SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
            checksum,name=row.split("  ",1)
            if name in hashes or not re.fullmatch("[0-9a-f]{64}",checksum):
                raise ValueError("Invalid review hashes")
            p=safe_file(source,name)
            if p.suffix.lower() in (".dxf",".tap",".nc",".gcode") or digest(p.read_bytes())!=checksum:
                raise ValueError("Blocked or changed review asset")
            hashes[name]=checksum
        if "review.json" not in hashes:
            raise ValueError("Review metadata not verified")
        with zipfile.ZipFile(safe_file(source,"TP40_REVISAO.zip")) as z:
            names=set(hashes)|{"SHA256SUMS.txt"}
            if sorted(z.namelist())!=sorted(names) or z.testzip() is not None:
                raise ValueError("Review ZIP inventory mismatch")
            for name in names:
                if z.read(name)!=safe_file(source,name).read_bytes():
                    raise ValueError("Review ZIP content mismatch")
        return "draft",report,set(hashes)
    names=set(verify_zip(source))
    report=load_json(safe_file(source,"06_manifest.json"))
    status=report.get("production_status")
    if status not in STATUS or report.get("has_errors") is not False or report.get("gcode_enabled") is not False:
        raise ValueError("Invalid or unsafe machine package")
    return status,report,names

def public_specs(report):
    geom=report.get("geometry") or {}
    roof=report.get("roof_3d") or {}
    # Deliberately omit origins, source paths, evidence, macros and machine settings.
    raw={
        "Largura (mm)":report.get("width_mm"),
        "Altura total (mm)":report.get("height_mm"),
        "Espessura mínima (mm)":report.get("min_thickness_mm"),
        "Comprimento de referência (mm)":report.get("extrusion_length_mm_assumed",roof.get("length_mm")),
        "Passo (mm)":geom.get("pitch_mm"),
        "Módulos":geom.get("periods"),
        "Microdobra - largura (mm)":geom.get("groove_width_mm"),
        "Microdobra - profundidade (mm)":geom.get("groove_depth_mm"),
        "Área transversal (mm²)":report.get("area_mm2",roof.get("core_area_mm2")),
        "Extensão X do percurso (mm)":(report.get("bbox_mm") or {}).get("width"),
        "Extensão Y do percurso (mm)":(report.get("bbox_mm") or {}).get("height"),
    }
    return {k:round(v,4) for k,v in raw.items() if isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) and v>=0}

def jpeg(src,dest,size,quality):
    with Image.open(src) as im:
        if im.width*im.height>30_000_000:
            raise ValueError("Oversized image")
        im=im.convert("RGBA")
        im.thumbnail(size,Image.Resampling.LANCZOS)
        canvas=Image.new("RGB",im.size,"white")
        canvas.paste(im,mask=im.getchannel("A"))
        canvas.save(dest,"JPEG",quality=quality,optimize=True,progressive=False)

def write_model(entry,base,stage,env):
    model_id=entry["id"]
    revision=entry["revision"]
    if not SLUG.fullmatch(model_id) or not re.fullmatch(r"r[0-9]{2,5}",revision):
        raise ValueError("Invalid model/revision id")
    name=entry["name"].strip()
    category=entry.get("category","Outros").strip()
    if not name or len(name)>120 or not category or len(category)>50:
        raise ValueError("Invalid public name or category")
    if entry.get("public_authorized") is not True:
        raise ValueError("Explicit public publication authorization required")
    source=(base/entry["source"]).resolve()
    status,report,verified=verified_source(source)
    # Only released, explicitly digest-approved machine file is published.
    release=entry.get("release") or {}
    dxf="03_cutpaths_r12.dxf"
    approved=bool(status=="production_released" and report.get("package_purpose")=="production"
                  and dxf in verified and release.get("approved") is True
                  and release.get("dxf_sha256")==digest(safe_file(source,dxf).read_bytes()))
    if approved:
        from epscad.loader import load_yaml
        from epscad.build import build_job
        from epscad.exporters.roundtrip import verify_roundtrip
        if "05_project.locked.yaml" not in verified:
            raise ValueError("Released project contract missing")
        spec=load_yaml(safe_file(source,"05_project.locked.yaml"))
        job=build_job(spec)
        if job.has_errors or job.production_status!="production_released" or not verify_roundtrip(job,safe_file(source,dxf)):
            raise ValueError("Released project fails current production gates or DXF readback")
    if status=="production_released" and not approved:
        raise ValueError("Production package requires explicit revision DXF hash approval")
    slug=model_id+"-"+revision
    folder=stage/"modelos"/slug
    folder.mkdir(parents=True)
    images=[]
    for key,label,candidates in IMAGE_GROUPS:
        selected=next((f for f in candidates if f in verified),None)
        if selected:
            jpeg(safe_file(source,selected),folder/(key+".jpg"),(1400,1000),86)
            images.append({"file":key+".jpg","label":label})
            if len(images)==1:
                jpeg(safe_file(source,selected),folder/"thumb.jpg",(420,280),76)
    if not images:
        raise ValueError("No verified preview")
    downloads=[]
    for original,target,label in (
        ("24_eps_core.glb","modelo.glb","Modelo 3D (GLB)"),
        ("23_assembly_reference.glb","montagem.glb","Montagem 3D (GLB)"),
        ("20_eps_core_mm.stl","peca-mm.stl","Sólido 3D (STL)"),
        ("02_ordem_corte_eps.pdf","ordem.pdf","Ordem de corte (PDF)"),
    ):
        if original in verified:
            # PDF may disclose machine parameters; only explicitly approved release.
            if original.endswith(".pdf") and not (approved and entry.get("public_pdf_authorized") is True):
                continue
            shutil.copyfile(safe_file(source,original),folder/target)
            downloads.append({"file":target,"label":label})
    machine=None
    if approved:
        machine=slug+".dxf"
        shutil.copyfile(safe_file(source,dxf),folder/machine)
    specs=public_specs(report)
    item={"id":model_id,"revision":revision,"slug":slug,"name":name,"category":category,
          "status":status if approved or status=="validated_geometry" else "draft",
          "status_label":STATUS[status] if approved or status=="validated_geometry" else STATUS["draft"],
          "machine":machine,"images":images,"specs":specs,"downloads":downloads,
          "render_note":"Renderização ilustrativa ou de estúdio. Conferir medidas e revisão.",
          "dimensions":" × ".join(str(specs[k]) for k in ("Largura (mm)","Altura total (mm)") if k in specs)}
    (folder/"especificacoes.json").write_text(json.dumps(item,ensure_ascii=False,indent=2),encoding="utf-8")
    # Rebuild public ZIP from allowlisted files only; never expose source manifest/evidence.
    bundle=slug+("-producao.zip" if approved else "-revisao.zip")
    payload=sorted(p for p in folder.iterdir() if p.is_file())
    with zipfile.ZipFile(folder/bundle,"w",zipfile.ZIP_DEFLATED) as z:
        for p in payload:
            z.write(p,p.name)
        z.writestr("LEIA-ME.txt",("PRODUÇÃO: conferir revisão, escala e dry-run." if approved else "REVISÃO: não é arquivo de corte.")+"\n")
        z.writestr("SHA256SUMS.txt","".join(digest(p.read_bytes())+"  "+p.name+"\n" for p in payload))
    with zipfile.ZipFile(folder/bundle) as z:
        if z.testzip() is not None:
            raise ValueError("Public bundle CRC failure")
    item["bundle"]=bundle
    item["bundle_bytes"]=(folder/bundle).stat().st_size
    (folder/"index.html").write_text(env.get_template("model.html").render(m=item),encoding="utf-8")
    return item

def build_site(registry,output,*,logo=None):
    registry=Path(registry).resolve()
    output=Path(output).resolve()
    if output.exists():
        raise ValueError("Choose a fresh output directory")
    records=load_json(registry)
    if not isinstance(records,list) or len(records)>500:
        raise ValueError("Expected up to 500 model records")
    env=Environment(loader=FileSystemLoader(PORTAL/"templates"),autoescape=select_autoescape(("html",)))
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent,prefix=".portal-") as tmp:
        stage=Path(tmp)/"site"
        stage.mkdir()
        shutil.copytree(PORTAL/"assets",stage/"assets")
        if logo:
            with Image.open(logo) as im:
                im=im.convert("RGBA")
                im.thumbnail((480,180),Image.Resampling.LANCZOS)
                im.save(stage/"assets"/"logo.png","PNG",optimize=True)
        else:
            # Explicit visual fallback, not a counterfeit logo.
            shutil.copyfile(PORTAL/"assets"/"wordmark.svg",stage/"assets"/"logo.svg")
        logo_name="logo.png" if logo else "logo.svg"
        env.globals["logo_name"]=logo_name
        items=[]
        seen=set()
        for entry in records:
            if entry["id"] in seen:
                raise ValueError("Only one current revision per model is allowed")
            seen.add(entry["id"])
            items.append(write_model(entry,registry.parent,stage,env))
        items.sort(key=lambda x:(not bool(x["machine"]),x["name"].casefold()))
        (stage/"index.html").write_text(env.get_template("index.html").render(models=items,categories=sorted({m["category"] for m in items})),encoding="utf-8")
        (stage/"catalog.json").write_text(json.dumps(items,ensure_ascii=False,indent=2),encoding="utf-8")
        for n in ("robots.txt",".htaccess"):
            shutil.copyfile(PORTAL/n,stage/n)
        inventory={p.relative_to(stage).as_posix():digest(p.read_bytes()) for p in stage.rglob("*") if p.is_file()}
        (stage/"portal-state.json").write_text(json.dumps({"format":1,"files":inventory},sort_keys=True,indent=2),encoding="utf-8")
        stage.rename(output)
    return items
