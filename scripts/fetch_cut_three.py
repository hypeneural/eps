"""Fetch an exact Three.js release into the private local vendor directory.
No dependencies or CDN at runtime. npm verifies the package tarball integrity.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.180.0"
MEMBERS = {"package/build/three.module.min.js": "three.module.min.js",
           "package/build/three.core.min.js": "three.core.min.js",
           "package/examples/jsm/controls/OrbitControls.js": "OrbitControls.js",
           "package/LICENSE": "THREE-LICENSE.txt"}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, default=ROOT/"portal_local"/"cut-three")
    a = p.parse_args()
    npm = shutil.which("npm.cmd") or shutil.which("npm")
    if not npm:
        p.error("npm is required on the development PC only; Canvas remains available")
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run([npm, "pack", "three@"+VERSION, "--ignore-scripts", "--pack-destination", tmp], check=True)
        with tarfile.open(Path(tmp)/("three-"+VERSION+".tgz"), "r:gz") as z:
            a.output.mkdir(parents=True, exist_ok=True)
            hashes = {}
            for member, dest in MEMBERS.items():
                obj = z.getmember(member)
                if not obj.isfile() or obj.size > 5_000_000:
                    raise ValueError("Invalid vendor member")
                data = z.extractfile(obj).read()
                (a.output/dest).write_bytes(data)
                hashes[dest] = hashlib.sha256(data).hexdigest()
            (a.output/"vendor.json").write_text(json.dumps({"version": VERSION, "files": hashes}, indent=2), encoding="utf-8")
    print("Three.js "+VERSION+" vendor ready:", a.output)

if __name__ == "__main__":
    main()
