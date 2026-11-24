"""Build portal locally from explicitly authorized model registry."""
import argparse
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from epscad.publishing.site import build_site

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--registry",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    p.add_argument("--logo",type=Path,help="Local original Iso Nunes PNG")
    a=p.parse_args()
    items=build_site(a.registry,a.output,logo=a.logo)
    print(f"{len(items)} models: {a.output.resolve()}")
if __name__=="__main__":
    main()
