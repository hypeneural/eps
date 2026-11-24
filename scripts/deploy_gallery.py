"""Deploy only after local review and explicit authorization. No credentials in arguments."""
import argparse
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from epscad.publishing.deploy import deploy,local_inventory

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--site",type=Path,required=True)
    p.add_argument("--initialize",action="store_true")
    p.add_argument("--allow-production",action="store_true")
    p.add_argument("--execute",action="store_true",help="Without this flag only validates local snapshot")
    a=p.parse_args()
    if not a.execute:
        print("DRY RUN:",len(local_inventory(a.site)),"verified files; no connection")
        return
    print("Uploaded and read back:",deploy(a.site,initialize=a.initialize,allow_production=a.allow_production))
if __name__=="__main__":
    main()
