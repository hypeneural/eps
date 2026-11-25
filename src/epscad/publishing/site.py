"""Build a fresh, sanitized public snapshot from verified EPS outputs."""
from pathlib import Path
import hashlib
import json
import math
import re
import shutil
import tempfile
import zipfile
from urllib.parse import quote
from datetime import datetime, timezone
from PIL import Image
from jinja2 import Environment, FileSystemLoader, select_autoescape
from epscad.exporters.integrity import verify_zip

ROOT=Path(__file__).resolve().parents[3]
PORTAL=ROOT/"portal"
SLUG=re.compile(r"[a-z0-9][a-z0-9-]{0,63}")
PUBLIC_ORIGIN="https://eps.etijucas.com.br"
MAX_ASSET=32*1024*1024
VIEWER_SHA256="18b2e711035aa4705ee281530a55dc2338ff05eed3d70ae16d54105282a75ed5"
VIEWER_LICENSE_SHA256="cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30"
IMAGE_GROUPS=(
    ("perspectiva", "Perspectiva do EPS", ("30_eps_perspective_cycles.png","30_eps_cycles.png","26_render_eps.png","01_preview.png")),
    ("montagem", "Montagem com chapa", ("33_assembly_cycles.png","31_assembly_cycles.png","27_render_assembly.png")),
    ("frontal", "Vista frontal", ("31_section_front_cycles.png",)),
    ("secao", "Desenho técnico", ("29_section_review.png",)),
    ("microdobra", "Detalhe da microdobra", ("32_microgroove_detail_cycles.png",)),
    ("explodida", "Vista explodida", ("34_exploded_cycles.png",)),
    ("textura", "Textura do EPS", ("35_texture_closeup_cycles.png",)),
)
STATUS={"draft":"Em revisão","validated_geometry":"Em homologação","cam_ready":"Em homologação",
        "machine_tested":"Em homologação","production_released":"Liberado para corte",
        "superseded":"Revisão substituída"}
STATUS_CLASS={"draft":"review","validated_geometry":"homologating","cam_ready":"homologating",
              "machine_tested":"homologating","production_released":"ready","superseded":"superseded"}

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
        archive_name="EPS_REVISAO.zip" if report.get("review_family")=="slab_lajota_reference" else "TP40_REVISAO.zip"
        with zipfile.ZipFile(safe_file(source,archive_name)) as z:
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
    tp40=report.get("tp40") or {}
    # Deliberately omit origins, source paths, evidence, macros and machine settings.
    raw={
        "Largura (mm)":report.get("width_mm",tp40.get("panel_width_mm")),
        "Altura total (mm)":report.get("height_mm",tp40.get("core_total_height_mm")),
        "Espessura mínima (mm)":report.get("min_thickness_mm",tp40.get("min_thickness_mm")),
        "Comprimento de referência (mm)":report.get("extrusion_length_mm_assumed",roof.get("length_mm")),
        "Passo (mm)":geom.get("pitch_mm",tp40.get("pitch_mm")),
        "Módulos":geom.get("periods",tp40.get("n_waves")),
        "Microdobra - largura (mm)":geom.get("groove_width_mm"),
        "Microdobra - profundidade (mm)":geom.get("groove_depth_mm"),
        "Área transversal (mm²)":report.get("area_mm2",roof.get("core_area_mm2")),
        "Rebaixo assumido - largura (mm)":report.get("assumed_rebate_width_mm"),
        "Rebaixo assumido - altura (mm)":report.get("assumed_rebate_height_mm"),
        "Extensão X do percurso (mm)":(report.get("bbox_mm") or {}).get("width"),
        "Extensão Y do percurso (mm)":(report.get("bbox_mm") or {}).get("height"),
    }
    def _clean(v):
        r=round(v,4)
        return int(r) if r==int(r) else r
    return {k:_clean(v) for k,v in raw.items() if isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) and v>=0}

def jpeg(src,dest,size,quality,subsampling=2):
    with Image.open(src) as im:
        if im.width*im.height>30_000_000:
            raise ValueError("Oversized image")
        im=im.convert("RGBA")
        im.thumbnail(size,Image.Resampling.LANCZOS)
        canvas=Image.new("RGB",im.size,"white")
        canvas.paste(im,mask=im.getchannel("A"))
        canvas.save(dest,"JPEG",quality=quality,optimize=True,progressive=False,subsampling=subsampling)

