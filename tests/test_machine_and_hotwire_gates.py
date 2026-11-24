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
from epscad.validators.machine_validator import validate_machine_profile_schema


def load_example(name: str) -> dict:
    return load_yaml(ROOT / "projects" / "exemplos" / name)


class MachineAndHotwireGateTests(unittest.TestCase):
    def test_machine_profile_schema_validates_required_structure(self) -> None:
        profile = load_yaml(ROOT / "machine_profiles" / "scara_hotwire_eps.yaml")

        messages = validate_machine_profile_schema(profile)

        self.assertEqual(messages, [])

    def test_machine_profile_schema_rejects_unknown_fields(self) -> None:
        profile = load_yaml(ROOT / "machine_profiles" / "scara_hotwire_eps.yaml")
        profile = copy.deepcopy(profile)
        profile["router"] = {"spindle_rpm": 18000}

        messages = validate_machine_profile_schema(profile)

        self.assertTrue(any(item.code in {"machine_profile_schema_error", "machine_profile_schema_unknown_field"} for item in messages))

    def test_machine_profile_schema_rejects_wrong_process_type(self) -> None:
        profile = load_yaml(ROOT / "machine_profiles" / "scara_hotwire_eps.yaml")
        profile = copy.deepcopy(profile)
        profile["process_type"] = "router_spindle"

        messages = validate_machine_profile_schema(profile)

        self.assertTrue(any(item.code in {"machine_profile_schema_error", "machine_profile_schema_const"} for item in messages))

    def test_hotwire_production_rejects_non_numeric_confirmed_values(self) -> None:
        spec = load_example("001_linha_500mm.yaml")
        spec = copy.deepcopy(spec)
        spec["project"]["status"] = "cam_ready"
        spec["project"]["source"]["production_confirmed"] = True
        spec["process"]["hotwire"]["effective_kerf_mm"] = "lento"
        spec["process"]["hotwire"]["min_segment_mm"] = "abc"
        spec["process"]["feed"]["xy_mm_min"] = "rapido"

        job = build_job(spec)

        self.assertTrue(job.has_errors)
        self.assertTrue(any(item.code == "hotwire_numeric_required_for_production" for item in job.validation))

    def test_hotwire_production_rejects_invalid_wire_count(self) -> None:
        spec = load_example("001_linha_500mm.yaml")
        spec = copy.deepcopy(spec)
        spec["project"]["status"] = "cam_ready"
        spec["project"]["source"]["production_confirmed"] = True
        spec["process"]["hotwire"]["wire_count"] = 0

        job = build_job(spec)

        self.assertTrue(job.has_errors)
        self.assertTrue(any(item.code == "hotwire_wire_count_invalid" for item in job.validation))


if __name__ == "__main__":
    unittest.main()
