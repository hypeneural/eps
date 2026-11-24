import argparse
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from epscad.exporters.integrity import verify_zip
def main():
    p=argparse.ArgumentParser(description="Verify manifest, SHA256 and ZIP contents; not production authorization.")
    p.add_argument("directory",type=Path)
    a=p.parse_args()
    print("Verified:",len(verify_zip(a.directory)),"files")
    return 0
if __name__=="__main__":
    raise SystemExit(main())
