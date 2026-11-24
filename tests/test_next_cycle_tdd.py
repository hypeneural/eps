from __future__ import annotations

import sys
import tempfile
import unittest
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from epscad.build import build_job
from epscad.exporters import write_outputs
from epscad.loader import load_yaml


def load_example(name: str) -> dict:
    return load_yaml(ROOT / "projects" / "exemplos" / name)


class NextCycleTddTests(unittest.TestCase):
    def test_validator_modules_are_separated_and_importable(self) -> None:
        from epscad.validators.hotwire_validator import validate_hotwire
        from epscad.validators.production_gate import validate_production_gates
        from epscad.validators.schema_validator import validate_schema

        self.assertTrue(callable(validate_schema))
        self.assertTrue(callable(validate_production_gates))
        self.assertTrue(callable(validate_hotwire))

    def test_hotwire_requires_wire_mode(self) -> None:
        spec = load_example("001_linha_500mm.yaml")
        del spec["process"]["hotwire"]["wire_mode"]

        job = build_job(spec)

        self.assertTrue(job.has_errors)
        self.assertTrue(any(item.code in {"schema_error", "schema_required", "hotwire_required_field_missing"} for item in job.validation))

    def test_hotwire_manifest_contains_wire_data_not_router_data(self) -> None:
        spec = load_example("001_linha_500mm.yaml")
        job = build_job(spec)

        self.assertFalse(job.has_errors, [item.message for item in job.validation])
        self.assertEqual(job.metadata["hotwire"]["wire_mode"], "line_hotwire")

        with tempfile.TemporaryDirectory() as tmp:
            files = write_outputs(job, spec, tmp)
            manifest = json.loads(Path(files["manifest"]).read_text(encoding="utf-8"))
            pdf_text = Path(files["pdf_job"]).read_bytes().decode("latin-1")

        self.assertEqual(manifest["machine_profile"], "scara_hotwire_eps")
        self.assertEqual(manifest["process_type"], "hotwire_2d")
        self.assertEqual(manifest["wire_mode"], "line_hotwire")
        self.assertEqual(manifest["wire_count"], 1)
        self.assertEqual(manifest["effective_kerf_mm"], 1.5)
        self.assertNotIn("tool_diameter_mm", manifest)
        self.assertNotIn("spindle_rpm", manifest)
        self.assertIn("Modo do fio: line_hotwire", pdf_text)


if __name__ == "__main__":
    unittest.main()
