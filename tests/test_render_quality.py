import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))


class RenderQualityCliTests(unittest.TestCase):
    def test_help_lists_all_six_views(self):
        res = subprocess.run(
            [sys.executable, str(ROOT / "scripts/render_quality.py"), "--help"],
            check=True,
            capture_output=True,
            text=True,
        )
        for view in (
            "perspective",
            "section_front",
            "microgroove_detail",
            "assembly",
            "exploded",
            "texture_closeup",
        ):
            self.assertIn(view, res.stdout)

    def test_protected_preview_filename_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake_glb = Path(tmp) / "model.glb"
            fake_glb.write_bytes(b"glb")
            fake_blender = Path(tmp) / "blender_stub.exe"
            fake_blender.write_bytes(b"stub")
            res = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/render_quality.py"),
                    "--input",
                    str(fake_glb),
                    "--output",
                    str(Path(tmp) / "26_render_eps.png"),
                    "--blender",
                    str(fake_blender),
                ],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(res.returncode, 0)
            self.assertIn("Do not overwrite hashed preview", res.stderr)

    def test_prepare_tp40_declares_six_cycles_views(self):
        import prepare_tp40

        views = [view for _, _, view in prepare_tp40.CYCLES_VIEWS]
        self.assertEqual(
            views,
            [
                "perspective",
                "section_front",
                "microgroove_detail",
                "assembly",
                "exploded",
                "texture_closeup",
            ],
        )


if __name__ == "__main__":
    unittest.main()
