import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from epscad.publishing.site import build_site
from epscad.publishing.deploy import local_inventory,check_revision,validate_state

class PublishingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.base=Path(cls.tmp.name)
        subprocess.run([sys.executable,str(ROOT/"scripts/prepare_tp40.py"),"--output",str(cls.base/"source")],check=True,capture_output=True)
        cls.entry={"id":"tp40-base-lisa","revision":"r01","name":"TP40 <teste>","category":"Telhas","source":"source","public_authorized":True}
    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()
    def registry(self,records):
        p=self.base/"registry.json"
        p.write_text(json.dumps(records),encoding="utf-8")
        return p
    def test_real_review_gallery(self):
        out=self.base/"site"
        items=build_site(self.registry([self.entry]),out)
        self.assertEqual(items[0]["specs"]["Área transversal (mm²)"],42560)
        self.assertIsNone(items[0]["machine"])
        page=(out/"index.html").read_text(encoding="utf-8")
        self.assertIn("TP40 &lt;teste&gt;",page)
        self.assertNotIn("Baixar DXF de corte",page)
        self.assertIn("Corte não liberado",page)
        self.assertNotIn("model-viewer.min.js",page)
        folder=out/"modelos/tp40-base-lisa-r01"
        self.assertTrue((folder/"modelo.glb").exists())
        self.assertLess((folder/"thumb.jpg").stat().st_size,100000)
        self.assertNotIn("historical_evidence",(folder/"especificacoes.json").read_text(encoding="utf-8"))
        with zipfile.ZipFile(folder/items[0]["bundle"]) as z:
            self.assertNotIn("review.json",z.namelist())
            self.assertFalse(any(n.endswith((".dxf",".tap",".xml",".pst")) for n in z.namelist()))
        self.assertIn("index.html",local_inventory(out))
        (folder/"thumb.jpg").write_bytes(b"changed")
        with self.assertRaises(ValueError):
            local_inventory(out)
    def test_public_presentation_has_no_operational_downloads(self):
        out=self.base/"public-presentation"
        item=build_site(self.registry([self.entry]),out)[0]
        folder=out/"modelos"/item["slug"]
        html=(folder/item["public_page"]).read_text(encoding="utf-8")
        self.assertIn("TP40 &lt;teste&gt;",html)
        self.assertIn("Especificações técnicas",html)
        self.assertIn("public-presentation",html)
        self.assertIn('id="hero-image"',html)
        self.assertIn('id="load-3d"',html)
        for forbidden in (' download','Corte não liberado','Arquivos individuais','-revisao.zip','.tap','.dxf','.stl','../../index.html','Extensão X do percurso'):
            self.assertNotIn(forbidden,html)
        self.assertIn('href="publico.html" target="_blank" rel="noopener noreferrer"',(folder/"index.html").read_text(encoding="utf-8"))
        self.assertIn("modelos/"+item["slug"]+"/publico.html",local_inventory(out))
        with zipfile.ZipFile(folder/item["bundle"]) as z:
            self.assertNotIn("publico.html",z.namelist())

    def test_no_public_permission(self):
        with self.assertRaises(ValueError):
            build_site(self.registry([dict(self.entry,public_authorized=False)]),self.base/"blocked")
    def test_duplicate_and_traversal(self):
        for suffix,records in (("dupe",[self.entry,self.entry]),("traversal",[dict(self.entry,id="../bad")])):
            with self.assertRaises(ValueError):
                build_site(self.registry(records),self.base/suffix)
    def test_tampered_review(self):
        file=self.base/"source/26_render_eps.png"
        data=file.read_bytes()
        try:
            file.write_bytes(b"bad")
            with self.assertRaises(ValueError):
                build_site(self.registry([self.entry]),self.base/"tampered")
        finally:
            file.write_bytes(data)
    def test_revision_and_inventory(self):
        old={"modelos/tp40-r01/tp40-r01.dxf":"a","modelos/tp40-r01/tp40-r01-producao.zip":"b","index.html":"c"}
        new={"index.html":"d"}
        self.assertEqual(set(check_revision(old,new)),set(old)-set(new))
        with self.assertRaises(ValueError):
            check_revision(old,dict(old,**{"modelos/tp40-r01/tp40-r01.dxf":"changed"}))
        with self.assertRaises(ValueError):
            validate_state({"format":1,"files":{"assets/..":"0"*64}})
    def test_calibration_never_public_cut(self):
        from epscad.build import build_job
        from epscad.loader import load_yaml
        from epscad.exporters import write_outputs
        spec=load_yaml(ROOT/"projects/exemplos/001_linha_500mm.yaml")
        source=self.base/"calibration"
        write_outputs(build_job(spec),spec,source)
        out=self.base/"cal-site"
        records=[dict(self.entry,id="calibration",source="calibration",release={"approved":True,"dxf_sha256":hashlib.sha256((source/"03_cutpaths_r12.dxf").read_bytes()).hexdigest()})]
        items=build_site(self.registry(records),out)
        self.assertIsNone(items[0]["machine"])
        self.assertFalse(any(out.rglob("*.dxf")))

    def test_same_review_rebuild_is_stable(self):
        a=self.base/"stable-a"; b=self.base/"stable-b"
        registry=self.registry([self.entry])
        first=build_site(registry,a)[0]
        second=build_site(registry,b)[0]
        path=Path("modelos")/first["slug"]/first["bundle"]
        self.assertEqual((a/path).read_bytes(),(b/path).read_bytes())
        self.assertEqual(first["bundle"],second["bundle"])

    def test_brand_contrast_and_gallery_contract(self):
        from PIL import Image
        from epscad.publishing.brand import palette,luminance
        logo=self.base/"logo.png"
        Image.new("RGB",(40,20),(250,200,20)).save(logo)
        primary,soft,accent=palette(logo)
        self.assertGreaterEqual(1.05/(luminance(primary)+.05),5)
        out=self.base/"design"
        items=build_site(self.registry([self.entry]),out,logo=logo)
        folder=out/"modelos"/items[0]["slug"]
        self.assertTrue((out/"assets/brand.css").is_file())
        for im in items[0]["images"]:
            self.assertTrue((folder/im["thumb"]).is_file())
        page=(folder/"index.html").read_text(encoding="utf-8")
        self.assertIn('id="lightbox"',page)
        self.assertIn('id="viewer-model"',page)
        self.assertNotIn("model-viewer.min.js",page)
        self.assertNotIn("Baixar DXF de corte",page)
        self.assertIn("assets/brand.css",local_inventory(out))

    def test_clean_integer_specs_and_local_viewer_bundle(self):
        empty_vendor=self.base/"no-vendor"
        empty_vendor.mkdir()
        out=self.base/"clean-specs"
        items=build_site(self.registry([self.entry]),out,viewer_dir=empty_vendor)
        self.assertEqual(items[0]["dimensions"],"980 × 67")
        self.assertIsInstance(items[0]["specs"]["Largura (mm)"],int)
        page=(out/"modelos"/items[0]["slug"]/"index.html").read_text(encoding="utf-8")
        self.assertIn('id="lightbox-full"',page)
        self.assertNotIn("data-local-viewer",page)
        self.assertNotIn("model-viewer.min.js",page)
        self.assertFalse((out/"assets/model-viewer.min.js").exists())

        vendor=self.base/"with-vendor"
        vendor.mkdir()
        (vendor/"model-viewer.min.js").write_text("/* vendor viewer stub */\n",encoding="utf-8")
        (vendor/"MODEL-VIEWER-LICENSE.txt").write_text("Apache License 2.0\n",encoding="utf-8")
        out_local=self.base/"local-viewer-site"
        from unittest.mock import patch
        with patch("epscad.publishing.site.VIEWER_SHA256", hashlib.sha256((vendor/"model-viewer.min.js").read_bytes()).hexdigest()), patch("epscad.publishing.site.VIEWER_LICENSE_SHA256", hashlib.sha256((vendor/"MODEL-VIEWER-LICENSE.txt").read_bytes()).hexdigest()):
            items_local=build_site(self.registry([self.entry]),out_local,viewer_dir=vendor)
        page_local=(out_local/"modelos"/items_local[0]["slug"]/"index.html").read_text(encoding="utf-8")
        self.assertIn('data-local-viewer="1"',page_local)
        self.assertNotIn("model-viewer.min.js",page_local)
        inv=local_inventory(out_local)
        self.assertIn("assets/model-viewer.min.js",inv)
        self.assertIn("assets/MODEL-VIEWER-LICENSE.txt",inv)

    def test_v3_review_download_and_vendor_integrity(self):
        out=self.base/"v3"
        items=build_site(self.registry([self.entry]),out,viewer_dir=self.base/"missing-vendor")
        item=items[0]
        folder=out/"modelos"/item["slug"]
        self.assertIn("single-model",(out/"index.html").read_text(encoding="utf-8"))
        self.assertIn("data-numbers",(out/"index.html").read_text(encoding="utf-8"))
        self.assertEqual((folder/"desenho-tecnico.png").read_bytes(),(self.base/"source/29_section_review.png").read_bytes())
        with zipfile.ZipFile(folder/item["bundle"]) as z:
            self.assertIn("desenho-tecnico.png",z.namelist())
            self.assertFalse(any(n.endswith((".dxf",".tap",".nc")) for n in z.namelist()))
        self.assertNotIn("https://ajax.googleapis.com",(out/"assets/app.js").read_text(encoding="utf-8"))
        vendor=self.base/"tampered-vendor"
        vendor.mkdir()
        (vendor/"model-viewer.min.js").write_bytes(b"bad")
        (vendor/"MODEL-VIEWER-LICENSE.txt").write_bytes(b"bad")
        with self.assertRaisesRegex(ValueError,"model-viewer integrity"):
            build_site(self.registry([self.entry]),self.base/"blocked-vendor",viewer_dir=vendor)

    def test_synthetic_positive_release_and_changed_profile_block(self):
        # Synthetic in-memory fixture; never write a confirmed profile into the repo.
        from contextlib import ExitStack
        from unittest.mock import patch
        from epscad.loader import load_yaml
        from epscad.build import build_job
        from epscad.exporters import write_outputs
        from epscad.publishing.site import verified_source
        from epscad.publishing.release import candidate_hashes
        spec=load_yaml(ROOT/"projects/exemplos/001_linha_500mm.yaml")
        spec["project"]["status"]="production_released"
        spec["project"]["source"]["production_confirmed"]=True
        profile=load_yaml(ROOT/"machine_profiles/scara_hotwire_eps.yaml")
        profile["profile_locked"]=True
        profile["work_area"]={"x_max":2000,"y_max":1000,"z_max":200}
        profile["axes"]={k:"synthetic_fixture" for k in profile["axes"]}
        profile["hotwire"].update(wire_count=1,effective_kerf_mm=1.5,min_segment_mm=5,min_radius_mm=2)
        profile["feed"].update(default_xy_mm_min=500,slow_curve_mm_min=250)
        profile["safety"]["production_allowed"]=True
        profile["notes"]={}
        source=self.base/"synthetic-release"
        entry=dict(self.entry,id="synthetic-fixture",source=source.name,name="Synthetic fixture - tests only")
        with ExitStack() as stack:
            for module in ("epscad.validators.machine_validator","epscad.validators.production_gate","epscad.validators.geometry_validator","epscad.publishing.release"):
                stack.enter_context(patch(module+".load_machine_profile",return_value=profile))
            job=build_job(spec)
            self.assertFalse(job.has_errors,[x.message for x in job.validation])
            write_outputs(job,spec,source)
            status,report,names=verified_source(source)
            hashes=candidate_hashes(source,report,names)
            with self.assertRaisesRegex(ValueError,"hash approval"):
                build_site(self.registry([entry]),self.base/"release-no-approval")
            entry["release"]={"approved":True,**hashes}
            with self.assertRaisesRegex(ValueError,"requires approved TAP"):
                build_site(self.registry([dict(entry,require_tap=True)]),self.base/"no-dxf-fallback")
            out=self.base/"release-fixture-site"
            item=build_site(self.registry([entry]),out)[0]
            self.assertEqual(item["status"],"production_released")
            folder=out/"modelos"/item["slug"]
            self.assertEqual((folder/item["machine"]).read_bytes(),(source/"03_cutpaths_r12.dxf").read_bytes())
            with zipfile.ZipFile(folder/item["bundle"]) as z:
                self.assertIn(item["machine"],z.namelist())
                self.assertNotIn("05_project.locked.yaml",z.namelist())
            self.assertIn("Baixar DXF de corte",(out/"index.html").read_text(encoding="utf-8"))
            profile["notes"]={"fixture":"changed"}
            with self.assertRaisesRegex(ValueError,"hash approval"):
                build_site(self.registry([entry]),self.base/"release-stale")
        # Real profile still blocks the very same synthetic package.
        with self.assertRaisesRegex(ValueError,"production gates"):
            build_site(self.registry([entry]),self.base/"release-real-machine-blocked")

    def test_check_release_candidate_cli_and_incremental_deploy_recovery(self):
        import os
        from ftplib import error_perm
        from unittest.mock import patch
        from epscad.publishing.deploy import deploy

        # 1) check_release_candidate.py refuses draft review package (read-only)
        res=subprocess.run([sys.executable,str(ROOT/"scripts/check_release_candidate.py"),str(self.base/"source")],capture_output=True,text=True)
        self.assertNotEqual(res.returncode,0)

        # 2) In-memory mock FTPS verifying incremental skip, revocation order, and crash recovery
        class MockFTPS:
            files={}
            ops=[]
            fail_on_upload=None
            def __init__(self,*a,**kw): self.cwd_path=""
            def __enter__(self): return self
            def __exit__(self,*a): return False
            def connect(self,h,p): pass
            def login(self,u,p): pass
            def prot_p(self): pass
            def pwd(self): return "/"+self.cwd_path
            def cwd(self,path):
                p=path.strip("/")
                if path.startswith("/"): self.cwd_path=p
                elif p and p!=".": self.cwd_path=(self.cwd_path+"/"+p).strip("/")
            def _full(self,name):
                p=name.lstrip("/")
                return (self.cwd_path+"/"+p).strip("/") if not name.startswith("/") else p
            def mkd(self,part): pass
            def nlst(self,folder="."):
                base=self._full("" if folder=="." else folder)
                pref=(base+"/") if base else ""
                names=set()
                for k in self.files:
                    if k.startswith(pref):
                        rest=k[len(pref):]
                        if rest: names.add(rest.split("/",1)[0])
                return sorted(names)
            def storbinary(self,cmd,bio):
                target=self._full(cmd.split(" ",1)[1])
                data=bio.read()
                self.ops.append(("STOR",target))
                if self.fail_on_upload and self.fail_on_upload in target:
                    type(self).fail_on_upload=None
                    raise RuntimeError("Simulated mid-deploy drop")
                self.files[target]=data
            def retrbinary(self,cmd,cb):
                target=self._full(cmd.split(" ",1)[1])
                if target not in self.files: raise error_perm("550 Not found")
                cb(self.files[target])
            def rename(self,src,dst):
                s,d=self._full(src),self._full(dst)
                self.ops.append(("RENAME",d))
                if self.fail_on_upload and self.fail_on_upload==d:
                    type(self).fail_on_upload=None
                    raise RuntimeError("Simulated mid-rename drop")
                self.files[d]=self.files.pop(s)
            def delete(self,name):
                t=self._full(name)
                if t not in self.files: raise error_perm("550 Not found")
                self.ops.append(("DELETE",t))
                del self.files[t]

        s1=self.base/"deploy-s1"; s2=self.base/"deploy-s2"
        build_site(self.registry([dict(self.entry,revision="r01")]),s1,viewer_dir=self.base/"missing-vendor")
        build_site(self.registry([dict(self.entry,revision="r02")]),s2,viewer_dir=self.base/"missing-vendor")
        env={"EPS_FTP_HOST":"mock.local","EPS_FTP_USER":"u","EPS_FTP_PASSWORD":"p","EPS_FTP_REMOTE_ROOT":"/"}
        MockFTPS.files={}; MockFTPS.ops=[]; MockFTPS.fail_on_upload=None
        with patch("epscad.publishing.deploy.FTP_TLS",MockFTPS), patch.dict(os.environ,env):
            # Initial deploy into empty root
            n1=deploy(s1,initialize=True)
            self.assertEqual(n1,len(local_inventory(s1)))
            self.assertFalse(any(".eps-upload-" in k for k in MockFTPS.files))

            # Incremental identical re-deploy skips unchanged files (0 renames except portal-state)
            MockFTPS.ops=[]
            deploy(s1,initialize=False)
            renames=[p for op,p in MockFTPS.ops if op=="RENAME"]
            self.assertEqual(renames,["portal-state.json","portal-state.json"])

            # Simulate interrupted r01 -> r02 deploy mid-transfer, then recover cleanly
            MockFTPS.ops=[]
            MockFTPS.fail_on_upload="modelos/tp40-base-lisa-r02/index.html"
            with self.assertRaisesRegex(RuntimeError,"Simulated"):
                deploy(s2,initialize=False)
            # No orphan temp file left after finally cleanup
            self.assertFalse(any(".eps-upload-" in k for k in MockFTPS.files))
            # Retry recovers completely, revokes stale r01 files, and leaves exact s2 inventory
            MockFTPS.ops=[]
            deploy(s2,initialize=False)
            self.assertFalse(any("tp40-base-lisa-r01" in k for k in MockFTPS.files))
            self.assertTrue("modelos/tp40-base-lisa-r02/index.html" in MockFTPS.files)
            self.assertEqual(set(MockFTPS.files.keys()),set(local_inventory(s2).keys())|{"portal-state.json"})
            # Stale non-machine visual files removed AFTER index.html switch
            idx_pos=next(i for i,(op,p) in enumerate(MockFTPS.ops) if op=="RENAME" and p=="index.html")
            del_positions=[i for i,(op,p) in enumerate(MockFTPS.ops) if op=="DELETE" and "tp40-base-lisa-r01" in p]
            self.assertTrue(del_positions and all(i>idx_pos for i in del_positions))
