import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]

from build_mach3_review_files import encode_review, plans
from epscad.exporters.mach3_tap import canonical, sha
from epscad.publishing.cut_animation import BANNER, animation_data
from epscad.publishing.review_area import (
    REVIEW_ZIP,
    build_review_area,
    local_review_inventory,
    make_htpasswd_bytes,
    require_access_control,
)
from epscad.publishing.site import build_site


def _make_fake_review_dir(root: Path) -> Path:
    rdir = root / "review9"
    rdir.mkdir()
    settings = {"feed_mm_min": 600.0, "spindle_s": 300.0, "dwell_value": 3.0, "dwell_unit": "seconds"}
    rows = []
    # Minimal 1x1 PNG bytes for simulation preview
    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc`\x00\x00"
        b"\x00\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    for slug, name, plan in plans():
        data, parsed = encode_review(plan["points_mm"], settings)
        sub = rdir / slug
        sub.mkdir()
        fname = f"{slug}-NAO-EXECUTAR.tap"
        (sub / fname).write_bytes(data)
        (sub / "simulacao.png").write_bytes(png)
        rows.append({
            "id": slug,
            "name": name,
            "file": f"{slug}/{fname}",
            "preview": f"{slug}/simulacao.png",
            "sha256": sha(data),
            "bytes": len(data),
            "path_sha256": sha(canonical(plan["points_mm"])),
            "metrics": parsed["metrics"],
            "settings_source": "historical_isopor_pst",
            "production_approved": False,
            "execution_authorized": False,
        })
    report = {
        "purpose": "offline_review_not_machine_execution",
        "public_authorized": False,
        "production_approved": False,
        "settings_observed": settings,
        "models": rows,
    }
    (rdir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return rdir


class ReviewAreaTests(unittest.TestCase):
    def test_build_nine_review_taps_zip_and_require_basic_auth(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            rdir = _make_fake_review_dir(tmp)
            out_no_auth = tmp / "area_no_auth"
            manifest = build_review_area(rdir, out_no_auth, logo=False)
            self.assertEqual(len(manifest["models"]), 9)
            self.assertFalse(manifest["production_approved"])
            self.assertFalse(manifest["access_controlled"])
            inv = local_review_inventory(out_no_auth)
            self.assertIn(REVIEW_ZIP, inv)
            with self.assertRaisesRegex(ValueError, "requires .htaccess and .htpasswd"):
                require_access_control(out_no_auth)

            out_auth = tmp / "area_auth"
            htpw = make_htpasswd_bytes("conferencia", "SenhaSegura123!")
            manifest_auth = build_review_area(
                rdir,
                out_auth,
                logo=False,
                auth_user_file="/var/www/example/conferencia/.htpasswd",
                htpasswd_bytes=htpw,
            )
            self.assertTrue(manifest_auth["access_controlled"])
            for m in manifest_auth["models"]:
                animation = json.loads((out_auth / m["animation_data"]).read_text(encoding="utf-8"))
                self.assertEqual(animation["tap_sha256"], m["sha256"])
                self.assertEqual(len(animation["segments"]), m["segment_count"])
                self.assertFalse(animation["execution_authorized"])
                self.assertIsNone(animation["physical_spacing_mm"])
                self.assertTrue((out_auth / m["animation"]).is_file())
                reg = animation["regions"]
                self.assertTrue(reg["demonstrable"], m["id"])
                self.assertEqual(reg["kind"], "x_monotone_bbox_partition")
                self.assertFalse(reg["physical_separation_confirmed"])
                self.assertGreater(reg["lower_area_mm2"], 0)
                self.assertGreater(reg["upper_area_mm2"], 0)
                self.assertAlmostEqual(
                    reg["lower_area_mm2"] + reg["upper_area_mm2"],
                    reg["bbox_area_mm2"],
                    delta=0.1,
                )
            # Non-monotone X path must NOT fabricate cut regions
            backtrack_tap = (
                BANNER
                + b"N10 G90 G21\r\n"
                + b"N20 G01 X0.000 Y0.000 F600\r\n"
                + b"N30 G01 X100.000 Y40.000\r\n"
                + b"N40 G01 X50.000 Y80.000\r\n"
                + b"N50 M30\r\n"
            )
            bt_anim = animation_data(backtrack_tap, "bt", "Backtrack", sha(backtrack_tap))
            self.assertFalse(bt_anim["regions"]["demonstrable"])
            self.assertEqual(bt_anim["regions"]["reason"], "non_monotone_x")
            self.assertFalse(bt_anim["regions"]["physical_separation_confirmed"])
            self.assertIn("assets/cut-animation.js", local_review_inventory(out_auth))
            require_access_control(out_auth)
            html = (out_auth / "index.html").read_text(encoding="utf-8")
            self.assertIn("Arquivo disponível", html)
            self.assertIn("BAIXAR ARQUIVO MACH3 (.TAP)", html)
            self.assertNotIn("TAP pendente", html)
            self.assertNotIn("Não disponível", html)
            with zipfile.ZipFile(out_auth / REVIEW_ZIP) as z:
                self.assertIsNone(z.testzip())
                tap_names = [n for n in z.namelist() if n.endswith("-NAO-EXECUTAR.tap")]
                self.assertEqual(len(tap_names), 9)
                self.assertIn("SHA256SUMS.txt", z.namelist())
                self.assertIn("LEIA-ME.txt", z.namelist())

    def test_portal_links_operational_review_tap_never_publico(self):
        import subprocess
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            rdir = _make_fake_review_dir(tmp)
            src = tmp / "tp40_src"
            subprocess.run([sys.executable, str(ROOT / "scripts/prepare_tp40.py"), "--output", str(src)], check=True, capture_output=True)
            reg = tmp / "reg.json"
            reg.write_text(json.dumps([{
                "id": "tp40-base-lisa",
                "revision": "r01",
                "name": "TP40 Base lisa",
                "category": "Telhas",
                "source": str(src),
                "public_authorized": True,
            }]), encoding="utf-8")
            site = tmp / "site"
            item = build_site(reg, site, logo=False, viewer_dir=tmp / "no-vendor", review_manifest=rdir / "report.json")[0]
            self.assertIsNone(item["machine"])
            self.assertEqual(item["review_tap"]["href"], "conferencia/#tp40-base-lisa-r01")
            home = (site / "index.html").read_text(encoding="utf-8")
            detail = (site / "modelos/tp40-base-lisa-r01/index.html").read_text(encoding="utf-8")
            pub = (site / "modelos/tp40-base-lisa-r01/publico.html").read_text(encoding="utf-8")
            self.assertIn("Arquivo disponível", home)
            self.assertIn("BAIXAR ARQUIVO MACH3 (.TAP)", home)
            self.assertNotIn("TAP pendente", home)
            self.assertIn("Arquivo disponível", detail)
            self.assertNotIn("TAP pendente", detail)
            # Public commercial presentation must NEVER mention conferencia or TAP downloads
            self.assertIn("simulacao.html", home)
            self.assertIn("simulacao.html", detail)
            self.assertNotIn("simulacao.html", pub)
            self.assertNotIn("conferencia/", pub)
            self.assertNotIn(".tap", pub.lower())
            self.assertNotIn("download=", pub)


if __name__ == "__main__":
    unittest.main()
