"""Fetch pinned @google/model-viewer 4.4.0 and Apache-2.0 LICENSE locally.

Eliminates external CDN dependency when bundled into site/assets/ by build_gallery.py,
while preserving lazy on-click loading and the upstream Apache-2.0 license.
"""
import argparse
import hashlib
from pathlib import Path
from urllib.request import Request, urlopen

MODEL_VIEWER_VERSION = "4.4.0"
JS_URL = f"https://ajax.googleapis.com/ajax/libs/model-viewer/{MODEL_VIEWER_VERSION}/model-viewer.min.js"
JS_SHA256 = "18b2e711035aa4705ee281530a55dc2338ff05eed3d70ae16d54105282a75ed5"
LICENSE_URL = "https://raw.githubusercontent.com/google/model-viewer/master/LICENSE"
LICENSE_SHA256 = "cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30"
MAX_BYTES = 4 * 1024 * 1024


def fetch(url, expected_sha256):
    req = Request(url, headers={"User-Agent": "EPS-Portal-Vendor/1"})
    with urlopen(req, timeout=30) as response:
        data = response.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES or not data:
        raise ValueError(f"Unexpected payload size from {url}")
    actual = hashlib.sha256(data).hexdigest()
    if expected_sha256 and actual != expected_sha256:
        raise ValueError(f"SHA256 mismatch for {url}: got {actual}, expected {expected_sha256}")
    return data, actual


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output-dir", type=Path, default=Path("portal_local"))
    a = p.parse_args()
    out = a.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    js_data, js_sha = fetch(JS_URL, JS_SHA256)
    lic_data, lic_sha = fetch(LICENSE_URL, LICENSE_SHA256)
    js_path = out / "model-viewer.min.js"
    lic_path = out / "MODEL-VIEWER-LICENSE.txt"
    js_path.write_bytes(js_data)
    lic_path.write_bytes(lic_data)
    print(f"Saved {js_path} ({len(js_data)} B, sha256={js_sha[:16]}...)")
    print(f"Saved {lic_path} ({len(lic_data)} B, sha256={lic_sha[:16]}...)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
