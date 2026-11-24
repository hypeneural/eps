import unittest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from epscad.exporters.tap_audit import audit
from epscad.exporters.mach3_tap import approval_hashes,canonical,sha
from epscad.schema import CutJobResult,CutPath,PathSegment,Point

class Mach3Tests(unittest.TestCase):
    def fixture(self):
        job=CutJobResult("fixture","Synthetic","mm","scara_hotwire_eps","hotwire_2d","production_released","manual",
            paths=[CutPath("p","CUT",[PathSegment("LINE",Point(0,0),Point(10,0))])])
        profile={"profile_locked":True,"safety":{"production_allowed":True},"work_area":{"x_max":20,"y_max":20},"hotwire":{"min_segment_mm":1},"feed":{"default_xy_mm_min":10}}
        from epscad.exporters.mach3_tap import FLAGS
        c={**dict.fromkeys(FLAGS,True),"controller_profile":"CNC_V","feed_mm_min":5,"heat_s":1,"dwell_value":0,
           "max_heat_s":2,"max_dwell_seconds":1,"dwell_unit":"seconds","path_control":"G61","work_offset":"G54","machine_profile_sha256":sha(canonical(profile))}
        return job,profile,c
    def test_historical_lexical(self):
        r=audit(b"N5 G21\r\nN10 G80\r\nN15 S300\r\nN20 F600\r\nN25 M3\r\nN30 G4 P3\r\nN35 G1 X0 Y0\r\nN40 X5\r\nN45 M5M30\r\n")
        self.assertFalse(r["absolute_mode_explicit"])
        self.assertFalse(r["production_approved"])
        self.assertEqual(r["codes"]["M30"],1)
    def test_candidate_and_gate(self):
        j,p,c=self.fixture()
        b,h=approval_hashes(j,p,c)
        self.assertEqual(h["tap_sha256"],sha(b))
        self.assertIn(b"G90",b)
        self.assertTrue(b.endswith(b"M30\r\n"))
        for key in ("io_mapping_confirmed","thermal_parameters_confirmed"):
            with self.assertRaises(ValueError): approval_hashes(j,p,dict(c,**{key:False}))
        j.production_status="draft"
        with self.assertRaises(ValueError): approval_hashes(j,p,c)
    def test_reject_discontinuous_and_bounds(self):
        j,p,c=self.fixture()
        j.paths[0].segments.append(PathSegment("LINE",Point(11,0),Point(12,0)))
        with self.assertRaises(ValueError): approval_hashes(j,p,c)
        j.paths[0].segments=[PathSegment("LINE",Point(0,0),Point(30,0))]
        with self.assertRaises(ValueError): approval_hashes(j,p,c)
    def test_revocation_type(self):
        from epscad.publishing.deploy import machine_file,check_revision
        name="modelos/example-r01/example-r01.tap"
        self.assertTrue(machine_file(name))
        with self.assertRaises(ValueError): check_revision({name:"a"},{name:"b"})

    def test_thermal_limits_and_order(self):
        j,p,c=self.fixture()
        with self.assertRaises(ValueError): approval_hashes(j,p,dict(c,heat_s=3))
        with self.assertRaises(ValueError): approval_hashes(j,p,dict(c,dwell_value=2))
        with self.assertRaises(ValueError): approval_hashes(j,p,dict(c,dwell_unit="milliseconds",dwell_value=2000))
        j.paths[0].segments.append(PathSegment("LINE",Point(10,0),Point(0,0)))
        b,h=approval_hashes(j,p,c)
        self.assertIn(b"X0.0000 Y0.0000",b)
    def test_tap_approval_binds_all_fields(self):
        from unittest.mock import patch
        from epscad.publishing.tap_release import approved_tap
        j,p,c=self.fixture()
        data,hashes=approval_hashes(j,p,c)
        expected={"dxf_sha256":"d","project_sha256":"p","profile_sha256":"m",**hashes}
        release={"approved":True,"tap_approved":True,"tap_contract":c,**expected}
        with patch("epscad.publishing.tap_release.tap_candidate",return_value=(data,expected)):
            self.assertEqual(approved_tap(None,None,None,release),data)
            for key in expected:
                with self.assertRaises(ValueError):
                    approved_tap(None,None,None,dict(release,**{key:"wrong"}))
            with self.assertRaises(ValueError): approved_tap(None,None,None,dict(release,tap_approved=False))
