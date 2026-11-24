from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from epscad.exporters.dxf_r12 import write_dxf_r12
from epscad.exporters.dxf_validator import validate_dxf
from epscad.schema import CutJobResult, CutPath, PathSegment, Point

try:
    import ezdxf
except Exception:  # pragma: no cover
    ezdxf = None


def make_job(*segments: PathSegment) -> CutJobResult:
    job = CutJobResult("t", "t", "mm", "scara_hotwire_eps", "hotwire_2d", "validated_geometry", "manual_text")
    job.paths = [CutPath(id="p", layer="CUT_OUTSIDE", segments=list(segments))]
    return job


LINE = PathSegment("LINE", Point(0, 0), Point(100, 0), "CUT_OUTSIDE")
ARC = PathSegment("ARC", Point(10, 0), Point(0, 10), "CUT_OUTSIDE", center=Point(0, 0))
CIRCLE = PathSegment("CIRCLE", Point(5, 0), Point(5, 0), "CUT_CIRCLE", center=Point(0, 0))


class DxfExportTests(unittest.TestCase):
    def modes(self):
        yield "fallback", False
        if ezdxf is not None:
            yield "ezdxf", True

    def test_line_arc_circle_exported_and_valid_in_both_writers(self) -> None:
        for name, use_ezdxf in self.modes():
            with self.subTest(writer=name), tempfile.TemporaryDirectory() as tmp:
                target = Path(tmp) / "out.dxf"
                write_dxf_r12(make_job(LINE, ARC, CIRCLE), target, use_ezdxf=use_ezdxf)
                result = validate_dxf(target)
                self.assertTrue(result.ok, result)
                self.assertEqual(result.entity_count, 3)
                self.assertEqual(result.forbidden_entities, [])
                self.assertEqual(result.bbox["min_x"], -5)  # circulo r=5 em (0,0)
                self.assertEqual(result.bbox["max_x"], 100)
                if ezdxf is not None:
                    kinds = sorted(entity.dxftype() for entity in ezdxf.readfile(target).modelspace())
                    self.assertEqual(kinds, ["ARC", "CIRCLE", "LINE"])

    def test_fallback_has_full_r12_structure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "out.dxf"
            write_dxf_r12(make_job(LINE), target, use_ezdxf=False)
            lines = target.read_text(encoding="ascii").splitlines()
        for token in ("HEADER", "AC1009", "TABLES", "LAYER", "CUT_OUTSIDE", "ENTITIES", "EOF"):
            self.assertIn(token, lines)
        if ezdxf is not None:
            with tempfile.TemporaryDirectory() as tmp:
                target = Path(tmp) / "out.dxf"
                write_dxf_r12(make_job(LINE, ARC), target, use_ezdxf=False)
                doc = ezdxf.readfile(target)
                self.assertEqual(doc.dxfversion, "AC1009")
                self.assertEqual(len(doc.modelspace()), 2)

    def test_arc_bbox_includes_cardinal_extremes(self) -> None:
        # arco de 270 a 90 graus (ccw) passa por 0 graus: x max = raio
        arc = PathSegment("ARC", Point(0, -10), Point(0, 10), "CUT_OUTSIDE", center=Point(0, 0))
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "out.dxf"
            write_dxf_r12(make_job(arc), target, use_ezdxf=False)
            bbox = validate_dxf(target).bbox
        self.assertAlmostEqual(bbox["max_x"], 10)
        self.assertAlmostEqual(bbox["min_x"], 0, places=6)

    def test_unsupported_segment_kind_raises_instead_of_dropping(self) -> None:
        bad = PathSegment("SPLINE", Point(0, 0), Point(1, 1))
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                write_dxf_r12(make_job(LINE, bad), Path(tmp) / "x.dxf")

    def test_validator_rejects_forbidden_entities_and_user_blocks(self) -> None:
        text = "\n".join(
            ["0", "SECTION", "2", "BLOCKS", "0", "BLOCK", "2", "MEUBLOCO", "0", "ENDBLK", "0", "ENDSEC",
             "0", "SECTION", "2", "ENTITIES", "0", "TEXT", "8", "X", "0", "ENDSEC", "0", "EOF", ""]
        )
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "bad.dxf"
            target.write_text(text, encoding="ascii")
            result = validate_dxf(target)
        self.assertFalse(result.ok)
        self.assertEqual(result.forbidden_entities, ["BLOCK", "TEXT"])

    def test_validator_accepts_standard_ezdxf_r12_blocks(self) -> None:
        if ezdxf is None:
            self.skipTest("ezdxf not installed")
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "r12.dxf"
            write_dxf_r12(make_job(LINE), target, use_ezdxf=True)
            self.assertTrue(validate_dxf(target).ok)


if __name__ == "__main__":
    unittest.main()
