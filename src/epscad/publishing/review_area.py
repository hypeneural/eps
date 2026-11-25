"""Build and deploy an authenticated private online review area for Mach3 TAPs.

Strictly separated from:
- Public commercial presentation pages (publico.html)
- Commercially homologated production releases (portal-state.json / --allow-production)
Never exposes factory backups, XML, PST, macros or credentials.
"""
from __future__ import annotations

import base64
from ftplib import FTP_TLS, error_perm
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import ssl
import tempfile
import uuid
import zipfile
from jinja2 import Environment, FileSystemLoader, select_autoescape
from PIL import Image

from epscad.publishing.site import PORTAL, ROOT, digest, zip_member

REVIEW_STATE = "review-state.json"
REVIEW_ZIP = "isonunes-taps-conferencia-9-modelos.zip"
OFFLINE_BANNER = b"(OFFLINE REVIEW ONLY - NOT APPROVED FOR MACHINE EXECUTION)\r\n"
REVIEW_PATH = re.compile(
    r"(?:index\.html|review-manifest\.json|\.htaccess|\.htpasswd|"
    r"isonunes-taps-conferencia-9-modelos\.zip|"
    r"assets/[A-Za-z0-9_.-]+|"
    r"[a-z0-9-]+/(?:[a-z0-9-]+-NAO-EXECUTAR\.tap|simulacao\.(?:png|json|html)))"
)

DISPLAY_META = {
    "tp40-base-lisa-r01": ("TP40 Base lisa", "Telhas"),
    "tp40-base-lisa-50mm-r01": ("TP40 Base lisa 50 mm", "Telhas"),
    "tp40-980-sks-30mm-r01": ("TP40/980 Comercial 30 mm (Ref. SKS)", "Telhas"),
    "tp40-980-sks-50mm-r01": ("TP40/980 Comercial 50 mm (Ref. SKS)", "Telhas"),
    "tp40-1020-isoeste-30mm-r01": ("TP40/1020 Comercial 30 mm (Ref. Isoeste)", "Telhas"),
    "capa-laje-h7-1000-r01": ("Capa de Laje EPS H7 (1000×330 mm)", "Lajes"),
    "capa-laje-h7-1250-r01": ("Capa de Laje EPS H7 (1250×330 mm)", "Lajes"),
    "capa-laje-h8-1000-r01": ("Capa de Laje EPS H8 (1000×330 mm)", "Lajes"),
    "capa-laje-h12-1000-r01": ("Capa de Laje EPS H12 (1000×330 mm)", "Lajes"),
}


def make_htpasswd_bytes(username: str, password: str) -> bytes:
    if not re.fullmatch(r"[A-Za-z0-9_.-]{3,64}", username):
        raise ValueError("Invalid review area username")
    if len(password) < 8 or any(ch in password for ch in ("\r", "\n", ":")):
        raise ValueError("Review area password must have at least 8 printable characters without ':'")
    sha1 = base64.b64encode(hashlib.sha1(password.encode("utf-8")).digest()).decode("ascii")
    return f"{username}:{{SHA}}{sha1}\n".encode("ascii")


def render_htaccess(auth_user_file: str | None) -> str:
    lines = [
        "Options -Indexes",
        "AddType application/octet-stream .tap",
    ]
    if auth_user_file:
        if any(ch in auth_user_file for ch in ('"', "\r", "\n")):
            raise ValueError("Invalid AuthUserFile path")
        lines.extend([
            "AuthType Basic",
            'AuthName "Iso Nunes - Area Privada TAP"',
            f'AuthUserFile "{auth_user_file}"',
            "Require valid-user",
        ])
    lines.extend([
        "<IfModule mod_headers.c>",
        '  Header always set X-Content-Type-Options "nosniff"',
        '  Header always set X-Robots-Tag "noindex, nofollow"',
        '  Header always set Referrer-Policy "no-referrer"',
        '  Header always set X-Frame-Options "SAMEORIGIN"',
        '  <FilesMatch "\\.(tap|zip)$">',
        '    Header set Content-Disposition "attachment"',
        "  </FilesMatch>",
        '  <FilesMatch "\\.(html|json|tap|zip)$">',
        '    Header set Cache-Control "no-store"',
        "  </FilesMatch>",
        "</IfModule>",
        '<FilesMatch "^\\.(ht|eps-upload-)">',
        "  Require all denied",
        "</FilesMatch>",
        "",
    ])
    return "\n".join(lines)


