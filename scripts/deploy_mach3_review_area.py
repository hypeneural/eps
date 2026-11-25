"""Deploy authenticated private Mach3 review area (/conferencia/) via FTPS TLS."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from epscad.publishing.review_area import deploy_review_area, local_review_inventory, require_access_control


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--area", type=Path, required=True, help="Local directory built by build_mach3_review_area.py")
    p.add_argument("--subdir", default="conferencia", help="Dedicated remote subdirectory (default: conferencia)")
    p.add_argument("--execute", action="store_true", help="Without this flag only validates local snapshot and auth rules")
    a = p.parse_args()
    inv = local_review_inventory(a.area)
    require_access_control(a.area)
    if not a.execute:
        print(f"DRY RUN: {len(inv)} verified private review files (Basic Auth enforced); no connection")
        return
    count = deploy_review_area(a.area, remote_subdir=a.subdir)
    print(f"Uploaded and read back ({a.subdir}/): {count}")


if __name__ == "__main__":
    main()
