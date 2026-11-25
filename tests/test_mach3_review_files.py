import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"src"),str(ROOT/"scripts")]
from build_mach3_review_files import encode_review,plans,COMMENT,historical_settings
from epscad.exporters.tap_simulator import parse_tap_modal

class ReviewFilesTests(unittest.TestCase):
    def test_nine_actual_nominal_plans(self):
        # Synthetic documentary values only for unit testing.
        settings={"feed_mm_min":100,"spindle_s":1,"dwell_value":1,"dwell_unit":"seconds"}
        rows=list(plans())
        self.assertEqual(len(rows),9)
        for slug,name,plan in rows:
            data,parsed=encode_review(plan["points_mm"],settings)
            self.assertTrue(data.startswith(COMMENT))
            self.assertEqual(parse_tap_modal(data[len(COMMENT):])["metrics"],parsed["metrics"])
            self.assertEqual(parsed["metrics"]["collinear_overlap_mm"],0)
            self.assertFalse(parsed["production_approved"])
    def test_reject_ambiguous_settings(self):
        with self.assertRaises(ValueError):
            historical_settings({"pst_observed":{"feed_mm_min":["100","200"]}})
