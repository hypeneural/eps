"""Generate separate calibration DXF and two nominal TP40 review packages."""
import argparse
import json
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from epscad.exporters.integrity import verify_zip

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",type=Path,default=ROOT/"outputs"/"primeiro_teste")
    a=p.parse_args()
    out=a.output.resolve()
    out.mkdir(parents=True,exist_ok=True)
    def run(*args):
        subprocess.run([sys.executable,*map(str,args)],cwd=ROOT,check=True)
    cal=out/"calibracao_500mm"
    run(ROOT/"scripts/generate_project.py",ROOT/"projects/exemplos/001_linha_500mm.yaml","--output",cal)
    run(ROOT/"scripts/validate_dxf.py",cal/"03_cutpaths_r12.dxf")
    verify_zip(cal)
    summary={"calibracao_500mm":{"status":"test_only","dxf":str(cal/"03_cutpaths_r12.dxf")}}
    coupon=out/"trapezio_sintetico_400mm"
    run(ROOT/"scripts/generate_project.py",ROOT/"projects/exemplos/008_trapezio_calibracao.yaml","--output",coupon)
    run(ROOT/"scripts/validate_dxf.py",coupon/"03_cutpaths_r12.dxf")
    verify_zip(coupon)
    summary["trapezio_sintetico_400mm"]={"status":"import_test_only","dxf":str(coupon/"03_cutpaths_r12.dxf"),"note":"Synthetic CAD calibration; not a commercial TP40 profile."}
    for variant in ("tp40_980_sks","tp40_1020_isoeste"):
        directory=out/variant
        run(ROOT/"scripts/new_tp40.py",variant,"--output",directory)
        names=verify_zip(directory)
        if any(n.lower().endswith(".dxf") for n in names):
            raise ValueError("Nominal catalog produced DXF")
        summary[variant]={"status":"draft","zip":str(directory/"12_package_for_machine.zip"),"render":str(directory/"26_render_eps.png")}
    (out/"summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    print(out/"summary.json")
    return 0
if __name__=="__main__":
    raise SystemExit(main())
