import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
import ezdxf
from epscad.geometry.historical_roof import recover_upper_profile
from epscad.exporters.roof_3d import mesh_mm

class HistoricalRoofTests(unittest.TestCase):
    def test_envelope_discards_overlapping_baseline_and_preserves_micro_step(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"synthetic.dxf"
            doc=ezdxf.new("R2013")
            doc.units=4
            m=doc.modelspace()
            points=[(0,0),(10,10),(15,10),(15,8),(25,8),(25,10),(30,10),(40,0),(50,0)]
            for a,b in zip(points,points[1:]):
                m.add_line(a,b)
            m.add_line((0,0),(40,0))
            m.add_line((0,0),(50,0))
            doc.saveas(path)
            roof,r=recover_upper_profile(path,left=0,right=50,top=25,length=100)
            self.assertEqual(r["status"],"draft")
            self.assertIn((15,8),r["profile_points_mm"])
            self.assertEqual(r["min_thickness_mm"],15)
            self.assertGreater(r["raw_line_length"],r["unique_line_length"])
            self.assertAlmostEqual(roof.core.area,970)
            self.assertTrue(mesh_mm(roof.core,100).is_watertight)
    def test_gap_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"gap.dxf"
            doc=ezdxf.new("R12")
            doc.modelspace().add_line((0,0),(10,0))
            doc.saveas(path)
            with self.assertRaises(ValueError):
                recover_upper_profile(path,left=0,right=20,top=20,length=100)
