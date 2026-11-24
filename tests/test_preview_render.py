from __future__ import annotations

import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from epscad.build import build_job
from epscad.exporters import write_outputs
from epscad.loader import load_yaml


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def load_example(name: str) -> dict:
    return load_yaml(ROOT / "projects" / "exemplos" / name)


class PreviewRenderTests(unittest.TestCase):
    def test_write_outputs_includes_png_preview_for_visual_delivery(self) -> None:
        spec = load_example("001_linha_500mm.yaml")
        job = build_job(spec)

        with tempfile.TemporaryDirectory() as tmp:
            files = write_outputs(job, spec, tmp)
            png_path = Path(files["png_preview"])
            manifest = json.loads(Path(files["manifest"]).read_text(encoding="utf-8"))
            with zipfile.ZipFile(files["package_zip"]) as package:
                names = set(package.namelist())

            self.assertTrue(png_path.exists())
            self.assertEqual(png_path.read_bytes()[:8], PNG_SIGNATURE)
            self.assertGreater(png_path.stat().st_size, 100)
            self.assertEqual(manifest["files"]["png_preview"], "01_preview.png")
            self.assertIn("01_preview.png", names)

    def test_photo_draft_still_gets_png_preview_but_no_dxf(self) -> None:
        spec = load_example("005_foto_bloqueada.yaml")
        job = build_job(spec)

        with tempfile.TemporaryDirectory() as tmp:
            files = write_outputs(job, spec, tmp)
            png_path = Path(files["png_preview"])

            self.assertTrue(png_path.exists())
            self.assertEqual(png_path.read_bytes()[:8], PNG_SIGNATURE)
            self.assertNotIn("dxf_r12", files)

    def test_write_outputs_removes_stale_generated_dxf_when_project_becomes_draft(self) -> None:
        spec = load_example("005_foto_bloqueada.yaml")
        job = build_job(spec)

        with tempfile.TemporaryDirectory() as tmp:
            stale_dxf = Path(tmp) / "03_cutpaths_r12.dxf"
            stale_dxf.write_text("stale dxf", encoding="utf-8")

            files = write_outputs(job, spec, tmp)

            self.assertNotIn("dxf_r12", files)
            self.assertFalse(stale_dxf.exists())


if __name__ == "__main__":
    unittest.main()
