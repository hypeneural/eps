"""Independent read-only HTTPS verifier for the authenticated private TAP review area.

Confirms:
- Unauthenticated access returns HTTP 401 for HTML, all 9 TAPs, and ZIP
- .htpasswd and .htaccess return HTTP 403 even with valid credentials
- Authenticated access returns HTTP 200, exact SHA-256, exact size, MIME and attachment headers
Does NOT imply physical CNC homologation (use check_mach3_delivery.py for production acceptance).
"""
import argparse
import base64
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import sys
from urllib.error import HTTPError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from epscad.publishing.review_area import OFFLINE_BANNER, local_review_inventory


def fetch(url: str, auth_header: str | None = None):
    headers = {"Cache-Control": "no-cache", "Accept-Encoding": "identity", "User-Agent": "EPS-Review-Check/1"}
    if auth_header:
        headers["Authorization"] = auth_header
    return urlopen(Request(url, headers=headers), timeout=25)


def check_live_review_area(area: Path, base_url: str, username: str, password: str) -> dict:
    area = Path(area)
    base = base_url.rstrip("/")
    u = urlsplit(base)
    if u.scheme != "https" or not u.hostname:
        raise ValueError("A clean HTTPS URL is required")
    inv = local_review_inventory(area)
    manifest = json.loads((area / "review-manifest.json").read_text(encoding="utf-8"))
    auth_header = "Basic " + base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")

    # 1. Verify unauthenticated access is strictly rejected with 401
    must_401 = ["index.html", manifest["bundle"]] + [m["file"] for m in manifest["models"]]
    for m in manifest["models"]:
        must_401.extend([m["animation"], m["animation_data"]])
    must_401.extend(["assets/cut-animation.js", "assets/cut-animation.css"])
    history = json.loads((area/"historicos.json").read_text(encoding="utf-8")) if manifest.get("historical") else None
    history_paths = []
    if history:
        history_paths = ["historicos.html", "historicos.json"]
        for item in history["models"]:
            history_paths.append(item["file"])
            for key in ("preview", "animation", "animation_data"):
                if item.get(key):
                    history_paths.append(item[key])
        must_401.extend(history_paths)
    three_paths = ["assets/"+n for n in ("three.module.min.js","three.core.min.js","OrbitControls.js","THREE-LICENSE.txt","cut-three.js")] if manifest.get("three_available") else []
    must_401.extend(three_paths)
    for rel in must_401:
        target = f"{base}/{quote(rel, safe='/')}"
        try:
            with fetch(target, None):
                raise AssertionError(f"Private resource accessible without auth: {rel}")
        except HTTPError as exc:
            if exc.code != 401:
                raise AssertionError(f"Expected 401 without auth for {rel}, got {exc.code}")

    # 2. Verify control files (.htaccess, .htpasswd) are never downloadable even authenticated
    for secret_file in (".htaccess", ".htpasswd"):
        target = f"{base}/{secret_file}"
        try:
            with fetch(target, auth_header):
                raise AssertionError(f"Server exposes control file: {secret_file}")
        except HTTPError as exc:
            if exc.code not in (403, 404, 410):
                raise AssertionError(f"Unexpected status for {secret_file}: {exc.code}")

    # 3. Verify authenticated index.html, manifest, ZIP, all 9 TAPs, and all 9 simulations
    for rel in ("index.html", "review-manifest.json"):
        with fetch(f"{base}/{rel}", auth_header) as r:
            body = r.read()
            assert r.status == 200 and hashlib.sha256(body).hexdigest() == inv[rel], rel

    zip_rel = manifest["bundle"]
    with fetch(f"{base}/{quote(zip_rel, safe='/')}", auth_header) as r:
        zbytes = r.read()
        assert r.status == 200
        assert "attachment" in r.headers.get("Content-Disposition", "").lower()
        assert len(zbytes) == manifest["bundle_bytes"]
        assert hashlib.sha256(zbytes).hexdigest() == manifest["bundle_sha256"]
        with zipfile.ZipFile(BytesIO(zbytes)) as zf:
            assert zf.testzip() is None
            names = set(zf.namelist())
            for m in manifest["models"]:
                assert m["filename"] in names and hashlib.sha256(zf.read(m["filename"])).hexdigest() == m["sha256"]

    for rel in ["assets/cut-animation.js", "assets/cut-animation.css"]:
        with fetch(f"{base}/{rel}", auth_header) as rr:
            assert rr.status == 200 and hashlib.sha256(rr.read()).hexdigest() == inv[rel], rel
    verified_models = []
    for m in manifest["models"]:
        rel = m["file"]
        tap_url = f"{base}/{quote(rel, safe='/')}"
        with fetch(tap_url, auth_header) as r:
            data = r.read()
            assert r.status == 200
            assert r.headers.get_content_type() == "application/octet-stream", (rel, r.headers.get_content_type())
            assert "attachment" in r.headers.get("Content-Disposition", "").lower()
            assert len(data) == m["bytes"]
            assert hashlib.sha256(data).hexdigest() == m["sha256"]
            assert data.startswith(OFFLINE_BANNER)
        sim_url = f"{base}/{quote(m['preview'], safe='/')}"
        with fetch(sim_url, auth_header) as sr:
            sdata = sr.read()
            assert sr.status == 200 and hashlib.sha256(sdata).hexdigest() == inv[m["preview"]]
        for visual in (m["animation"], m["animation_data"]):
            with fetch(f"{base}/{quote(visual, safe='/')}", auth_header) as ar:
                payload = ar.read()
                assert ar.status == 200 and hashlib.sha256(payload).hexdigest() == inv[visual], visual
                if visual == m["animation_data"]:
                    adata = json.loads(payload)
                    assert adata["tap_sha256"] == m["sha256"], visual
                    assert adata["physical_spacing_mm"] is None, visual
                    assert adata["execution_authorized"] is False, visual
        verified_models.append({
            "animation_verified": True,
            "animation_url": f"{base}/{quote(m['animation'], safe='/')}",
            "id": m["id"],
            "name": m["display_name"],
            "url": tap_url,
            "bytes": len(data),
            "sha256": m["sha256"],
            "http_status_noauth": 401,
            "http_status_auth": 200,
            "content_type": "application/octet-stream",
        })

    for rel in three_paths:
        with fetch(f"{base}/{quote(rel, safe='/')}", auth_header) as tr:
            assert tr.status == 200 and hashlib.sha256(tr.read()).hexdigest() == inv[rel], rel
    for rel in history_paths:
        with fetch(f"{base}/{quote(rel, safe='/')}", auth_header) as hr:
            body = hr.read()
            assert hr.status == 200 and hashlib.sha256(body).hexdigest() == inv[rel], rel
            if rel.endswith(".tap"):
                assert hr.headers.get_content_type() == "application/octet-stream"
                assert "attachment" in hr.headers.get("Content-Disposition", "").lower()
    return {
        "historical_online_verified": history["unique_files"] if history else 0,
        "historical_animations_verified": history["animations"] if history else 0,
        "historical_source_files": history["source_files"] if history else 0,
        "purpose": "private_review_area_https_verification_not_production_homologation",
        "review_area_url": f"{base}/",
        "zip_url": f"{base}/{quote(zip_rel, safe='/')}",
        "zip_bytes": manifest["bundle_bytes"],
        "zip_sha256": manifest["bundle_sha256"],
        "expected": 9,
        "taps_online_verified": len(verified_models),
        "animations_online_verified": sum(m["animation_verified"] for m in verified_models),
        "access_control_401_verified": True,
        "control_files_blocked": True,
        "zip_verified": True,
        "production_homologated": False,
        "models": verified_models,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--area", type=Path, required=True)
    p.add_argument("--url", default="https://eps.etijucas.com.br/conferencia")
    a = p.parse_args()
    user = os.environ.get("EPS_REVIEW_USER")
    password = os.environ.get("EPS_REVIEW_PASSWORD")
    if not user or not password:
        p.error("Set EPS_REVIEW_USER and EPS_REVIEW_PASSWORD in environment")
    result = check_live_review_area(a.area, a.url, user, password)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(
        result["taps_online_verified"] != result["expected"]
        or result["animations_online_verified"] != result["expected"]
        or not result["zip_verified"]
        or not result["access_control_401_verified"]
    )


if __name__ == "__main__":
    raise SystemExit(main())
