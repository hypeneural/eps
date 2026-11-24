from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from epscad.build import build_job
from epscad.loader import load_yaml
from epscad.templates import build_paths
from epscad.validators.geometry_validator import validate_geometry


def load_example(name: str) -> dict:
    return load_yaml(ROOT / "projects" / "exemplos" / name)


class GeometryValidatorTests(unittest.TestCase):
    def test_duplicate_reversed_segment_is_error(self) -> None:
        spec = load_example("001_linha_500mm.yaml")
        spec = copy.deepcopy(spec)
        spec["cut"]["template"] = "profile_2d"
        spec["cut"]["template_params"] = {"points": [[0, 0], [100, 0]], "closed": True}

        job = build_job(spec)

        self.assertTrue(job.has_errors)
        self.assertTrue(any(item.code == "geometry_duplicate_segment" for item in job.validation))

    def test_segment_shorter_than_min_segment_is_error(self) -> None:
        spec = load_example("001_linha_500mm.yaml")
        spec = copy.deepcopy(spec)
        spec["cut"]["template"] = "profile_2d"
        spec["cut"]["template_params"] = {"points": [[0, 0], [2, 0], [20, 0]], "closed": False}
        spec["process"]["hotwire"]["min_segment_mm"] = 5

        job = build_job(spec)

        self.assertTrue(job.has_errors)
        self.assertTrue(any(item.code == "geometry_segment_too_short" for item in job.validation))

    def test_bbox_outside_stock_is_error(self) -> None:
        spec = load_example("001_linha_500mm.yaml")
        spec = copy.deepcopy(spec)
        spec["cut"]["template_params"]["length_mm"] = 1200
        spec["material"]["stock"]["length_x"] = 1000

        job = build_job(spec)

        self.assertTrue(job.has_errors)
        self.assertTrue(any(item.code == "geometry_outside_stock" for item in job.validation))

    def test_bbox_outside_machine_area_is_error(self) -> None:
        spec = load_example("001_linha_500mm.yaml")
        paths, messages = build_paths(spec)

        self.assertEqual(messages, [])
        result = validate_geometry(spec, paths, machine_profile={"work_area": {"x_max": 400, "y_max": 100}})

        self.assertTrue(any(item.code == "geometry_outside_machine_area" for item in result))


if __name__ == "__main__":
    unittest.main()
