import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CatalogCliTests(unittest.TestCase):
    def test_list_distinguishes_microgroove_from_simplified(self):
        res = subprocess.run(
            [sys.executable, str(ROOT / "scripts/generate_catalog.py"), "--list"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        rows = {row["id"]: row for row in json.loads(res.stdout)}
        self.assertEqual(rows["tp40_980_microgroove_review"]["kind"], "microgroove_review")
        self.assertEqual(rows["tp40_980_sks"]["kind"], "trapezoidal_simplified")
        self.assertEqual(rows["tp40_1020_isoeste"]["kind"], "trapezoidal_simplified")

    def test_microgroove_route_preserves_geometry_and_blocks_dxf(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "micro"
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/generate_catalog.py"),
                    "tp40_980_microgroove_review",
                    "--output",
                    str(out),
                    "--thickness",
                    "31",
                    "--length",
                    "1000",
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
            )
            review = json.loads((out / "review.json").read_text(encoding="utf-8"))
            self.assertEqual(review["reference_id"], "tp40_980_microgroove_review")
            self.assertAlmostEqual(review["area_mm2"], 42560.0)
            self.assertIn([58.0, 34.0], review["profile_points_mm"])
            self.assertFalse(any(p.suffix.lower() == ".dxf" for p in out.iterdir()))

    def test_simplified_route_generates_nominal_without_dxf(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "sks"
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/generate_catalog.py"),
                    "tp40_980_sks",
                    "--output",
                    str(out),
                    "--thickness",
                    "30",
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
            )
            manifest = json.loads((out / "06_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["project_id"], "tp40_980_sks")
            self.assertEqual(manifest["production_status"], "draft")
            self.assertFalse((out / "03_cutpaths_r12.dxf").exists())

    def test_unknown_catalog_id_fails(self):
        res = subprocess.run(
            [sys.executable, str(ROOT / "scripts/generate_catalog.py"), "nao_existe"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("Unknown catalog_id", res.stderr)


if __name__ == "__main__":
    unittest.main()
