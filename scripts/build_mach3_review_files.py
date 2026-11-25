"""Generate nine real TAP files for OFFLINE review from documentary evidence.

No machine connection, physical approval, registry changes or public deployment.
Do not execute these programs on a controller before the machine review.
"""
import argparse
import html
import json
import math
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from epscad.cam.tp40_planner import PORTAL_MODELS,plan_portal_model
from epscad.cam.slab_planner import SLAB_CATALOG,plan_slab_section
from epscad.loader import load_yaml
from epscad.exporters.mach3_tap import sha,canonical
from epscad.exporters.tap_simulator import parse_tap_modal,render_tap_simulation
from recover_cnc_v_evidence import inspect_backup

WARNING="OFFLINE REVIEW ONLY - NOT APPROVED FOR MACHINE EXECUTION"
COMMENT=("("+WARNING+")\r\n").encode("ascii")

def historical_settings(evidence):
    p=evidence["pst_observed"]
    result={}
    for k in ("feed_mm_min","spindle_s","dwell_value"):
        values=p[k]
        if len(values)!=1:
            raise ValueError("Ambiguous documentary setting: "+k)
        v=float(values[0])
        if not math.isfinite(v) or v<=0:
            raise ValueError("Invalid documentary setting: "+k)
        result[k]=v
    if p["dwell_unit"] not in ("seconds","milliseconds"):
        raise ValueError("Unknown documentary dwell unit")
    result["dwell_unit"]=p["dwell_unit"]
    return result

def encode_review(points,settings):
    if len(points)<2 or tuple(points[0])!=(0,0):
        raise ValueError("Missing nominal origin")
    q=[tuple(round(float(v),4) for v in pt) for pt in points]
    if any(len(p)!=2 or any(not math.isfinite(v) or v<0 for v in p) for p in q):
        raise ValueError("Invalid nominal geometry")
    if any(a==b for a,b in zip(q,q[1:])):
        raise ValueError("Duplicate point after quantization")
    # Documentary parameters, not authorized machine settings.
    # Offset and path control are deliberately not selected without evidence.
    lines=["G21 G17 G90 G94 G40 G49 G80",
           "S"+format(settings["spindle_s"],"g"),
           "F"+format(settings["feed_mm_min"],"g"),"M3",
           "G4 P"+format(settings["dwell_value"],"g")]
    lines.extend("G1 X%.4f Y%.4f"%p for p in q[1:])
    lines.extend(["M5","M30"])
    body=("\r\n".join("N%d %s"%((i+1)*5,line) for i,line in enumerate(lines))+"\r\n").encode("ascii")
    parsed=parse_tap_modal(body)
    rebuilt=[tuple(parsed["segments"][0]["start"])]+[tuple(s["end"]) for s in parsed["segments"]]
    if rebuilt!=q or parsed["modal"]["m_sequence"]!=[3,5,30] or parsed["metrics"]["collinear_overlap_mm"]>0.01:
        raise ValueError("Offline path readback failed")
    return COMMENT+body,parsed

def plans():
    for m in PORTAL_MODELS:
        yield m["portal_id"]+"-"+m["revision"],m["name"],plan_portal_model(m["portal_id"])["plan"]
    for v in sorted(load_yaml(SLAB_CATALOG)["variants"]):
        yield v+"-r01",v,plan_slab_section(v)

def build(backup,output):
    evidence=inspect_backup(backup)
    settings=historical_settings(evidence)
    output=Path(output)
    output.mkdir(parents=True,exist_ok=False)
    rows=[]
    for slug,name,plan in plans():
        data,parsed=encode_review(plan["points_mm"],settings)
        folder=output/slug
        folder.mkdir()
        filename=slug+"-NAO-EXECUTAR.tap"
        (folder/filename).write_bytes(data)
        render_tap_simulation(parsed,folder/"simulacao.png",title=name)
        rows.append({"id":slug,"name":name,"file":slug+"/"+filename,
                     "preview":slug+"/simulacao.png","sha256":sha(data),"bytes":len(data),
                     "path_sha256":sha(canonical(plan["points_mm"])),
                     "metrics":parsed["metrics"],"settings_source":"historical_isopor_pst",
                     "production_approved":False,"execution_authorized":False})
    report={"purpose":"offline_review_not_machine_execution","public_authorized":False,
            "production_approved":False,"settings_observed":settings,
            "archive_sha256":evidence["archive_sha256"],"pst_sha256":evidence["pst_sha256"],
            "pending":evidence["pending_physical"],"models":rows}
    (output/"report.json").write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    cards="".join('<article><h2>'+html.escape(r["name"])+'</h2><img loading="lazy" src="'+r["preview"]+'" alt="Trajetoria nominal"><p>Conferencia offline; nao executar na maquina.</p><a download href="'+r["file"]+'">Baixar TAP para conferencia</a><p>'+str(r["bytes"])+' bytes</p></article>' for r in rows)
    (output/"index.html").write_text('<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Iso Nunes | Conferencia privada</title><style>body{font:16px Arial,sans-serif;max-width:1100px;margin:auto;padding:16px;background:#f3f5f6;color:#17232b}header{border-bottom:4px solid #c92512}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px}article{background:white;padding:14px;border:1px solid #ccd4d8;border-radius:8px}img{width:100%}a{display:block;padding:12px;background:#865416;color:white;border-radius:5px;text-align:center}</style><header><h1>Iso Nunes | Conferencia privada</h1><p><strong>NAO EXECUTAR NA MAQUINA. Arquivos sem homologacao fisica.</strong></p><p>Somente analise offline. Nao publicar este diretorio no portal de producao.</p></header><main>'+cards+'</main></html>',encoding="utf-8")
    print(f"{len(rows)} TAPs de conferencia gerados; zero aprovados para execucao.")
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--backup",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    a=p.parse_args()
    build(a.backup,a.output)
if __name__=="__main__":
    main()