def zip_member(z,name,data):
    # Fixed metadata: re-building the same revision yields the same ZIP hash.
    info=zipfile.ZipInfo(name,date_time=(2000,1,1,0,0,0))
    info.compress_type=zipfile.ZIP_DEFLATED
    info.external_attr=0o644<<16
    z.writestr(info,data)

def load_review_tap_index(manifest_path):
    """Read and verify locally generated offline review TAPs for linking to the private area."""
    p=Path(manifest_path).resolve()
    report=load_json(p)
    if report.get("purpose")!="offline_review_not_machine_execution" or report.get("production_approved") is not False:
        raise ValueError("Invalid offline review manifest")
    index={}
    for m in report.get("models") or []:
        slug=m["id"]
        tap_file=(p.parent/m["file"]).resolve()
        if not tap_file.is_file():
            raise FileNotFoundError("Missing review TAP file: "+str(tap_file))
        data=tap_file.read_bytes()
        if not data or digest(data)!=m["sha256"] or len(data)!=m["bytes"]:
            raise ValueError("Review TAP checksum mismatch: "+slug)
        index[slug]={"bytes":len(data),"sha256_short":m["sha256"][:12],"filename":tap_file.name}
    return index

def write_model(entry,base,stage,env,*,review_tap=None,review_area_url="conferencia/"):
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
    dxf="03_cutpaths_r12.dxf"
    approved=False
    tap_data=None
    if status=="production_released":
        from epscad.publishing.release import candidate_hashes
        expected=candidate_hashes(source,report,verified)
        release=entry.get("release") or {}
        if release.get("approved") is not True or any(release.get(k)!=v for k,v in expected.items()):
            raise ValueError("Production requires explicit DXF, project and machine profile hash approval")
        if release.get("tap_approved") is True:
            from epscad.publishing.tap_release import approved_tap
            tap_data=approved_tap(source,report,verified,release)
        if entry.get("require_tap") is True and tap_data is None:
            raise ValueError("Mach3 model requires approved TAP; DXF fallback is not allowed")
        approved=True
    slug=model_id+"-"+revision
    folder=stage/"modelos"/slug
    folder.mkdir(parents=True)
    images=[]
    for key,label,candidates in IMAGE_GROUPS:
        selected=next((f for f in candidates if f in verified),None)
        if selected:
            if key=="secao":
                jpeg(safe_file(source,selected),folder/(key+".jpg"),(1800,1200),92,subsampling=0)
            else:
                jpeg(safe_file(source,selected),folder/(key+".jpg"),(1400,1000),86)
            jpeg(safe_file(source,selected),folder/(key+"-thumb.jpg"),(240,160),72)
            images.append({"file":key+".jpg","thumb":key+"-thumb.jpg","label":label})
            if len(images)==1:
                jpeg(safe_file(source,selected),folder/"thumb.jpg",(420,280),76)
    if not images:
        raise ValueError("No verified preview")
    downloads=[]
    if "29_section_review.png" in verified:
        shutil.copyfile(safe_file(source,"29_section_review.png"),folder/"desenho-tecnico.png")
        downloads.append({"file":"desenho-tecnico.png","label":"Desenho técnico (PNG, conferência)"})
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
        if tap_data is not None:
            machine=slug+".tap"
            (folder/machine).write_bytes(tap_data)
            if entry.get("public_cam_dxf_authorized") is True and dxf in verified:
                cam_dxf=slug+".dxf"
                shutil.copyfile(safe_file(source,dxf),folder/cam_dxf)
                downloads.append({"file":cam_dxf,"label":"Desenho CAM (DXF R12 · referência técnica)"})
        else:
            machine=slug+".dxf"
            shutil.copyfile(safe_file(source,dxf),folder/machine)
    specs=public_specs(report)
    effective_status="production_released" if approved else (status if status in ("validated_geometry","cam_ready","machine_tested") else "draft")
    raw_history=entry.get("revision_history") or []
    history=[]
    for h in raw_history[:20]:
        if isinstance(h,dict) and re.fullmatch(r"r[0-9]{2,5}",str(h.get("revision",""))):
            history.append({"revision":str(h["revision"]),"status_label":STATUS["superseded"],"note":str(h.get("note",""))[:160]})
    item={"id":model_id,"revision":revision,"slug":slug,"name":name,"category":category,
          "status":effective_status,
          "status_label":STATUS[effective_status],
          "status_class":STATUS_CLASS[effective_status],
          "machine":machine,"machine_format":"TAP" if tap_data is not None else ("DXF" if machine else None),"images":images,"specs":specs,"downloads":downloads,
          "history":history,"public_page":"publico.html",
          "render_note":("Conceito recortado. Rebaixos assumidos, sem relevo moldado. Conferir encaixe e medidas; não homologado." if report.get("review_family")=="slab_lajota_reference" else "Renderização ilustrativa ou de estúdio. Conferir medidas e revisão."),
          "dimensions":" × ".join(str(specs[k]) for k in ("Largura (mm)","Altura total (mm)") if k in specs)}
    (folder/"especificacoes.json").write_text(json.dumps(item,ensure_ascii=False,indent=2),encoding="utf-8")
    # Rebuild public ZIP from allowlisted files only; never expose source manifest/evidence.
    bundle=slug+("-producao.zip" if approved else "-revisao.zip")
    payload=sorted(p for p in folder.iterdir() if p.is_file())
    with zipfile.ZipFile(folder/bundle,"w",zipfile.ZIP_DEFLATED) as z:
        for p in payload:
            zip_member(z,p.name,p.read_bytes())
        zip_member(z,"LEIA-ME.txt",(("PRODUÇÃO: TAP para Mach3; conferir revisão e procedimento local." if tap_data is not None else "PRODUÇÃO: DXF para CAM; conferir revisão, escala e dry-run.") if approved else "REVISÃO: não é arquivo de corte.")+"\n")
        zip_member(z,"SHA256SUMS.txt","".join(digest(p.read_bytes())+"  "+p.name+"\n" for p in payload))
    with zipfile.ZipFile(folder/bundle) as z:
        if z.testzip() is not None:
            raise ValueError("Public bundle CRC failure")
    item["bundle"]=bundle
    item["bundle_bytes"]=(folder/bundle).stat().st_size
    # Share the presentation, never the operational or machine download address.
    # Keep social metadata outside the already-built production ZIP.
    item["public_url"]=PUBLIC_ORIGIN+"/modelos/"+slug+"/"+item["public_page"]
    message="Conheça "+name+" | Iso Nunes — Indústria de EPS.\nVeja imagens, medidas e modelo 3D:\n"+item["public_url"]
    item["whatsapp_url"]="https://wa.me/?text="+quote(message,safe="")
    if machine:
        item["machine_bytes"]=(folder/machine).stat().st_size
        item["machine_sha256"]=digest((folder/machine).read_bytes())
        if not item["machine_bytes"]:
            raise ValueError("Empty machine download")
    elif review_tap:
        # Operational pointer only to the authenticated private review area; never exposed in publico.html.
        item["review_tap"]={"bytes":review_tap["bytes"],"sha256_short":review_tap["sha256_short"],
                            "href":review_area_url.rstrip("/")+"/#"+slug}
    (folder/"index.html").write_text(env.get_template("model.html").render(m=item),encoding="utf-8")
    # Presentation receives a deliberately reduced projection, not the operator metadata.
    public_spec_keys=("Largura (mm)","Altura total (mm)","Espessura mínima (mm)",
                      "Comprimento de referência (mm)","Passo (mm)","Módulos",
                      "Microdobra - largura (mm)","Microdobra - profundidade (mm)",
                      "Área transversal (mm²)","Rebaixo assumido - largura (mm)",
                      "Rebaixo assumido - altura (mm)")
    presentation={k:item[k] for k in ("name","category","revision","images","render_note","public_url","whatsapp_url")}
    social_img_path=folder/images[0]["file"]
    with Image.open(social_img_path) as sim:
        social_w,social_h=sim.size
    presentation["social_image"]=PUBLIC_ORIGIN+"/modelos/"+slug+"/"+images[0]["file"]
    presentation["social_image_width"]=social_w
    presentation["social_image_height"]=social_h
    dim_tag=f" ({item['dimensions']} mm)" if item["dimensions"] else ""
    presentation["social_description"]=f"{name}{dim_tag} — EPS (poliestireno expandido). Veja imagens, medidas e visualização 3D na Iso Nunes."
    presentation["specs"]={k:specs[k] for k in public_spec_keys if k in specs}
    presentation["dimension_note"]="Medidas nominais de referência. Confirmar encaixe e aplicação." if not approved else "Dimensões da revisão apresentada. Confirmar adequação à aplicação."
    view_models=[{"file":f["file"],"label":("Peça em EPS" if f["file"]=="modelo.glb" else "Montagem com chapa")} for f in downloads if f["file"] in ("modelo.glb","montagem.glb")]
    (folder/item["public_page"]).write_text(env.get_template("public_model.html").render(m=presentation,view_models=view_models),encoding="utf-8")
    return item

