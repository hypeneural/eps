import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from recover_cnc_v_evidence import inspect_backup

class EvidenceTests(unittest.TestCase):
    def test_documentary_only(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"backup.zip"
            with zipfile.ZipFile(p,"w") as z:
                z.writestr("CONFIG/CNC_V.xml","<profile><Preferences><Profile>CNC_V</Profile><DwellinMilli>0</DwellinMilli><SoftLimit>0</SoftLimit></Preferences></profile>")
                z.writestr("CONFIG/isopor.pst","F600\nS300\nG4 P3\n")
                z.writestr("MACROS/m3.m1s","DoSpinCW()")
                z.writestr("MACROS/m5.m1s","DoSpinStop()")
                z.writestr("test.tap","N5 F600\nN10 S300\nN15 G4 P3\n")
                z.writestr("duplicate/test.tap","N5 F600\nN10 S300\nN15 G4 P3\n")
            r=inspect_backup(p)
            self.assertEqual(r["unique_taps"],1)
            self.assertEqual(r["pst_observed"]["dwell_unit"],"seconds")
            self.assertEqual(r["pst_observed"]["feed_mm_min"],["600"])
            self.assertFalse(r["production_approved"])
            self.assertNotIn("work_area",r)
            with zipfile.ZipFile(p,"a") as z:
                z.writestr("other/CNC_V.xml","<profile/>")
            with self.assertRaisesRegex(ValueError,"Conflicting copies"):
                inspect_backup(p)
