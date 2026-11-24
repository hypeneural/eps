"""Build nominal slab reference packages for gallery review. Never generates machine code."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from PIL import Image,ImageDraw
import trimesh
from epscad.loader import load_yaml
from epscad.geometry.slab_reference import section
from epscad.exporters.roof_3d import mesh_mm,_eps_visual

CATALOG=ROOT/"catalogs/slab_profiles/capa_laje_referencias.yaml"

def drawings(poly,length,stage,model):
    # Orthographic section, and independent illustrative axonometric preview.
    w,h=poly.bounds[2:]
    points=list(poly.exterior.coords)[:-1]
    im=Image.new("RGB",(1200,760),"#f5f6f7")
    d=ImageDraw.Draw(im)
    # Projection uses x,y section coordinates and z extrusion; fit all vertices.
    def raw(x,y,z): return (x+.48*z,-y-.25*z)
    allp=[raw(x,y,z) for x,y in points for z in (0,length)]
    lo=[min(p[i] for p in allp) for i in (0,1)]
    hi=[max(p[i] for p in allp) for i in (0,1)]
    scale=min(1000/(hi[0]-lo[0]),500/(hi[1]-lo[1]))
    def project(x,y,z):
        a,b=raw(x,y,z)
        return (100+(a-lo[0])*scale,110+(b-lo[1])*scale)
    front=[project(x,y,0) for x,y in points]
    back=[project(x,y,length) for x,y in points]
    d.polygon(back,fill="#d8dcde",outline="#a2adb1")
    # Render visible top and right faces; front section remains unoccluded.
    for i,(x,y) in enumerate(points):
        j=(i+1)%len(points)
        xx,yy=points[j]
        if xx-x<0 or yy-y>0:
            d.polygon([front[i],back[i],back[j],front[j]],fill="#eef0ef" if xx-x<0 else "#c9d0d1",outline="#a2adb1")
    d.polygon(front,fill="#fafbf9",outline="#7f9096")
    d.text((40,35),model,fill="#26323b")
    d.text((40,700),"REFERENCIA NOMINAL - NAO HOMOLOGADA",fill="#a14420")
    im.save(stage/"26_render_eps.png")
    im=Image.new("RGB",(1200,620),"white")
    d=ImageDraw.Draw(im)
    k=min(960/w,290/h)
    xy=[(120+x*k,410-y*k) for x,y in points]
    d.polygon(xy,fill="#e7eef0",outline="#33434b",width=3)
    d.text((50,35),model+" | SECAO NOMINAL",fill="#26323b")
    d.line([(120,440),(120+w*k,440)],fill="#33434b",width=2)
    d.text((120,458),f"Largura {w:g} mm | Altura {h:g} mm | Comprimento {length:g} mm",fill="#26323b")
    d.text((50,520),"Rebaixos inferiores simetricos assumidos; confirmar orientacao, medidas e encaixe.",fill="#a14420")
    d.text((50,550),"Sem chanfros adicionais, frisos ou relevo moldado. NAO USAR PARA CORTE.",fill="#a14420")
    im.save(stage/"29_section_review.png")

def prepare(model,output):
    cat=load_yaml(CATALOG)
    spec=cat["variants"][model]
    w,h,length=(spec[k] for k in ("width_mm","height_mm","length_mm"))
    rw,rh=spec["published_fit_mm"]
    poly=section(w,h,rw,rh)
    output=Path(output).resolve()
    if output.exists():
        raise ValueError("Choose a new review directory")
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".slab-review-",dir=output.parent) as tmp:
        stage=Path(tmp)/"review"
        stage.mkdir()
        mesh=mesh_mm(poly,length)
        mesh.export(stage/"20_eps_core_mm.stl")
        (stage/"24_eps_core.glb").write_bytes(trimesh.Scene(_eps_visual(mesh)).export(file_type="glb"))
        drawings(poly,length,stage,model)
        report={"reference_id":model,"review_family":"slab_lajota_reference","status":"draft",
                "production_confirmed":False,"machine_export_allowed":False,
                "width_mm":w,"height_mm":h,"extrusion_length_mm_assumed":length,
                "area_mm2":poly.area,"assumed_rebate_width_mm":rw,"assumed_rebate_height_mm":rh,
                "source_url":cat["sources"][spec["source"]],"source_process":spec["source_process"],
                "geometry_assumption":"Symmetric lower rebates; catalog pair interpreted as width x height. No bevels, molded pattern or structural certification.",
                "render_backend":"CPU_illustrative","note":spec["note"]}
        (stage/"review.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
        (stage/"LEIA-ME.txt").write_text("REVISAO NOMINAL. Sem TAP/DXF. Rebaixos assumidos; conferir desenho e vigota. Sem certificacao estrutural.\n",encoding="utf-8")
        inventory=sorted(stage.iterdir())
        hashes=stage/"SHA256SUMS.txt"
        hashes.write_text("".join(hashlib.sha256(f.read_bytes()).hexdigest()+"  "+f.name+"\n" for f in inventory),encoding="utf-8")
        with zipfile.ZipFile(stage/"EPS_REVISAO.zip","w",compression=zipfile.ZIP_DEFLATED) as z:
            for f in inventory+[hashes]:
                z.write(f,f.name)
        from epscad.publishing.site import verified_source
        verified_source(stage)
        stage.rename(output)
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("model",nargs="?",choices=sorted(load_yaml(CATALOG)["variants"]))
    p.add_argument("--list",action="store_true")
    p.add_argument("--output",type=Path)
    a=p.parse_args()
    if a.list:
        print(json.dumps(load_yaml(CATALOG),ensure_ascii=False,indent=2))
        return
    if not a.model or a.output is None:
        p.error("Model and --output required")
    prepare(a.model,a.output)
    print(a.output)
if __name__=="__main__":
    main()
