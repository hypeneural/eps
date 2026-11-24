import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from epscad.publishing.site import build_site
from epscad.publishing.deploy import local_inventory,check_revision,validate_state

class PublishingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.base=Path(cls.tmp.name)
        subprocess.run([sys.executable,str(ROOT/"scripts/prepare_tp40.py"),"--output",str(cls.base/"source")],check=True,capture_output=True)
        cls.entry={"id":"tp40-base-lisa","revision":"r01","name":"TP40 <teste>","category":"Telhas","source":"source","public_authorized":True}
    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()
    def registry(self,records):
        p=self.base/"registry.json"
        p.write_text(json.dumps(records),encoding="utf-8")
        return p
    def test_real_review_gallery(self):
        out=self.base/"site"
        items=build_site(self.registry([self.entry]),out)
        self.assertEqual(items[0]["specs"]["Área transversal (mm²)"],42560)
        self.assertIsNone(items[0]["machine"])
        page=(out/"index.html").read_text(encoding="utf-8")
        self.assertIn("TP40 &lt;teste&gt;",page)
        self.assertNotIn("Baixar DXF de corte",page)
        self.assertIn("Corte não liberado",page)
        self.assertNotIn("model-viewer.min.js",page)
        folder=out/"modelos/tp40-base-lisa-r01"
        self.assertTrue((folder/"modelo.glb").exists())
        self.assertLess((folder/"thumb.jpg").stat().st_size,100000)
        self.assertNotIn("historical_evidence",(folder/"especificacoes.json").read_text(encoding="utf-8"))
        with zipfile.ZipFile(folder/items[0]["bundle"]) as z:
            self.assertNotIn("review.json",z.namelist())
            self.assertFalse(any(n.endswith((".dxf",".tap",".xml",".pst")) for n in z.namelist()))
        self.assertIn("index.html",local_inventory(out))
        (folder/"thumb.jpg").write_bytes(b"changed")
        with self.assertRaises(ValueError):
            local_inventory(out)
    def test_no_public_permission(self):
        with self.assertRaises(ValueError):
            build_site(self.registry([dict(self.entry,public_authorized=False)]),self.base/"blocked")
    def test_duplicate_and_traversal(self):
        for suffix,records in (("dupe",[self.entry,self.entry]),("traversal",[dict(self.entry,id="../bad")])):
            with self.assertRaises(ValueError):
                build_site(self.registry(records),self.base/suffix)
    def test_tampered_review(self):
        file=self.base/"source/26_render_eps.png"
        data=file.read_bytes()
        try:
            file.write_bytes(b"bad")
            with self.assertRaises(ValueError):
                build_site(self.registry([self.entry]),self.base/"tampered")
        finally:
            file.write_bytes(data)
    def test_revision_and_inventory(self):
        old={"modelos/tp40-r01/tp40-r01.dxf":"a","modelos/tp40-r01/tp40-r01-producao.zip":"b","index.html":"c"}
        new={"index.html":"d"}
        self.assertEqual(set(check_revision(old,new)),set(old)-set(new))
        with self.assertRaises(ValueError):
            check_revision(old,dict(old,**{"modelos/tp40-r01/tp40-r01.dxf":"changed"}))
        with self.assertRaises(ValueError):
            validate_state({"format":1,"files":{"assets/..":"0"*64}})
    def test_calibration_never_public_cut(self):
        from epscad.build import build_job
        from epscad.loader import load_yaml
        from epscad.exporters import write_outputs
        spec=load_yaml(ROOT/"projects/exemplos/001_linha_500mm.yaml")
        source=self.base/"calibration"
        write_outputs(build_job(spec),spec,source)
        out=self.base/"cal-site"
        records=[dict(self.entry,id="calibration",source="calibration",release={"approved":True,"dxf_sha256":hashlib.sha256((source/"03_cutpaths_r12.dxf").read_bytes()).hexdigest()})]
        items=build_site(self.registry(records),out)
        self.assertIsNone(items[0]["machine"])
        self.assertFalse(any(out.rglob("*.dxf")))
