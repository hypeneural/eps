from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Create or refresh machine package ZIP from an output directory.")
    parser.add_argument("output_dir")
    args = parser.parse_args()

    out = Path(args.output_dir)
    if not out.exists():
        print(f"output directory not found: {out}", file=sys.stderr)
        return 1
    zip_path = out / "12_package_for_machine.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(out.iterdir()):
            if path.is_file() and path.name != zip_path.name:
                archive.write(path, arcname=path.name)
    print(zip_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
