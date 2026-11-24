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
