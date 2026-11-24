from __future__ import annotations

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


def load_example(name: str) -> dict:
    return load_yaml(ROOT / "projects" / "exemplos" / name)


class CoreWorkflowTests(unittest.TestCase):
    def test_straight_cut_500_bbox(self) -> None:
        job = build_job(load_example("001_linha_500mm.yaml"))

        self.assertFalse(job.has_errors, [item.message for item in job.validation])
        self.assertEqual(job.bbox["width"], 500)
        self.assertEqual(job.bbox["height"], 0)
        self.assertEqual(len(job.paths), 1)

    def test_square_100_bbox(self) -> None:
        job = build_job(load_example("002_quadrado_100mm.yaml"))

        self.assertFalse(job.has_errors, [item.message for item in job.validation])
        self.assertEqual(job.bbox["width"], 100)
        self.assertEqual(job.bbox["height"], 100)
        self.assertEqual(sum(len(path.segments) for path in job.paths), 4)

    def test_grid_blocks_has_no_duplicate_segments(self) -> None:
        job = build_job(load_example("003_grade_blocos_100mm.yaml"))
        segments = [segment for path in job.paths for segment in path.segments]
        normalized = {
            tuple(sorted(((segment.start.x, segment.start.y), (segment.end.x, segment.end.y))))
            for segment in segments
        }

        self.assertFalse(job.has_errors, [item.message for item in job.validation])
        self.assertEqual(len(segments), 17)
        self.assertEqual(len(normalized), len(segments))
        self.assertEqual(job.bbox["width"], 1000)
        self.assertEqual(job.bbox["height"], 500)

    def test_photo_reference_stays_draft_and_writes_no_dxf(self) -> None:
        spec = load_example("005_foto_bloqueada.yaml")
        job = build_job(spec)

        self.assertFalse(job.has_errors, [item.message for item in job.validation])
        self.assertEqual(job.production_status, "draft")
        self.assertTrue(any(item.code == "image_reference_locked" for item in job.validation))

        with tempfile.TemporaryDirectory() as tmp:
            files = write_outputs(job, spec, tmp)
            self.assertNotIn("dxf_r12", files)

    def test_generated_dxf_has_no_forbidden_entities(self) -> None:
        spec = load_example("001_linha_500mm.yaml")
        job = build_job(spec)
        with tempfile.TemporaryDirectory() as tmp:
            files = write_outputs(job, spec, tmp)
            result = validate_dxf(files["dxf_r12"])

        self.assertTrue(result.ok)
        self.assertEqual(result.forbidden_entities, [])
        self.assertEqual(result.bbox["width"], 500)

    def test_missing_machine_profile_is_error(self) -> None:
        spec = load_example("001_linha_500mm.yaml")
        spec["machine"]["profile"] = "nao_existe"
        job = build_job(spec)

        self.assertTrue(job.has_errors)
        self.assertTrue(any(item.code == "unsupported_machine_profile" for item in job.validation))

    def test_gcode_enabled_is_blocked_by_default(self) -> None:
        spec = load_example("001_linha_500mm.yaml")
        spec["outputs"]["gcode"]["enabled"] = True
        job = build_job(spec)

        self.assertTrue(job.has_errors)
        self.assertTrue(any(item.code in {"schema_const", "schema_error", "gcode_blocked_by_default"} for item in job.validation))

    def test_hotwire_confirmar_blocks_production_status(self) -> None:
        spec = load_example("005_foto_bloqueada.yaml")
        spec["project"]["status"] = "cam_ready"
        job = build_job(spec)

        self.assertTrue(job.has_errors)
        self.assertTrue(any(item.code == "confirmar_blocks_production" for item in job.validation))
        self.assertTrue(any(item.code == "hotwire_confirmar_blocks_production" for item in job.validation))

    def test_scara_hotwire_rejects_router_fields(self) -> None:
        spec = load_example("001_linha_500mm.yaml")
        spec["tool"] = {"kind": "endmill", "diameter_mm": 6}
        spec["cut"]["depth"] = {"z_safe_mm": 15, "final_depth_z": 12, "pass_depth_mm": 5}
        spec["cut"]["feed"] = {"spindle_rpm": 18000}
        job = build_job(spec)

        self.assertTrue(job.has_errors)
        self.assertTrue(any(item.code in {"schema_error", "schema_unknown_field"} for item in job.validation))
        self.assertNotIn("router", job.metadata)


if __name__ == "__main__":
    unittest.main()
