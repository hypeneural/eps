"""Local evidence only; no extraction, execution or upload."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from epscad.exporters.tap_audit import audit_zip
p=argparse.ArgumentParser(description=__doc__)
p.add_argument("archive",type=Path)
p.add_argument("--output",type=Path,required=True)
if __name__=="__main__":
    a=p.parse_args()
    result=audit_zip(a.archive)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open("x",encoding="utf-8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False)
    print(f'{result["files"]} TAP audited; no production approval')
