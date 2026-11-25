import sys
import unittest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from check_mach3_delivery import inspect,expected_ids

class DeliveryTests(unittest.TestCase):
    def test_nine_real_model_ids_and_zero_downloads_fails_acceptance(self):
        ids=expected_ids()
        self.assertEqual(len(ids),9)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            (p/"index.html").write_text("<html></html>")
            (p/"catalog.json").write_text(json.dumps([{"id":x,"status":"draft","machine":None} for x in ids]))
            with patch("check_mach3_delivery.local_inventory",return_value={}):
                r=inspect(p)
            self.assertEqual(r["expected"],9)
            self.assertEqual(r["delivered"],0)
            self.assertTrue(all(x["reason"]=="approved_TAP_missing" for x in r["models"]))
