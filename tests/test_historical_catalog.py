import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from epscad.publishing.historical_catalog import inventory, project_history

class HistoricalCatalogTests(unittest.TestCase):
    def test_dedup_and_modal_trajectory(self):
        data=b"N5 G21\r\nN10 G1 X0 Y0\r\nN15 X10\r\nN20 Y5\r\nN25 X0\r\nN30 M5M30\r\n"
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            (p/"a.TAP").write_bytes(data)
            (p/"b.tap").write_bytes(data)
            n, rows=inventory(p)
            self.assertEqual(n,2)
            self.assertEqual(len(rows),1)
            h=hashlib.sha256(data).hexdigest()
            self.assertEqual(len(rows[h]["aliases"]),2)
            parsed, visual=project_history(data,"history","Test",h)
            self.assertEqual(visual["distance_mm"],25)
            self.assertEqual(visual["segments"][-1]["end"],(0.0,5.0))
            self.assertFalse(visual["execution_authorized"])
            self.assertFalse(visual["regions"]["demonstrable"])
