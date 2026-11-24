import unittest
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
           "dwell_unit":"seconds","path_control":"G61","work_offset":"G54","machine_profile_sha256":sha(canonical(profile))}
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
