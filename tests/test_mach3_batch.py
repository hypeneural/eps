import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"src"),str(ROOT/"scripts")]
from prepare_mach3_batch import batch,plan_rows,bind_reviewed_contract
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

    def test_bind_only_reviewed_contract_and_never_rebind(self):
        from epscad.exporters.mach3_tap import FLAGS
        import yaml
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            profile={"id":"scara_hotwire_eps","unit":"mm","process_type":"hotwire_2d",
                     "profile_locked":False,"safety":{"production_allowed":False},
                     "work_area":{"x_max":1200,"y_max":300,"z_max":1500},
                     "hotwire":{"wire_count":1,"effective_kerf_mm":1.2,"min_segment_mm":1},
                     "feed":{"default_xy_mm_min":400}}
            # Synthetic unit-test values only; never deploy or operate hardware.
            (p/"profile.yaml").write_text(yaml.safe_dump(profile))
            c={**dict.fromkeys(FLAGS,True),"controller_profile":"CNC_V",
               "machine_profile_sha256":"CALCULAR_COM_sha(canonical(profile))_APOS_PREENCHER_SNAPSHOT",
               "work_offset":"G54","path_control":"G61","dwell_unit":"seconds",
               "dwell_value":0,"max_dwell_seconds":1,"feed_mm_min":100,"heat_s":1,"max_heat_s":2}
            record={"purpose":"local_supervised_trial","operator_trial_authorized":True,"contract":c}
            (p/"contract.json").write_text(json.dumps(record))
            h=bind_reviewed_contract(p/"profile.yaml",p/"contract.json",p/"bound.json")
            bound=json.loads((p/"bound.json").read_text())
            self.assertEqual(h,sha(canonical(profile)))
            self.assertEqual(bound["contract"],dict(c,machine_profile_sha256=h))
            self.assertEqual(json.loads((p/"contract.json").read_text()),record)
            profile["work_area"]["x_max"]=1300
            (p/"profile.yaml").write_text(yaml.safe_dump(profile))
            with self.assertRaisesRegex(ValueError,"new review"):
                bind_reviewed_contract(p/"profile.yaml",p/"bound.json",p/"bad.json")
            record["operator_trial_authorized"]=False
            (p/"contract.json").write_text(json.dumps(record))
            with self.assertRaises(ValueError):
                bind_reviewed_contract(p/"profile.yaml",p/"contract.json",p/"bad.json")
            self.assertFalse((p/"bad.json").exists())
