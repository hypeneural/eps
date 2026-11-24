import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from epscad.build import build_job
from epscad.loader import load_yaml
from epscad.exporters import write_outputs
from epscad.exporters.integrity import verify_zip,rebuild_zip

class DeliveryTests(unittest.TestCase):
    def test_verify_and_tamper(self):
        spec=load_yaml(ROOT/"projects/exemplos/001_linha_500mm.yaml")
        with tempfile.TemporaryDirectory() as tmp:
            write_outputs(build_job(spec),spec,tmp)
            names=verify_zip(tmp)
            self.assertIn("03_cutpaths_r12.dxf",names)
            (Path(tmp)/"old.tap").write_text("stale")
            self.assertNotIn("old.tap",rebuild_zip(tmp))
            (Path(tmp)/"03_cutpaths_r12.dxf").write_text("broken")
            with self.assertRaises(ValueError):
                verify_zip(tmp)
    def test_catalogs(self):
        for name,width,height in (("tp40_980_sks",980,36),("tp40_1020_isoeste",1020,40)):
            with self.subTest(name=name):
                ref=load_yaml(ROOT/"catalogs/roof_profiles"/(name+".yaml"))
                spec=load_yaml(ROOT/"projects/exemplos/007_tp40_nucleo_eps.yaml")
                spec["cut"]["template_params"]=ref["profile"]
                spec["material"]["stock"]["length_x"]=width
                job=build_job(spec)
                self.assertFalse(job.has_errors,job.validation)
                self.assertAlmostEqual(job.bbox["width"],width)
                self.assertAlmostEqual(job.bbox["height"],height)
                with tempfile.TemporaryDirectory() as tmp:
                    files=write_outputs(job,spec,tmp)
                    self.assertNotIn("dxf_r12",files)
                    self.assertIn("24_eps_core.glb",verify_zip(tmp))
                    self.assertIn("28_eps_normal.png",verify_zip(tmp))

    def test_first_test_cli(self):
        import subprocess
        from epscad.exporters.dxf_validator import validate_dxf
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run([sys.executable,str(ROOT/"scripts/first_test.py"),"--output",tmp],cwd=ROOT,check=True,capture_output=True)
            root=Path(tmp)
            for name in ("calibracao_500mm","trapezio_sintetico_400mm","tp40_980_sks","tp40_1020_isoeste"):
                verify_zip(root/name)
            result=validate_dxf(root/"trapezio_sintetico_400mm"/"03_cutpaths_r12.dxf")
            self.assertEqual(result.entity_count,9)
            self.assertAlmostEqual(result.bbox["width"],400)
            self.assertAlmostEqual(result.bbox["height"],40)
            for name in ("tp40_980_sks","tp40_1020_isoeste"):
                self.assertFalse((root/name/"03_cutpaths_r12.dxf").exists())
    def test_profile_missing_points_is_not_square(self):
        spec=load_yaml(ROOT/"projects/exemplos/008_trapezio_calibracao.yaml")
        spec["cut"]["template_params"]={}
        job=build_job(spec)
        self.assertTrue(job.has_errors)
        self.assertFalse(job.paths)
