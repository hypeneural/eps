"""Prepare an explicitly reviewed LOCAL trial, before commercial production release.

No changes to machine profile, project status or portal registry.
No network or hardware access. Output is intentionally outside the public package.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from epscad.loader import load_yaml
from epscad.build import build_job
from epscad.exporters.mach3_tap import render_trial_tap,canonical,sha,ordered_points,VERSION
from epscad.exporters.tap_simulator import parse_tap_modal,render_tap_simulation

def prepare_trial(project,profile_path,contract_path,output):
    project=Path(project)
    profile_path=Path(profile_path)
    contract_path=Path(contract_path)
    output=Path(output)
    spec=load_yaml(project)
    profile=load_yaml(profile_path)
    record=json.loads(contract_path.read_text(encoding="utf-8"))
    if set(record)!={"purpose","operator_trial_authorized","contract"} or record["purpose"]!="local_supervised_trial" or record["operator_trial_authorized"] is not True:
        raise ValueError("Explicit local supervised trial authorization required")
    contract=record["contract"]
    if spec.get("project",{}).get("source",{}).get("production_confirmed") is not False:
        raise ValueError("Local trial must not claim production confirmation")
    job=build_job(spec)
    data=render_trial_tap(job,profile,contract)
    parsed=parse_tap_modal(data)
    output.mkdir(parents=True,exist_ok=False)
    filename="TESTE-NAO-HOMOLOGADO.tap"
    (output/filename).write_bytes(data)
    render_tap_simulation(parsed,output/"simulacao.png",title="TESTE LOCAL - NAO HOMOLOGADO")
    report={"purpose":"local_supervised_trial","production_approved":False,"approved":False,
            "tap_approved":False,"public_authorized":False,"machine_file":filename,
            "tap_sha256":sha(data),"project_sha256":sha(project.read_bytes()),
            "profile_sha256":sha(canonical(profile)),"contract_sha256":sha(canonical(contract)),
            "path_sha256":sha(canonical(ordered_points(job))),"postprocessor":VERSION,
            "metrics":parsed["metrics"],"warnings":parsed["warnings"]}
    (output/"relatorio.json").write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    (output/"LEIA-ME.txt").write_text(
        "TESTE LOCAL NAO HOMOLOGADO. Nao publicar nem usar como producao.\n"
        "Verificar hash, simulacao, posicao inicial, estoque, limites e procedimento local.\n"
        "Teste presencial supervisionado com energia do fio fisicamente isolada antes de qualquer corte.\n"
        "A aprovacao comercial e a publicacao sao etapas independentes.\n"
        "Nao renomear este candidato como revisao liberada.\n",encoding="utf-8")
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("project",type=Path)
    p.add_argument("--profile",required=True,type=Path,help="Local measured machine snapshot, not modified by this script")
    p.add_argument("--contract",required=True,type=Path,help="Local reviewed test contract, never public")
    p.add_argument("--output",required=True,type=Path,help="New private directory outside the published snapshot")
    a=p.parse_args()
    prepare_trial(a.project,a.profile,a.contract,a.output)
    print("LOCAL TRIAL ONLY: "+str(a.output/"TESTE-NAO-HOMOLOGADO.tap"))
if __name__=="__main__":
    main()
