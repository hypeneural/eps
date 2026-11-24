"""Synthetic pre-homologation requirement tests for future TP40 base-lisa hotwire cutpaths.

Tests mathematical continuity, monotonic +X ordering (zero collinear overlaps), thermal kerf
safety limits around the 48x2 mm microgrooves, lead-in/lead-out stock envelope checks, and
ongoing safety lock of the real SCARA machine profile. Never generates commercial DXF or G-code.
"""
import math
from pathlib import Path
import sys
import unittest

from shapely.geometry import LineString

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from epscad.geometry.roof_review import build_reference
from epscad.loader import load_machine_profile, load_yaml
from epscad.schema import Point
from epscad.templates.tp40 import offset_polyline


class TP40CutpathRequirementsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_yaml(ROOT / "catalogs/roof_profiles/tp40_980_microgroove_review.yaml")
        cls.roof, cls.spec = build_reference(cls.catalog["geometry"], length=1000.0)
        cls.pts = [tuple(p) for p in cls.spec["profile_points_mm"]]

    def test_nominal_interface_is_monotonic_continuous_without_overlaps(self):
        # Monotonic non-decreasing X (zero -X backtracking; only vertical microgroove steps have dx=0)
        xs = [p[0] for p in self.pts]
        self.assertEqual(xs[0], 0.0)
        self.assertEqual(xs[-1], 980.0)
        for a, b in zip(self.pts, self.pts[1:]):
            self.assertGreaterEqual(b[0], a[0] - 1e-9, f"Unexpected -X backtrack: {a} -> {b}")
            seg_len = math.hypot(b[0] - a[0], b[1] - a[1])
            self.assertGreater(seg_len, 0.0)
        line = LineString(self.pts)
        self.assertTrue(line.is_simple, "Nominal interface must not self-intersect or overlap collinearly")
        self.assertAlmostEqual(line.length, 1158.3646, places=3)
        # Verify minimum segment is the 2.0 mm microgroove vertical step
        min_seg = min(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(self.pts, self.pts[1:]))
        self.assertAlmostEqual(min_seg, 2.0, places=6)

    def test_kerf_offset_preserves_simple_path_within_microgroove_bounds(self):
        groove_depth = self.catalog["geometry"]["groove_depth_mm"]
        groove_width = self.catalog["geometry"]["groove_width_mm"]
        self.assertEqual(groove_depth, 2.0)
        self.assertEqual(groove_width, 48.0)
        point_objs = [Point(x, y) for x, y in self.pts]

        # Realistic hotwire kerf values strictly below 2 * groove_depth must remain simple and non-intersecting
        for kerf_mm in (1.0, 1.5, 2.0, 2.5):
            half_k = kerf_mm / 2.0
            self.assertLess(half_k, groove_depth)
            shifted = offset_polyline(point_objs, -half_k)
            ls = LineString([(p.x, p.y) for p in shifted])
            self.assertTrue(ls.is_simple, f"Kerf {kerf_mm} mm produced self-intersection in microgroove")
            # Core thickness preservation: every shifted point lies strictly on/below the nominal crest ceiling (36 mm)
            self.assertLess(max(p.y for p in shifted), 36.0)
            # Every microgroove bottom shifted down by half_k without collapsing width
            groove_bottom_ys = [p.y for p in shifted if abs(p.y - (34.0 - half_k)) < 0.05]
            self.assertEqual(len(groove_bottom_ys), 10, f"Expected 5 microgroove bottoms (10 pts) at kerf={kerf_mm}")

    def test_lead_in_and_lead_out_extend_required_machine_envelope(self):
        lead_in = 20.0
        lead_out = 20.0
        cutpath = [(-lead_in, 0.0)] + self.pts + [(980.0 + lead_out, 0.0)]
        ls = LineString(cutpath)
        self.assertTrue(ls.is_simple)
        min_x, min_y, max_x, max_y = ls.bounds
        self.assertAlmostEqual(max_x - min_x, 980.0 + lead_in + lead_out, places=6)
        self.assertAlmostEqual(min_y, 0.0, places=6)
        self.assertAlmostEqual(max_y, 36.0, places=6)

    def test_real_scara_profile_remains_locked_and_unconfirmed(self):
        profile = load_machine_profile("scara_hotwire_eps")
        self.assertIs(profile["profile_locked"], False)
        self.assertEqual(profile["hotwire"]["effective_kerf_mm"], "confirmar")
        self.assertEqual(profile["hotwire"]["min_segment_mm"], "confirmar")
        self.assertEqual(profile["work_area"]["x_max"], "confirmar")
        self.assertEqual(self.catalog["status"], "reference_only")
        self.assertIs(self.catalog["validation"]["machine_export_allowed"], False)
        self.assertIs(self.catalog["validation"]["physical_fit_confirmed"], False)


if __name__ == "__main__":
    unittest.main()
