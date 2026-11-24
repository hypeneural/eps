from __future__ import annotations

import copy
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from epscad.build import build_job
from epscad.exporters import write_outputs
from epscad.exporters.dxf_validator import validate_dxf
from epscad.loader import load_yaml
from epscad.templates.tp40 import offset_polyline, profile_points
from epscad.schema import Point

try:
    import ezdxf
except Exception:  # pragma: no cover
    ezdxf = None


def example() -> dict:
    return load_yaml(ROOT / "projects" / "exemplos" / "007_tp40_nucleo_eps.yaml")


def confirmed_spec() -> dict:
    spec = example()
    spec["project"]["status"] = "validated_geometry"
    spec["project"]["source"]["scale_confirmed"] = True
    spec["project"]["source"]["dimensions_confirmed"] = True
    spec["cut"]["template_params"]["profile_confirmed"] = True
    return spec


def codes(job) -> set[str]:
    return {item.code for item in job.validation}


class Tp40TemplateTests(unittest.TestCase):
    def test_example_is_draft_with_nominal_warning_and_no_dxf(self) -> None:
        spec = example()
        job = build_job(spec)

        self.assertFalse(job.has_errors, [item.message for item in job.validation])
        self.assertEqual(job.production_status, "draft")
        self.assertIn("tp40_profile_not_confirmed", codes(job))
        with tempfile.TemporaryDirectory() as tmp:
            files = write_outputs(job, spec, tmp)
            self.assertNotIn("dxf_r12", files)
            self.assertTrue(Path(files["png_preview"]).exists())
            self.assertTrue(Path(files["pdf_job"]).exists())

    def test_wavy_line_geometry(self) -> None:
        job = build_job(example())
        segments = job.paths[0].segments

        self.assertEqual(len(segments), 4 * 5 + 1)
        self.assertEqual(job.bbox["width"], 1000)
        self.assertEqual(job.bbox["height"], 40)
        # topo do bloco y=100, espessura minima 30 -> crista y=70, vale y=30
        self.assertEqual(job.bbox["min_y"], 30)
        self.assertEqual(job.bbox["max_y"], 70)
        first_ramp = segments[1]
        self.assertEqual((first_ramp.start.x, first_ramp.start.y), (52.5, 30))
        self.assertEqual((first_ramp.end.x, first_ramp.end.y), (82.5, 70))
        angle = math.degrees(math.atan2(40, 30))
        self.assertAlmostEqual(angle, job.metadata["tp40"]["ramp_angle_deg"], places=1)
        self.assertTrue(all(segment.kind == "LINE" for segment in segments))
        # simetria: primeiro e ultimo segmentos sao meio vale
        self.assertAlmostEqual(
            segments[0].end.x - segments[0].start.x, segments[-1].end.x - segments[-1].start.x
        )

    def test_confirmed_profile_generates_valid_dxf(self) -> None:
        spec = confirmed_spec()
        job = build_job(spec)
        self.assertFalse(job.has_errors, [item.message for item in job.validation])

        with tempfile.TemporaryDirectory() as tmp:
            files = write_outputs(job, spec, tmp)
            result = validate_dxf(files["dxf_r12"])
            manifest = json.loads(Path(files["manifest"]).read_text(encoding="utf-8"))
            pdf_text = Path(files["pdf_job"]).read_bytes().decode("latin-1")
            if ezdxf is not None:
                doc = ezdxf.readfile(files["dxf_r12"])
                self.assertEqual(doc.dxfversion, "AC1009")
                self.assertEqual(len(doc.modelspace()), 21)

        self.assertTrue(result.ok, result)
        self.assertEqual(result.entity_count, 21)
        self.assertEqual(result.bbox["width"], 1000)
        self.assertEqual(result.bbox["height"], 40)
        self.assertEqual(manifest["template"], "tp40_core")
        self.assertEqual(manifest["tp40"]["pitch_mm"], 200)
        self.assertTrue(manifest["tp40"]["profile_confirmed"])
        self.assertIn("Perfil TP40", pdf_text)

    def test_unconfirmed_profile_blocks_dxf_status(self) -> None:
        spec = confirmed_spec()
        spec["cut"]["template_params"]["profile_confirmed"] = False
        job = build_job(spec)

        self.assertTrue(job.has_errors)
        self.assertIn("tp40_profile_not_confirmed", codes(job))
        with tempfile.TemporaryDirectory() as tmp:
            self.assertNotIn("dxf_r12", write_outputs(job, spec, tmp))

    def test_invalid_params_are_rejected(self) -> None:
        cases = {
            "tp40_profile_invalid": {"crest_width_mm": 100, "valley_width_mm": 100},
            "tp40_width_mismatch": {"panel_width_mm": 980},
            "tp40_param_invalid": {"n_waves": 0},
            "tp40_param_invalid ": {"profile_height_mm": "confirmar"},
        }
        for code, change in cases.items():
            with self.subTest(change=change):
                spec = example()
                spec["cut"]["template_params"].update(change)
                job = build_job(spec)
                self.assertTrue(job.has_errors)
                self.assertIn(code.strip(), codes(job))
                self.assertEqual(job.paths, [])

    def test_profile_taller_than_stock_is_rejected(self) -> None:
        spec = example()
        spec["material"]["stock"]["height_y"] = 60
        job = build_job(spec)

        self.assertTrue(job.has_errors)
        self.assertIn("tp40_exceeds_stock_height", codes(job))

    def test_panel_wider_than_stock_is_rejected_by_geometry(self) -> None:
        spec = example()
        spec["material"]["stock"]["length_x"] = 900
        job = build_job(spec)

        self.assertIn("geometry_outside_stock", codes(job))

    def test_kerf_offset_moves_line_down_for_core_and_keeps_slopes(self) -> None:
        spec = example()
        spec["cut"]["compensation"] = "thermal_kerf_offset_applied"
        spec["process"]["hotwire"]["effective_kerf_mm"] = 2.0
        job = build_job(spec)
        nominal = build_job(example()).paths[0].segments

        self.assertFalse(job.has_errors, [item.message for item in job.validation])
        segments = job.paths[0].segments
        self.assertEqual(len(segments), len(nominal))
        self.assertEqual(job.bbox["width"], 1000)
        # horizontais descem 1.0 mm (kerf/2); extremos continuam em x=0 e x=1000
        self.assertAlmostEqual(segments[0].start.y, 29.0)
        self.assertAlmostEqual(segments[0].start.x, 0.0)
        self.assertAlmostEqual(segments[-1].end.x, 1000.0)
        # rampas mantem a inclinacao
        for new, old in zip(segments, nominal):
            old_dx, old_dy = old.end.x - old.start.x, old.end.y - old.start.y
            new_dx, new_dy = new.end.x - new.start.x, new.end.y - new.start.y
            self.assertAlmostEqual(old_dx * new_dy, old_dy * new_dx, places=4)
        self.assertTrue(job.reference_segments)

    def test_kerf_compensation_requires_numeric_kerf(self) -> None:
        spec = example()
        spec["cut"]["compensation"] = "thermal_kerf_offset_applied"
        spec["process"]["hotwire"]["effective_kerf_mm"] = "confirmar"
        job = build_job(spec)

        self.assertIn("tp40_kerf_required", codes(job))
        self.assertTrue(job.has_errors)

    def test_kerf_below_stock_bottom_is_flagged(self) -> None:
        spec = example()
        spec["material"]["stock"]["height_y"] = 70  # vale em y=0
        spec["cut"]["compensation"] = "thermal_kerf_offset_applied"
        job = build_job(spec)

        self.assertIn("geometry_outside_stock", codes(job))

    def test_core_outline_is_closed_and_has_no_duplicates(self) -> None:
        spec = example()
        spec["cut"]["template_params"]["cut_mode"] = "core_outline"
        job = build_job(spec)

        self.assertFalse(job.has_errors, [item.message for item in job.validation])
        segments = job.paths[0].segments
        self.assertEqual(len(segments), 21 + 3)
        self.assertEqual((segments[-1].end.x, segments[-1].end.y), (segments[0].start.x, segments[0].start.y))
        self.assertEqual(job.bbox["height"], 70)
        self.assertEqual(job.bbox["max_y"], 100)

    def test_reference_lines_never_enter_dxf(self) -> None:
        spec = confirmed_spec()
        job = build_job(spec)
        self.assertTrue(job.reference_segments)
        with tempfile.TemporaryDirectory() as tmp:
            files = write_outputs(job, spec, tmp)
            text = Path(files["dxf_r12"]).read_text(encoding="latin-1")
        self.assertNotIn("REF_STOCK", text)

    def test_profile_points_and_offset_helpers(self) -> None:
        pts = [Point(0, 0), Point(10, 0), Point(10, 10)]
        moved = offset_polyline(pts, 1.0)  # esquerda do sentido
        self.assertEqual((moved[0].x, moved[0].y), (0, 1))
        self.assertEqual((moved[1].x, moved[1].y), (9, 1))
        self.assertEqual((moved[2].x, moved[2].y), (9, 10))
        self.assertEqual(len(profile_points(build_params(), 100)), 22)


def build_params():
    from epscad.templates.tp40 import parse_params

    params, messages = parse_params(example())
    assert params is not None, messages
    return params


if __name__ == "__main__":
    unittest.main()
