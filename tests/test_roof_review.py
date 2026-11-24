import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
import ezdxf
import trimesh
from epscad.loader import load_yaml
from epscad.geometry.roof_review import build_reference
from epscad.geometry.evidence_zip import inspect_zip

class RoofReviewTests(unittest.TestCase):
    def geometry(self):
        return load_yaml(ROOT/"catalogs/roof_profiles/tp40_980_microgroove_review.yaml")["geometry"]
    def test_reference(self):
        roof,r=build_reference(self.geometry())
        self.assertEqual((r["width_mm"],r["height_mm"],r["min_thickness_mm"]),(980,67,31))
        self.assertAlmostEqual(r["area_mm2"],42560)
        self.assertEqual(len(r["profile_points_mm"]),41)
        self.assertIn((58,34),r["profile_points_mm"])
        self.assertEqual(roof.core.intersection(roof.metal).area,0)
        self.assertFalse(r["machine_export_allowed"])
        changed,_=build_reference(dict(self.geometry(),min_thickness_mm=40))
        self.assertAlmostEqual(changed.core.area-roof.core.area,980*9)
    def test_evidence_dedup(self):
        roof,r=build_reference(self.geometry())
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            doc=ezdxf.new("R2013")
            doc.units=4
            points=r["profile_points_mm"]
            for a,b in zip(points,points[1:]):
                doc.modelspace().add_line(a,b)
            doc.modelspace().add_line((0,0),(-1,0))
            doc.modelspace().add_line((-1,0),(-1,67))
            dxf=root/"x.dxf"
            doc.saveas(dxf)
            archive=root/"evidence.zip"
            with zipfile.ZipFile(archive,"w") as z:
                for folder in ("a","b"):
                    z.write(dxf,folder+"/telha tp 40 base lisa.dxf")
            report=inspect_zip(archive,width=980,length=1000,gauge=.43,expected_roof=roof)
            self.assertEqual(report["unique_counts"][".dxf"],1)
            self.assertAlmostEqual(report["comparison_area_mm2"],0)
    def test_cli_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/"review"
            subprocess.run([sys.executable,str(ROOT/"scripts/prepare_tp40.py"),"--output",str(out)],check=True,capture_output=True)
            r=json.loads((out/"review.json").read_text())
            self.assertFalse(r["production_confirmed"])
            with zipfile.ZipFile(out/"TP40_REVISAO.zip") as z:
                self.assertIn("29_section_review.png",z.namelist())
                self.assertFalse(any(x.endswith((".dxf",".tap")) for x in z.namelist()))
            mesh=trimesh.load(out/"20_eps_core_mm.stl")
            self.assertTrue(mesh.is_watertight)
            self.assertAlmostEqual(mesh.volume,42560000,delta=10)
            scene=trimesh.load(out/"24_eps_core.glb",force="scene")
            self.assertAlmostEqual(scene.extents[0],.98,places=5)
