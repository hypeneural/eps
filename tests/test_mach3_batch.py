import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"src"),str(ROOT/"scripts")]
from prepare_mach3_batch import batch,plan_rows
from epscad.exporters.mach3_tap import sha,canonical

class BatchTests(unittest.TestCase):
    def test_requires_model_approval_and_keeps_going(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            profile=p/"profile.yaml"; profile.write_text("id: scara_hotwire_eps\n")
            contract=p/"contract.json"; contract.write_text(json.dumps({"contract":{"machine_profile_sha256":sha(canonical({"id":"scara_hotwire_eps"}))}}))
            approvals=p/"approvals.json"; approvals.write_text(json.dumps({"one":{"trial_authorized":True,"path_sha256":"a","project_sha256":"b"}}))
            rows=[{"id":"one","project":p/"one.yaml","path_sha256":"a","project_sha256":"b"},
                  {"id":"two","project":p/"two.yaml","path_sha256":"c","project_sha256":"d"}]
            with patch("prepare_mach3_batch.plan_rows",return_value=rows),patch("prepare_mach3_batch.prepare_trial",return_value={"machine_file":"TESTE.tap","tap_sha256":"x"}) as prepare:
                r=batch(p,profile,contract,approvals,p/"out")
            self.assertEqual(prepare.call_count,1)
            self.assertEqual([x["status"] for x in r["models"]],["trial_generated","blocked"])
            self.assertFalse(r["production_approved"])

    def test_nine_model_inventory_with_missing_projects(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            self.assertEqual(len(plan_rows(p)),5)
            rows=plan_rows(p,p/"private")
            self.assertEqual(len(rows),9)
            self.assertEqual(len({r["id"] for r in rows}),9)
            self.assertEqual(sum(r["id"].startswith("capa-laje-") for r in rows),4)
            self.assertTrue(all("error" in r for r in rows))
