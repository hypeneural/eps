import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
import trimesh
from epscad.build import build_job
from epscad.loader import load_yaml
from epscad.exporters import write_outputs
from epscad.exporters.roof_3d import mesh_mm
from epscad.exporters.dxf_validator import validate_dxf

class Roof3DTests(unittest.TestCase):
    def spec(self):
        return load_yaml(ROOT/"projects/exemplos/007_tp40_nucleo_eps.yaml")
    def test_geometry_and_mesh(self):
        job=build_job(self.spec())
        self.assertFalse(job.has_errors,job.validation)
        roof=job.roof_geometry
        self.assertAlmostEqual(roof.core.area,57000)
        self.assertAlmostEqual(roof.core.area+roof.complement.area,100000)
        self.assertAlmostEqual(roof.core.intersection(roof.metal).area,0)
        mesh=mesh_mm(roof.core,roof.length_mm)
        self.assertTrue(mesh.is_watertight)
        self.assertAlmostEqual(mesh.volume,roof.core.area*roof.length_mm,places=4)
    def test_package(self):
        spec=self.spec()
        with tempfile.TemporaryDirectory() as tmp:
            files=write_outputs(build_job(spec),spec,tmp)
            self.assertNotIn("dxf_r12",files)
            for k in ("eps_glb","assembly_glb","core_stl","render_eps","render_assembly"):
                self.assertGreater(Path(files[k]).stat().st_size,100)
            scene=trimesh.load(files["eps_glb"],force="scene")
            self.assertAlmostEqual(scene.extents[0],1.0,places=5)
    def test_empty_dxf_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"empty.dxf"
            path.write_text("")
            self.assertFalse(validate_dxf(path).ok)
    def test_confirmation_and_outline(self):
        spec=self.spec()
        spec["project"]["status"]="validated_geometry"
        spec["cut"]["template_params"]["profile_confirmed"]=True
        self.assertTrue(build_job(spec).has_errors)
        spec["project"]["source"].update(scale_confirmed=True,dimensions_confirmed=True)
        spec["cut"]["template_params"]["cut_mode"]="core_outline"
        self.assertTrue(build_job(spec).has_errors)