def _clean_num(v: float) -> str:
    r = round(float(v), 1)
    return str(int(r)) if r == int(r) else f"{r:.1f}".replace(".", ",")


def build_review_area(
    review_dir: Path | str,
    output: Path | str,
    *,
    logo: Path | str | None = None,
    auth_user_file: str | None = None,
    htpasswd_bytes: bytes | None = None,
) -> dict:
    review_dir = Path(review_dir).resolve()
    output = Path(output).resolve()
    if output.exists():
        raise ValueError("Choose a fresh output directory")
    report_path = review_dir / "report.json"
    if not report_path.is_file():
        raise FileNotFoundError(f"Missing review report: {report_path}")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("purpose") != "offline_review_not_machine_execution" or report.get("production_approved") is not False:
        raise ValueError("Expected offline review report")
    raw_models = report.get("models") or []
    if not raw_models:
        raise ValueError("No review models found")
    if htpasswd_bytes is not None and not auth_user_file:
        raise ValueError("htpasswd requires auth_user_file")

    if logo is None and (ROOT / "portal_local/logo-isonunes.png").is_file():
        logo = ROOT / "portal_local/logo-isonunes.png"

    env = Environment(loader=FileSystemLoader(PORTAL / "templates"), autoescape=select_autoescape(("html",)))
    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(dir=output.parent, prefix=".review-area-") as tmp:
        stage = Path(tmp) / "area"
        stage.mkdir()
        assets_dir = stage / "assets"
        assets_dir.mkdir()
        for asset in ("style.css", "eps-pattern.svg", "cut-animation.js", "cut-animation.css"):
            shutil.copyfile(PORTAL / "assets" / asset, assets_dir / asset)
        if logo:
            with Image.open(logo) as im:
                im = im.convert("RGBA")
                im.thumbnail((480, 180), Image.Resampling.LANCZOS)
                im.save(assets_dir / "logo.png", "PNG", optimize=True)
            logo_name = "logo.png"
        else:
            shutil.copyfile(PORTAL / "assets/wordmark.svg", assets_dir / "logo.svg")
            logo_name = "logo.svg"
        from epscad.publishing.brand import write_brand
        write_brand(assets_dir / "brand.css", assets_dir / "logo.png" if logo else None)

        entries = []
        zip_files: list[tuple[str, bytes]] = []
        for m in raw_models:
            slug = m["id"]
            if not re.fullmatch(r"[a-z0-9-]+", slug):
                raise ValueError(f"Invalid review slug: {slug}")
            tap_src = (review_dir / m["file"]).resolve()
            sim_src = (review_dir / m["preview"]).resolve()
            if not tap_src.is_file() or not sim_src.is_file():
                raise FileNotFoundError(f"Missing review artifact for {slug}")
            tap_bytes = tap_src.read_bytes()
            if not tap_bytes.startswith(OFFLINE_BANNER):
                raise ValueError(f"Offline review banner missing in {tap_src.name}")
            if digest(tap_bytes) != m["sha256"] or len(tap_bytes) != m["bytes"]:
                raise ValueError(f"Review TAP checksum mismatch for {slug}")
            dest_dir = stage / slug
            dest_dir.mkdir()
            filename = f"{slug}-NAO-EXECUTAR.tap"
            (dest_dir / filename).write_bytes(tap_bytes)
            shutil.copyfile(sim_src, dest_dir / "simulacao.png")
            from epscad.publishing.cut_animation import animation_data
            animation = animation_data(tap_bytes, slug, m["name"], m["sha256"])
            (dest_dir / "simulacao.json").write_text(json.dumps(animation, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
            zip_files.append((filename, tap_bytes))

            disp_name, category = DISPLAY_META.get(slug, (m["name"], "Outros"))
            bb = m["metrics"]["bbox_mm"]
            entries.append({
                "id": slug,
                "display_name": disp_name,
                "category": category,
                "filename": filename,
                "file": f"{slug}/{filename}",
                "preview": f"{slug}/simulacao.png",
                "animation": f"{slug}/simulacao.html",
                "animation_data": f"{slug}/simulacao.json",
                "bytes": len(tap_bytes),
                "sha256": m["sha256"],
                "path_sha256": m["path_sha256"],
                "width_mm": _clean_num(bb["width"]),
                "height_mm": _clean_num(bb["height"]),
                "segment_count": m["metrics"]["segment_count"],
                "total_length_mm": _clean_num(m["metrics"]["total_length_mm"]),
                "overlap_mm": _clean_num(m["metrics"]["collinear_overlap_mm"]),
                "production_approved": False,
                "execution_authorized": False,
            })

        for entry in entries:
            (stage / entry["animation"]).write_text(env.get_template("cut_animation.html").render(m=entry, logo_name=logo_name), encoding="utf-8")

        entries.sort(key=lambda r: (0 if r["category"] == "Telhas" else 1, r["display_name"].casefold()))

        zip_path = stage / REVIEW_ZIP
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            for fname, fbytes in sorted(zip_files):
                zip_member(z, fname, fbytes)
            readme_txt = (
                "ISO NUNES - PACOTE PRIVADO DE CONFERENCIA MACH3 (.TAP)\n"
                f"Modelos incluidos: {len(zip_files)}\n"
                "AVISO: Arquivos gerados para conferencia tecnica offline.\n"
                "NAO possuem homologacao fisica na maquina SCARA CNC_V.\n"
                "Preservam comentario interno (OFFLINE REVIEW ONLY - NOT APPROVED FOR MACHINE EXECUTION).\n"
                "A homologacao industrial e a liberacao comercial permanecem etapas independentes.\n"
            ).encode("utf-8")
            sums_txt = "".join(f"{digest(b)}  {n}\n" for n, b in sorted(zip_files)).encode("utf-8")
            zip_member(z, "LEIA-ME.txt", readme_txt)
            zip_member(z, "SHA256SUMS.txt", sums_txt)
        with zipfile.ZipFile(zip_path) as z:
            if z.testzip() is not None:
                raise ValueError("Review ZIP CRC failure")
        bundle_bytes = zip_path.stat().st_size
        bundle_sha256 = digest(zip_path.read_bytes())

        manifest = {
            "purpose": "private_online_review_area_not_production",
            "production_approved": False,
            "execution_authorized": False,
            "access_controlled": bool(auth_user_file and htpasswd_bytes),
            "bundle": REVIEW_ZIP,
            "bundle_bytes": bundle_bytes,
            "bundle_sha256": bundle_sha256,
            "settings_observed": report["settings_observed"],
            "models": entries,
        }
        (stage / "review-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        html_out = env.get_template("review_area.html").render(
            logo_name=logo_name,
            models=entries,
            bundle=REVIEW_ZIP,
            bundle_bytes=bundle_bytes,
            settings=report["settings_observed"],
        )
        (stage / "index.html").write_text(html_out, encoding="utf-8")
        (stage / ".htaccess").write_text(render_htaccess(auth_user_file), encoding="utf-8")
        if htpasswd_bytes is not None:
            (stage / ".htpasswd").write_bytes(htpasswd_bytes)

        files_inv = {p.relative_to(stage).as_posix(): digest(p.read_bytes()) for p in stage.rglob("*") if p.is_file()}
        validate_review_state({"format": 1, "files": files_inv})
        (stage / REVIEW_STATE).write_text(json.dumps({"format": 1, "files": files_inv}, sort_keys=True, indent=2), encoding="utf-8")
        shutil.move(str(stage), str(output))
    return manifest


def validate_review_state(state: dict) -> dict[str, str]:
    if state.get("format") != 1 or not isinstance(state.get("files"), dict) or len(state["files"]) > 500:
        raise ValueError("Invalid review area state")
    for name, checksum in state["files"].items():
        if not REVIEW_PATH.fullmatch(name) or any(p in (".", "..") for p in PurePosixPath(name).parts) or not re.fullmatch("[0-9a-f]{64}", checksum):
            raise ValueError("Invalid review area inventory path: " + name)
    return state["files"]


def local_review_inventory(root: Path | str) -> dict[str, str]:
    root = Path(root)
    files = validate_review_state(json.loads((root / REVIEW_STATE).read_text(encoding="utf-8")))
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    if actual != set(files) | {REVIEW_STATE}:
        raise ValueError("Unexpected local review area files")
    for name, checksum in files.items():
        p = root / name
        if p.is_symlink() or digest(p.read_bytes()) != checksum:
            raise ValueError("Local review area integrity mismatch: " + name)
    return files


def require_access_control(root: Path | str) -> None:
    root = Path(root)
    ht_path = root / ".htaccess"
    pw_path = root / ".htpasswd"
    if not ht_path.is_file() or not pw_path.is_file():
        raise ValueError("Private review area deployment requires .htaccess and .htpasswd")
    ht = ht_path.read_text(encoding="utf-8")
    if "AuthType Basic" not in ht or "Require valid-user" not in ht or "AuthUserFile" not in ht:
        raise ValueError("Private review area .htaccess must enforce HTTP Basic Auth")
    if not pw_path.read_text(encoding="ascii").strip():
        raise ValueError("Empty .htpasswd file")


def deploy_review_area(root: Path | str, *, remote_subdir: str = "conferencia") -> int:
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{1,31}", remote_subdir):
        raise ValueError("Invalid remote_subdir")
    root = Path(root)
    current = local_review_inventory(root)
    require_access_control(root)

    host = os.environ["EPS_FTP_HOST"]
    user = os.environ["EPS_FTP_USER"]
    password = os.environ["EPS_FTP_PASSWORD"]
    remote_root = os.environ["EPS_FTP_REMOTE_ROOT"]
    if not remote_root.strip() or not password:
        raise ValueError("Explicit remote root and FTPS password required")

    from epscad.publishing.deploy import ensure_dirs, read_remote, remote_names, remove, upload

    def open_session() -> FTP_TLS:
        conn = FTP_TLS(context=ssl.create_default_context(), timeout=40)
        conn.connect(host, int(os.getenv("EPS_FTP_PORT", "21")))
        conn.login(user, password)
        conn.prot_p()
        conn.cwd(remote_root)
        try:
            conn.cwd(remote_subdir)
        except error_perm:
            conn.mkd(remote_subdir)
            conn.cwd(remote_subdir)
        return conn

    def close_session(conn: FTP_TLS) -> None:
        for fn in (getattr(conn, "quit", None), getattr(conn, "close", None)):
            if callable(fn):
                try:
                    fn()
                    return
                except (error_perm, OSError):
                    pass

    ftp = open_session()
    reconnects = 0
    try:
        previous: dict[str, str] = {}
        if REVIEW_STATE in remote_names(ftp):
            previous = validate_review_state(json.loads(read_remote(ftp, REVIEW_STATE, 1024 * 1024)))
        # Upload .htpasswd and .htaccess FIRST so no TAP file is ever reachable unauthenticated!
        priority = lambda n: (0 if n == ".htpasswd" else 1 if n == ".htaccess" else 2 if n != "index.html" else 3, n)
        for name in sorted(current, key=priority):
            for attempt in range(2):
                try:
                    if previous.get(name) == current[name]:
                        try:
                            if digest(read_remote(ftp, name)) == current[name]:
                                break
                        except error_perm:
                            pass
                    upload(ftp, name, (root / name).read_bytes())
                    break
                except (OSError, EOFError):
                    if attempt == 1 or reconnects >= 6:
                        raise
                    reconnects += 1
                    close_session(ftp)
                    ftp = open_session()
        stale = sorted(previous.keys() - current.keys())
        for name in stale:
            remove(ftp, name)
        upload(ftp, REVIEW_STATE, (root / REVIEW_STATE).read_bytes())
    finally:
        close_session(ftp)
    return len(current)
