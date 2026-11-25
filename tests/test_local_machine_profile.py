import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from epscad.loader import load_machine_profile

class LocalProfileTests(unittest.TestCase):
    def test_explicit_override_never_changes_versioned_profile(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"private.yaml"
            p.write_text("id: scara_hotwire_eps\nprofile_locked: false\n")
            with patch.dict(os.environ,{"EPS_SCARA_PROFILE_FILE":str(p)}):
                self.assertEqual(load_machine_profile("scara_hotwire_eps")["profile_locked"],False)
                self.assertEqual(load_machine_profile("scara_hotwire_teste")["id"],"scara_hotwire_teste")
                p.write_text("id: scara_hotwire_teste\n")
                with self.assertRaisesRegex(ValueError,"ID mismatch"):
                    load_machine_profile("scara_hotwire_eps")
