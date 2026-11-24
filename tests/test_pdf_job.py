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
from epscad.loader import load_yaml


def load_example(name: str) -> dict:
    return load_yaml(ROOT / "projects" / "exemplos" / name)


def pdf_text(path: Path) -> str:
    return path.read_bytes().decode("latin-1")


class PdfJobTests(unittest.TestCase):
    def test_pdf_job_is_technical_hotwire_order_with_strong_test_warning(self) -> None:
        spec = load_example("001_linha_500mm.yaml")
        job = build_job(spec)

        with tempfile.TemporaryDirectory() as tmp:
            files = write_outputs(job, spec, tmp)
            text = pdf_text(Path(files["pdf_job"]))

        self.assertIn("ORDEM DE CORTE EPS - SCARA HOTWIRE", text)
        self.assertIn("ARQUIVO DE TESTE - NAO CORTAR PRODUCAO", text)
        self.assertIn("Projeto: 001_linha_500mm", text)
        self.assertIn("Status: validated_geometry", text)
        self.assertIn("Maquina/perfil: scara_hotwire_eps", text)
        self.assertIn("Material: EPS", text)
        self.assertIn("Bloco EPS: X=1000 mm, Y=500 mm, Z=100 mm", text)
        self.assertIn("Origem: lower_left", text)
        self.assertIn("Eixo X no preview: direita", text)
        self.assertIn("Eixo Y no preview: cima", text)
        self.assertIn("Modo do fio: line_hotwire", text)
        self.assertIn("Fios: 1", text)
        self.assertIn("Kerf/perda efetiva: 1.5 mm", text)
        self.assertIn("Feed reto XY: 500 mm/min", text)
        self.assertIn("Preview cotado", text)
        self.assertIn("BBox: X 0.0..500.0 mm / Y 0.0..0.0 mm", text)
        self.assertIn("Checklist LazyCam", text)
        self.assertIn("Checklist Mach3/EPS", text)
        self.assertIn("Dry-run obrigatorio", text)
        self.assertNotIn("spindle", text.lower())
        self.assertNotIn("fresa", text.lower())
        self.assertNotIn("RPM", text)

    def test_pdf_job_keeps_photo_reference_locked(self) -> None:
        spec = load_example("005_foto_bloqueada.yaml")
        job = build_job(spec)

        with tempfile.TemporaryDirectory() as tmp:
            files = write_outputs(job, spec, tmp)
            text = pdf_text(Path(files["pdf_job"]))

        self.assertIn("ARQUIVO PRELIMINAR - FOTO SEM ESCALA CONFIRMADA", text)
        self.assertIn("Sem DXF de producao enquanto escala e medidas nao forem confirmadas.", text)
        self.assertIn("Checklist de medidas pendentes", text)
        self.assertNotIn("03_cutpaths_r12.dxf", text)

    def test_pdf_job_contains_vector_preview_commands(self) -> None:
        spec = load_example("001_linha_500mm.yaml")
        job = build_job(spec)

        with tempfile.TemporaryDirectory() as tmp:
            files = write_outputs(job, spec, tmp)
            text = pdf_text(Path(files["pdf_job"]))

        self.assertIn("% preview_vector_begin", text)
        self.assertIn("% preview_vector_end", text)
        self.assertIn(" m ", text)
        self.assertIn(" l S", text)


if __name__ == "__main__":
    unittest.main()
