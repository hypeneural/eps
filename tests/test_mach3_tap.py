import unittest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from epscad.exporters.tap_audit import audit
from epscad.exporters.mach3_tap import approval_hashes,canonical,sha
from epscad.schema import CutJobResult,CutPath,PathSegment,Point

class Mach3Tests(unittest.TestCase):
    def fixture(self):
        job=CutJobResult("fixture","Synthetic","mm","scara_hotwire_eps","hotwire_2d","production_released","manual",
            paths=[CutPath("p","CUT",[PathSegment("LINE",Point(0,0),Point(10,0))])])
        profile={"profile_locked":True,"safety":{"production_allowed":True},"work_area":{"x_max":20,"y_max":20},"hotwire":{"min_segment_mm":1},"feed":{"default_xy_mm_min":10}}
        from epscad.exporters.mach3_tap import FLAGS
        c={**dict.fromkeys(FLAGS,True),"controller_profile":"CNC_V","feed_mm_min":5,"heat_s":1,"dwell_value":0,
           "max_heat_s":2,"max_dwell_seconds":1,"dwell_unit":"seconds","path_control":"G61","work_offset":"G54","machine_profile_sha256":sha(canonical(profile))}
        return job,profile,c
    def test_historical_lexical(self):
        r=audit(b"N5 G21\r\nN10 G80\r\nN15 S300\r\nN20 F600\r\nN25 M3\r\nN30 G4 P3\r\nN35 G1 X0 Y0\r\nN40 X5\r\nN45 M5M30\r\n")
        self.assertFalse(r["absolute_mode_explicit"])
        self.assertFalse(r["production_approved"])
        self.assertEqual(r["codes"]["M30"],1)
    def test_candidate_and_gate(self):
        j,p,c=self.fixture()
        b,h=approval_hashes(j,p,c)
        self.assertEqual(h["tap_sha256"],sha(b))
        self.assertIn(b"G90",b)
        self.assertTrue(b.endswith(b"M30\r\n"))
        for key in ("io_mapping_confirmed","thermal_parameters_confirmed"):
            with self.assertRaises(ValueError): approval_hashes(j,p,dict(c,**{key:False}))
        j.production_status="draft"
        with self.assertRaises(ValueError): approval_hashes(j,p,c)
    def test_reject_discontinuous_and_bounds(self):
        j,p,c=self.fixture()
        j.paths[0].segments.append(PathSegment("LINE",Point(11,0),Point(12,0)))
        with self.assertRaises(ValueError): approval_hashes(j,p,c)
        j.paths[0].segments=[PathSegment("LINE",Point(0,0),Point(30,0))]
        with self.assertRaises(ValueError): approval_hashes(j,p,c)
    def test_revocation_type(self):
        from epscad.publishing.deploy import machine_file,check_revision
        name="modelos/example-r01/example-r01.tap"
        self.assertTrue(machine_file(name))
        with self.assertRaises(ValueError): check_revision({name:"a"},{name:"b"})

    def test_thermal_limits_and_order(self):
        j,p,c=self.fixture()
        with self.assertRaises(ValueError): approval_hashes(j,p,dict(c,heat_s=3))
        with self.assertRaises(ValueError): approval_hashes(j,p,dict(c,dwell_value=2))
        with self.assertRaises(ValueError): approval_hashes(j,p,dict(c,dwell_unit="milliseconds",dwell_value=2000))
        j.paths[0].segments.append(PathSegment("LINE",Point(10,0),Point(0,0)))
        b,h=approval_hashes(j,p,c)
        self.assertIn(b"X0.0000 Y0.0000",b)
    def test_tap_approval_binds_all_fields(self):
        from unittest.mock import patch
        from epscad.publishing.tap_release import approved_tap
        j,p,c=self.fixture()
        data,hashes=approval_hashes(j,p,c)
        expected={"dxf_sha256":"d","project_sha256":"p","profile_sha256":"m",**hashes}
        release={"approved":True,"tap_approved":True,"tap_contract":c,**expected}
        with patch("epscad.publishing.tap_release.tap_candidate",return_value=(data,expected)):
            self.assertEqual(approved_tap(None,None,None,release),data)
            for key in expected:
                with self.assertRaises(ValueError):
                    approved_tap(None,None,None,dict(release,**{key:"wrong"}))
            with self.assertRaises(ValueError): approved_tap(None,None,None,dict(release,tap_approved=False))

    def test_modal_parser_arcs_omitted_axes_overlap_and_simulation(self):
        import tempfile
        from epscad.exporters.tap_simulator import parse_tap_modal,render_tap_simulation,validate_candidate_tap
        # Historical style: omitted axes, negative-X return, collinear overlap, grouped M5M30, implicit G90
        hist=(
            b"N5 G21\r\nN10 G80\r\nN15 S300\r\nN20 F600\r\nN25 M3\r\nN30 G4 P3\r\n"
            b"N35 G1 X0 Y0\r\nN40 X100\r\nN45 Y30\r\nN50 X0\r\nN55 Y0\r\nN60 X100\r\nN65 M5M30\r\n"
        )
        p=parse_tap_modal(hist)
        self.assertEqual(p["metrics"]["omitted_axis_moves"],5)
        self.assertEqual(p["metrics"]["backtrack_x_count"],1)
        self.assertAlmostEqual(p["metrics"]["collinear_overlap_mm"],100.0,places=2)
        self.assertIn("implicit_distance_mode_missing_G90",p["warnings"])
        self.assertIn("grouped_m_codes_in_single_block",p["warnings"])
        self.assertFalse(p["production_approved"])

        # Arc program (G2/G3 with incremental IJ)
        arc_tap=(
            b"N5 G21\r\nN10 G80\r\nN15 M3\r\nN20 G4 P3\r\n"
            b"N25 G1 X0 Y0\r\nN30 G2 X20 Y0 I10 J0\r\nN35 G3 X40 Y0 I10 J0\r\nN40 M5M30\r\n"
        )
        pa=parse_tap_modal(arc_tap,default_ij_mode="incremental")
        self.assertEqual(pa["metrics"]["arc_count"],2)
        self.assertIn("implicit_ij_mode_on_arcs",pa["warnings"])
        self.assertAlmostEqual(pa["metrics"]["bbox_mm"]["width"],40.0,places=2)

        with tempfile.TemporaryDirectory() as tmp:
            out_png=Path(tmp)/"sim.png"
            render_tap_simulation(p,out_png,title="Test Sim")
            self.assertTrue(out_png.is_file() and out_png.stat().st_size>2000)

        # Candidate independent readback catches tampered coordinate
        j,prof,c=self.fixture()
        good,_=approval_hashes(j,prof,c)
        tampered=good.replace(b"X10.0000",b"X11.0000")
        with self.assertRaisesRegex(ValueError,"drift"):
            validate_candidate_tap(tampered,[(0.0,0.0),(10.0,0.0)],prof,c)

    def test_controlled_historical_tap_importer_preserves_bytes_and_blocks_approval(self):
        import json,tempfile,zipfile
        from epscad.exporters.tap_library import stage_historical_archive
        tap_a=b"N5 G21\r\nN10 G80\r\nN15 S300\r\nN20 F600\r\nN25 M3\r\nN30 G4 P3\r\nN35 G1 X0 Y0\r\nN40 X50\r\nN45 Y20\r\nN50 M5M30\r\n"
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)
            zpath=base/"hist.zip"
            with zipfile.ZipFile(zpath,"w") as z:
                z.writestr("folder/telha tp 40 5 cm.tap",tap_a)
                z.writestr("dup/telha tp 40 5 cm.tap",tap_a)
            stage=base/"staged"
            manifest=stage_historical_archive(zpath,stage)
            self.assertEqual(manifest["total_unique_programs"],1)
            rec=manifest["programs"][0]
            self.assertEqual(rec["sha256"],sha(tap_a))
            self.assertEqual((stage/rec["preserved_file"]).read_bytes(),tap_a)
            self.assertTrue((stage/rec["preview_image"]).is_file())
            self.assertFalse(rec["operator_confirmed"])
            self.assertFalse(rec["public_authorized"])
            self.assertFalse(rec["production_approved"])
            self.assertIsNone(rec["verified_nominal_dimensions_mm"])
            self.assertEqual(len(rec["duplicate_paths"]),1)
            self.assertTrue((stage/"historical_catalog_draft.json").is_file())

    def test_portal_v4_direct_tap_download_and_homologation_statuses(self):
        import json,tempfile,zipfile
        from contextlib import ExitStack
        from unittest.mock import patch
        from epscad.build import build_job
        from epscad.exporters import write_outputs
        from epscad.exporters.mach3_tap import FLAGS
        from epscad.loader import load_yaml
        from epscad.publishing.site import build_site,verified_source
        from epscad.publishing.tap_release import tap_candidate
        ROOT=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)
            spec=load_yaml(ROOT/"projects/exemplos/001_linha_500mm.yaml")
            # 1) Homologating (validated_geometry) never leaks .tap or .dxf
            spec_val=json.loads(json.dumps(spec))
            src_val=base/"src_val"
            write_outputs(build_job(spec_val),spec_val,src_val)
            # 2) Synthetic production_released TAP fixture (in-memory mock only)
            spec_prod=json.loads(json.dumps(spec))
            spec_prod["project"]["status"]="production_released"
            spec_prod["project"]["source"]["production_confirmed"]=True
            profile=load_yaml(ROOT/"machine_profiles/scara_hotwire_eps.yaml")
            profile["profile_locked"]=True
            profile["work_area"]={"x_max":2000,"y_max":1000,"z_max":200}
            profile["axes"]={k:"synthetic_fixture" for k in profile["axes"]}
            profile["hotwire"].update(wire_count=1,effective_kerf_mm=1.5,min_segment_mm=5,min_radius_mm=2)
            profile["feed"].update(default_xy_mm_min=500,slow_curve_mm_min=250)
            profile["safety"]["production_allowed"]=True
            profile["notes"]={}
            contract={**dict.fromkeys(FLAGS,True),"controller_profile":"CNC_V","feed_mm_min":400,"heat_s":250,
                      "dwell_value":2,"max_heat_s":350,"max_dwell_seconds":5,"dwell_unit":"seconds",
                      "path_control":"G61","work_offset":"G54","machine_profile_sha256":sha(canonical(profile))}
            src_prod=base/"src_prod"
            with ExitStack() as stack:
                for mod in ("epscad.validators.machine_validator","epscad.validators.production_gate","epscad.validators.geometry_validator","epscad.publishing.release","epscad.publishing.tap_release"):
                    stack.enter_context(patch(mod+".load_machine_profile",return_value=profile))
                job=build_job(spec_prod)
                self.assertFalse(job.has_errors)
                write_outputs(job,spec_prod,src_prod)
                _,report,names=verified_source(src_prod)
                tap_bytes,hashes=tap_candidate(src_prod,report,names,contract)
                reg=base/"registry.json"
                reg.write_text(json.dumps([
                    {"id":"homolog-item","revision":"r01","name":"Peça em Homologação","category":"Testes","source":str(src_val),"public_authorized":True},
                    {"id":"tap-fixture","revision":"r02","name":"Linha Sintética TAP","category":"Testes","source":str(src_prod),"public_authorized":True,
                     "public_cam_dxf_authorized":True,
                     "revision_history":[{"revision":"r01","note":"Substituída após ajuste de origem."}],
                     "release":{"approved":True,"tap_approved":True,"tap_contract":contract,**hashes}},
                ]),encoding="utf-8")
                out=base/"site_tap"
                items=build_site(reg,out,viewer_dir=base/"no-vendor")
            by_id={i["id"]:i for i in items}
            self.assertEqual(by_id["homolog-item"]["status_label"],"Em homologação")
            self.assertIsNone(by_id["homolog-item"]["machine"])
            self.assertFalse(any((out/"modelos/homolog-item-r01").glob("*.tap")))
            self.assertFalse(any((out/"modelos/homolog-item-r01").glob("*.dxf")))

            titem=by_id["tap-fixture"]
            self.assertEqual(titem["machine"],"tap-fixture-r02.tap")
            self.assertEqual(titem["machine_format"],"TAP")
            self.assertEqual((out/"modelos/tap-fixture-r02/tap-fixture-r02.tap").read_bytes(),tap_bytes)
            self.assertTrue((out/"modelos/tap-fixture-r02/tap-fixture-r02.dxf").is_file())
            idx_html=(out/"index.html").read_text(encoding="utf-8")
            det_html=(out/"modelos/tap-fixture-r02/index.html").read_text(encoding="utf-8")
            self.assertIn("BAIXAR ARQUIVO MACH3 (.TAP)",idx_html)
            self.assertIn("BAIXAR ARQUIVO MACH3 (.TAP)",det_html)
            self.assertIn("Em homologação",idx_html)
            self.assertIn("Revisão substituída",det_html)
            self.assertIn("Desenho CAM (DXF R12)",det_html)
            with zipfile.ZipFile(out/"modelos/tap-fixture-r02"/titem["bundle"]) as z:
                self.assertIn("tap-fixture-r02.tap",z.namelist())
                self.assertNotIn("05_project.locked.yaml",z.namelist())

    def test_local_trial_without_commercial_release(self):
        from epscad.exporters.mach3_tap import render_trial_tap, render_tap
        j,p,c=self.fixture()
        j.production_status="validated_geometry"
        p.update(id="scara_hotwire_eps",unit="mm",process_type="hotwire_2d",profile_locked=False)
        p["safety"]["production_allowed"]=False
        c["machine_profile_sha256"]=sha(canonical(p))
        data=render_trial_tap(j,p,c)
        self.assertTrue(data.endswith(b"M30\r\n"))
        self.assertFalse(p["profile_locked"])
        self.assertFalse(p["safety"]["production_allowed"])
        with self.assertRaises(ValueError): render_tap(j,p,c)
        with self.assertRaises(ValueError): render_trial_tap(j,p,dict(c,limits_confirmed=False))
        with self.assertRaises(ValueError): render_trial_tap(j,p,dict(c,machine_profile_sha256="wrong"))
        j.production_status="draft"
        with self.assertRaises(ValueError): render_trial_tap(j,p,c)

    def test_tp40_planners_and_prepare_trial_end_to_end_for_all_five_portal_models(self):
        import json, tempfile, yaml
        from scripts.prepare_mach3_trial import prepare_trial
        from epscad.cam.tp40_planner import PORTAL_MODELS, build_trial_project_spec, plan_portal_model, plan_tp40_base_lisa
        from epscad.exporters.mach3_tap import FLAGS
        from epscad.exporters.tap_simulator import parse_tap_modal

        # Verify historical pocket reconstruction exact geometry (50 segments, 986x67 mm, 21 -X returns)
        hist_plan=plan_tp40_base_lisa(min_thickness_mm=31.0,strategy="historical_pocket")
        self.assertEqual(hist_plan["metrics"]["segment_count"],50)
        self.assertEqual(hist_plan["metrics"]["backtrack_x_count"],21)
        self.assertAlmostEqual(hist_plan["metrics"]["bbox_mm"]["width"],986.0,places=4)
        self.assertAlmostEqual(hist_plan["metrics"]["bbox_mm"]["height"],67.0,places=4)
        self.assertAlmostEqual(hist_plan["metrics"]["total_length_mm"],3005.365,places=2)

        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)
            # Synthetic test-only local machine snapshot (never modifies versioned machine profile)
            snap={
                "id":"scara_hotwire_eps","unit":"mm","process_type":"hotwire_2d","profile_locked":False,
                "safety":{"production_allowed":False},
                "work_area":{"x_max":1200.0,"y_max":200.0,"z_max":0.0},
                "hotwire":{"min_segment_mm":1.0},
                "feed":{"default_xy_mm_min":600.0},
            }
            snap_path=base/"snap.yaml"
            snap_path.write_text(yaml.safe_dump(snap,sort_keys=False),encoding="utf-8")
            contract_payload={
                "purpose":"local_supervised_trial",
                "operator_trial_authorized":True,
                "contract":{
                    **dict.fromkeys(FLAGS,True),
                    "controller_profile":"CNC_V","feed_mm_min":400.0,"heat_s":150.0,
                    "dwell_value":2.0,"max_heat_s":250.0,"max_dwell_seconds":5.0,
                    "dwell_unit":"seconds","path_control":"G61","work_offset":"G54",
                    "machine_profile_sha256":sha(canonical(snap)),
                },
            }
            contract_path=base/"contract.json"
            contract_path.write_text(json.dumps(contract_payload),encoding="utf-8")

            self.assertEqual(len(PORTAL_MODELS),5)
            for meta in PORTAL_MODELS:
                bundle=plan_portal_model(meta["portal_id"])
                proj_path=base/f"{meta['portal_id']}.yaml"
                proj_path.write_text(yaml.safe_dump(build_trial_project_spec(bundle),sort_keys=False),encoding="utf-8")
                out_dir=base/f"trial_{meta['portal_id']}"
                rep=prepare_trial(proj_path,snap_path,contract_path,out_dir)
                self.assertEqual(rep["purpose"],"local_supervised_trial")
                self.assertFalse(rep["production_approved"])
                self.assertFalse(rep["approved"])
                self.assertFalse(rep["tap_approved"])
                self.assertFalse(rep["public_authorized"])
                tap_file=out_dir/"TESTE-NAO-HOMOLOGADO.tap"
                self.assertTrue(tap_file.is_file())
                self.assertTrue((out_dir/"simulacao.png").is_file())
                self.assertTrue((out_dir/"relatorio.json").is_file())
                self.assertTrue((out_dir/"LEIA-ME.txt").is_file())
                parsed=parse_tap_modal(tap_file.read_bytes())
                self.assertEqual(parsed["modal"]["distance_mode"],"G90")
                self.assertEqual(parsed["modal"]["m_sequence"],[3,5,30])
                self.assertEqual(parsed["metrics"]["arc_count"],0)
                self.assertEqual(parsed["metrics"]["backtrack_x_count"],0)
                self.assertEqual(parsed["metrics"]["collinear_overlap_mm"],0.0)
                self.assertLess(parsed["blocks"],500)

    def test_private_handoff_never_fabricates_taps_or_exposes_publicly(self):
        import json, tempfile, zipfile
        from scripts.prepare_private_handoff import build_private_handoff
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/"handoff"
            res=build_private_handoff(out,[])
            self.assertEqual(res["models_count"],5)
            self.assertFalse(res["public_catalog_allowed"])
            self.assertFalse(any(out.rglob("*.tap")))
            self.assertTrue((out/"SHA256SUMS.txt").is_file())
            self.assertTrue((out/"HANDOFF_PRIVADO_TESTES.zip").is_file())
            tpl=json.loads((out/"local_trial_contract.TEMPLATE.json").read_text(encoding="utf-8"))
            self.assertFalse(tpl["operator_trial_authorized"])
            self.assertTrue(all(v is False for k,v in tpl["contract"].items() if k.endswith("_confirmed")))
            with zipfile.ZipFile(out/"HANDOFF_PRIVADO_TESTES.zip") as zf:
                self.assertIsNone(zf.testzip())
                self.assertFalse(any(n.endswith(".tap") for n in zf.namelist()))

    def test_slab_cam_planners_and_batch_resilience(self):
        import json, tempfile, yaml
        from epscad.cam.slab_planner import SLAB_CATALOG, build_slab_trial_spec, plan_slab_section
        from epscad.exporters.mach3_tap import FLAGS
        from epscad.exporters.tap_simulator import parse_tap_modal
        from epscad.loader import load_yaml
        from scripts.prepare_mach3_batch import batch, plan_rows
        from scripts.prepare_mach3_trial import prepare_trial
        from scripts.prepare_private_handoff import build_private_handoff

        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)
            snap={
                "id":"scara_hotwire_eps","unit":"mm","process_type":"hotwire_2d","profile_locked":False,
                "safety":{"production_allowed":False},
                "work_area":{"x_max":1200.0,"y_max":200.0,"z_max":0.0},
                "hotwire":{"min_segment_mm":1.0},
                "feed":{"default_xy_mm_min":600.0},
            }
            snap_p=base/"snap.yaml"
            snap_p.write_text(yaml.safe_dump(snap,sort_keys=False),encoding="utf-8")
            contract_p=base/"contract.json"
            contract_p.write_text(json.dumps({
                "purpose":"local_supervised_trial","operator_trial_authorized":True,
                "contract":{**dict.fromkeys(FLAGS,True),"controller_profile":"CNC_V","feed_mm_min":400.0,"heat_s":150.0,
                            "dwell_value":2.0,"max_heat_s":250.0,"max_dwell_seconds":5.0,"dwell_unit":"seconds",
                            "path_control":"G61","work_offset":"G54","machine_profile_sha256":sha(canonical(snap))},
            }),encoding="utf-8")

            # 1. All 4 slab references through constant-section XY planner + prepare_trial
            variants=sorted(load_yaml(SLAB_CATALOG)["variants"])
            self.assertEqual(len(variants),4)
            for vid in variants:
                plan=plan_slab_section(vid)
                proj_p=base/f"{vid}.yaml"
                proj_p.write_text(yaml.safe_dump(build_slab_trial_spec(plan),sort_keys=False),encoding="utf-8")
                rep=prepare_trial(proj_p,snap_p,contract_p,base/f"slab_trial_{vid}")
                parsed=parse_tap_modal((base/f"slab_trial_{vid}/TESTE-NAO-HOMOLOGADO.tap").read_bytes())
                self.assertEqual(parsed["modal"]["distance_mode"],"G90")
                self.assertEqual(parsed["metrics"]["segment_count"],7)
                self.assertEqual(parsed["metrics"]["backtrack_x_count"],0)
                self.assertFalse(rep["production_approved"])

            # 2. Batch resilience: authorize 4 of 5 TP40 models -> 4 succeed, 1 blocked cleanly without aborting batch
            handoff=base/"handoff"
            build_private_handoff(handoff,[])
            rows=plan_rows(handoff)
            self.assertEqual(len(rows),5)
            approvals={r["id"]:{"trial_authorized":True,"path_sha256":r["path_sha256"],"project_sha256":r["project_sha256"]} for r in rows[:4]}
            approvals[rows[4]["id"]]={"trial_authorized":False,"path_sha256":rows[4]["path_sha256"],"project_sha256":rows[4]["project_sha256"]}
            app_p=base/"approvals.json"
            app_p.write_text(json.dumps(approvals),encoding="utf-8")
            bres=batch(handoff,snap_p,contract_p,app_p,base/"lote_out")
            statuses=[m["status"] for m in bres["models"]]
            self.assertEqual(statuses.count("trial_generated"),4)
            self.assertEqual(statuses.count("blocked"),1)
            self.assertFalse(bres["production_approved"])
            self.assertFalse(bres["public_authorized"])
