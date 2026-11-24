"""Generate local candidate only from a previously released project and reviewed machine contract."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from epscad.publishing.site import verified_source
from epscad.publishing.tap_release import tap_candidate
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("source",type=Path)
    p.add_argument("--contract",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    _,report,names=verified_source(a.source)
    contract=json.loads(a.contract.read_text(encoding="utf-8"))
    data,hashes=tap_candidate(a.source,report,names,contract)
    a.output.mkdir(parents=True,exist_ok=False)
    # Candidate is local and not approved for machine use by this tool.
    (a.output/"candidate.tap").write_bytes(data)
    (a.output/"approval.json").write_text(json.dumps({"approved":False,"tap_approved":False,"tap_contract":contract,**hashes},indent=2),encoding="utf-8")
    print("LOCAL CANDIDATE ONLY; no publication or machine execution")
if __name__=="__main__": main()