def build_site(registry,output,*,logo=None,viewer_dir=None,review_manifest=None,review_area_url="conferencia/"):
    registry=Path(registry).resolve()
    output=Path(output).resolve()
    if output.exists():
        raise ValueError("Choose a fresh output directory")
    review_index=load_review_tap_index(review_manifest) if review_manifest else {}
    records=load_json(registry)
    if not isinstance(records,list) or len(records)>500:
        raise ValueError("Expected up to 500 model records")
    env=Environment(loader=FileSystemLoader(PORTAL/"templates"),autoescape=select_autoescape(("html",)))
    if logo is None and (ROOT/"portal_local/logo-isonunes.png").is_file():
        logo=ROOT/"portal_local/logo-isonunes.png"
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
        vdir=Path(viewer_dir) if viewer_dir is not None else (ROOT/"portal_local")
        local_mv=vdir/"model-viewer.min.js"
        local_mv_lic=vdir/"MODEL-VIEWER-LICENSE.txt"
        has_local_viewer=local_mv.is_file() and local_mv_lic.is_file()
        if has_local_viewer:
            if local_mv.is_symlink() or local_mv_lic.is_symlink() or digest(local_mv.read_bytes())!=VIEWER_SHA256 or digest(local_mv_lic.read_bytes())!=VIEWER_LICENSE_SHA256:
                raise ValueError("Local model-viewer integrity mismatch; run fetch_model_viewer.py again")
            shutil.copyfile(local_mv,stage/"assets/model-viewer.min.js")
            shutil.copyfile(local_mv_lic,stage/"assets/MODEL-VIEWER-LICENSE.txt")
        env.globals["local_viewer"]=has_local_viewer
        env.globals["review_area_url"]=review_area_url if review_index else None
        from epscad.publishing.brand import write_brand
        write_brand(stage/"assets"/"brand.css",stage/"assets"/"logo.png" if logo else None)
        items=[]
        seen=set()
        for entry in records:
            if entry["id"] in seen:
                raise ValueError("Only one current revision per model is allowed")
            seen.add(entry["id"])
            slug=entry["id"]+"-"+entry["revision"]
            items.append(write_model(entry,registry.parent,stage,env,review_tap=review_index.get(slug),review_area_url=review_area_url))
        items.sort(key=lambda x:(not bool(x["machine"]),x["name"].casefold()))
        (stage/"index.html").write_text(env.get_template("index.html").render(models=items,categories=sorted({m["category"] for m in items})),encoding="utf-8")
        (stage/"catalog.json").write_text(json.dumps(items,ensure_ascii=False,indent=2),encoding="utf-8")
        for n in ("robots.txt",".htaccess"):
            shutil.copyfile(PORTAL/n,stage/n)
        inventory={p.relative_to(stage).as_posix():digest(p.read_bytes()) for p in stage.rglob("*") if p.is_file()}
        (stage/"portal-state.json").write_text(json.dumps({"format":1,"files":inventory},sort_keys=True,indent=2),encoding="utf-8")
        stage.rename(output)
    return items
