import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"src"),str(ROOT/"scripts")]
from epscad.geometry.slab_reference import section
from prepare_slab_reference import prepare
from epscad.publishing.site import build_site,verified_source

class SlabReferenceTests(unittest.TestCase):
    def test_geometry(self):
        p=section(330,70,25,15)
        self.assertEqual(p.bounds,(0,0,330,70))
        self.assertEqual(p.area,22350)
        for args in ((330,70,165,15),(330,70,25,70),(float("nan"),70,25,15)):
            with self.assertRaises(ValueError):
                section(*args)
    def test_review_gallery_no_machine_program(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)
            source=base/"review"
            report=prepare("capa-laje-h7-1250",source)
            self.assertEqual(report["extrusion_length_mm_assumed"],1250)
            self.assertFalse(report["production_confirmed"])
            self.assertEqual(verified_source(source)[0],"draft")
            self.assertTrue((source/"24_eps_core.glb").is_file())
            reg=base/"registry.json"
            reg.write_text(json.dumps([{"id":"capa-laje-h7-1250","revision":"r01","name":"Capa de laje H7 - conceito recortado","category":"Lajes","source":str(source),"public_authorized":True}]),encoding="utf-8")
            out=base/"site"
            item=build_site(reg,out,viewer_dir=base/"no-vendor")[0]
            self.assertIsNone(item["machine"])
            self.assertEqual(item["specs"]["Rebaixo assumido - largura (mm)"],25)
            self.assertIn("não homologado",item["render_note"])
            with zipfile.ZipFile(out/"modelos"/item["slug"]/item["bundle"]) as z:
                self.assertFalse(any(n.endswith((".tap",".dxf",".nc",".gcode")) for n in z.namelist()))
