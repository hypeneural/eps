"""Browser smoke test for local gallery snapshot (optional Playwright dependency)."""
import argparse
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import json
from pathlib import Path
from threading import Thread
from playwright.sync_api import sync_playwright

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--site",type=Path,required=True)
    p.add_argument("--screenshots",type=Path,required=True)
    a=p.parse_args()
    a.screenshots.mkdir(parents=True,exist_ok=True)
    items=json.loads((a.site/"catalog.json").read_text(encoding="utf-8"))
    assert items, "Browser demo needs at least one model"
    item=items[0]
    server=ThreadingHTTPServer(("127.0.0.1",0),partial(SimpleHTTPRequestHandler,directory=str(a.site.resolve())))
    thread=Thread(target=server.serve_forever,daemon=True)
    thread.start()
    url=f"http://127.0.0.1:{server.server_port}"
    def fits(page):
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth+1"), "Horizontal overflow"
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch()
            for w,h in ((800,600),(1024,600),(1024,768),(1366,768),(1920,1080),(390,844),(320,568)):
                context=browser.new_context(viewport={"width":w,"height":h},accept_downloads=True)
                page=context.new_page()
                errors=[]
                requests=[]
                page.on("pageerror",lambda e: errors.append(str(e)))
                page.on("request",lambda r: requests.append(r.url))
                page.goto(url,wait_until="networkidle")
                fits(page)
                assert page.locator(".model-card").count()==len(items)
                assert page.locator(".model-card").first.is_visible()
                assert page.locator(".model-card .whatsapp-card-link").first.get_attribute("href")==item["whatsapp_url"]
                page.screenshot(path=a.screenshots/f"gallery-{w}x{h}.png")
                page.locator("#search").fill("not-a-real-model-999")
                assert page.locator("#empty").is_visible()
                page.locator("#reset-filters").click()
                assert page.locator(".model-card").first.is_visible()
                if item["specs"].get("Largura (mm)")==980 and item["specs"].get("Altura total (mm)")==67:
                    page.locator("#search").fill("980x67")
                    assert page.locator(".model-card").first.is_visible()
                    page.locator("#search").fill("980000")
                    assert page.locator("#empty").is_visible()
                    page.locator("#reset-filters").click()
                page.locator("#list-mode").click()
                fits(page)
                page.screenshot(path=a.screenshots/f"list-{w}x{h}.png")
                page.reload()
                assert page.locator("#list-mode").get_attribute("aria-pressed")=="true"
                page.locator("#gallery-mode").click()
                if not any(i["machine"] for i in items):
                    page.locator("#ready-only").check()
                    assert page.locator("#empty").is_visible()
                    page.locator("#ready-only").uncheck()
                page.locator(".model-card .details").first.click()
                fits(page)
                assert page.locator("#hero-image").evaluate("(i)=>i.complete && i.naturalWidth>0")
                page.locator("#hero-link").click()
                assert page.locator("#lightbox").is_visible()
                assert page.locator("main").get_attribute("aria-hidden")=="true"
                assert page.locator("#lightbox-close").evaluate("(e)=>document.activeElement===e")
                for _ in range(5):
                    page.keyboard.press("Tab")
                    assert page.locator("#lightbox").evaluate("(e)=>e.contains(document.activeElement)")
                if len(item["images"])>1:
                    page.locator("#lightbox-next").click()
                    assert page.locator("#image-count").inner_text().startswith("2 /")
                page.keyboard.press("Escape")
                assert not page.locator("#lightbox").is_visible()
                assert page.locator("main").get_attribute("aria-hidden") is None
                assert page.locator("#hero-link").evaluate("(e)=>document.activeElement===e")
                page.wait_for_function("() => { const i = document.querySelector('#hero-image'); return i && i.complete && i.naturalWidth > 0; }", timeout=5000)
                page.screenshot(path=a.screenshots/f"detail-{w}x{h}.png",full_page=True)
                with page.expect_download() as download:
                    page.locator(".download-panel a[download]").last.click()
                assert download.value.suggested_filename.endswith(".zip")
                from hashlib import sha256
                local_bundle=a.site/"modelos"/item["slug"]/item["bundle"]
                assert sha256(download.value.path().read_bytes()).digest()==sha256(local_bundle.read_bytes()).digest()
                if not item["machine"]:
                    assert page.locator("a[href$='.dxf'],a[href$='.tap']").count()==0
                else:
                    with page.expect_download() as machine_download:
                        page.locator(".download-panel a.primary[download]").click()
                    assert machine_download.value.suggested_filename==item["machine"]
                    assert sha256(machine_download.value.path().read_bytes()).hexdigest()==item["machine_sha256"]
                assert not any(x.endswith(".glb") or "model-viewer.min.js" in x for x in requests)
                assert not errors, errors
                with context.expect_page() as public_tab:
                    page.locator(".public-link").click()
                public=public_tab.value
                public_errors=[]
                public.on("pageerror",lambda e:public_errors.append(str(e)))
                public.wait_for_load_state("networkidle")
                fits(public)
                assert public.url.endswith("/publico.html")
                assert public.locator("a[download], .download-panel, .other-files").count()==0
                assert public.locator("#hero-image").evaluate("(i)=>i.complete && i.naturalWidth>0")
                assert public.locator("#specifications").is_visible()
                assert public.locator("a.whatsapp-link").count()==2
                public.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                assert abs(public.locator(".public-top").bounding_box()["y"])<=2
                assert public.locator(".header-share").is_visible()
                assert public.locator(".header-share").get_attribute("aria-label")
                public.locator(".public-nav a[href='#specifications']").click()
                assert public.locator("#specifications").bounding_box()["y"]>=public.locator(".public-top").bounding_box()["height"]-2
                public.evaluate("window.scrollTo(0,0)")
                assert public.locator("a.whatsapp-link").first.get_attribute("href")==item["whatsapp_url"]
                assert public.locator("a.whatsapp-link").last.get_attribute("href")==item["whatsapp_url"]
                assert public.locator("a.whatsapp-link").first.get_attribute("target")=="_blank"
                assert page.locator("a.whatsapp-link").get_attribute("href")==item["whatsapp_url"]
                assert public.locator("meta[property=\"og:url\"]").get_attribute("content")==item["public_url"]
                assert public.locator("meta[property=\"og:image:secure_url\"]").get_attribute("content").startswith("https://")
                assert public.locator("meta[property=\"og:image:type\"]").get_attribute("content")=="image/jpeg"
                assert int(public.locator("meta[property=\"og:image:width\"]").get_attribute("content"))>=300
                assert int(public.locator("meta[property=\"og:image:height\"]").get_attribute("content"))>0
                assert public.locator("#copy-public-link").get_attribute("data-public-url")==item["public_url"]
                public.locator("#copy-public-link").click()
                public.locator("#hero-link").click()
                assert public.locator("#lightbox").is_visible()
                public.keyboard.press("Escape")
                assert not public.locator("#lightbox").is_visible()
                public.screenshot(path=a.screenshots/f"public-{w}x{h}.png",full_page=True)
                assert not public_errors,public_errors
                public.close()
                page.locator(".back a").click()
                page.locator("#search").fill(item["id"])
                page.locator(".model-card .details").first.click()
                page.locator(".back a").click()
                assert page.locator("#search").input_value()==item["id"]
                assert page.locator(".model-card").first.is_visible()
                context.close()
            context=browser.new_context(java_script_enabled=False,viewport={"width":800,"height":600},accept_downloads=True)
            page=context.new_page()
            page.goto(url)
            assert page.locator(".model-card").first.is_visible()
            with page.expect_download() as download:
                page.locator(".model-card a[download]").first.click()
            assert download.value.suggested_filename
            page.locator(".model-card .details").first.click()
            assert page.locator("#hero-link").is_visible()
            page.goto(url+"/modelos/"+item["slug"]+"/publico.html")
            assert page.locator("#hero-link").is_visible()
            assert page.locator("a[download]").count()==0
            assert page.locator("a.whatsapp-link").first.is_visible()
            assert page.locator("a.whatsapp-link").first.get_attribute("href")==item["whatsapp_url"]
            fits(page)
            context.close()
            # Check every published product, not just the first card, without JS.
            context=browser.new_context(java_script_enabled=False,viewport={"width":390,"height":844},accept_downloads=True)
            page=context.new_page()
            for m in items:
                folder=a.site/"modelos"/m["slug"]
                page.goto(url+"/modelos/"+m["slug"]+"/publico.html")
                fits(page)
                assert page.locator("a[download]").count()==0
                assert page.locator(".header-share").get_attribute("href")==m["whatsapp_url"]
                if m["machine"]:
                    page.goto(url+"/modelos/"+m["slug"]+"/index.html")
                    with page.expect_download() as dl:
                        page.locator(".download-panel a.primary[download]").click()
                    assert dl.value.suggested_filename==m["machine"]
                    assert sha256(dl.value.path().read_bytes()).hexdigest()==m["machine_sha256"]
            context.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
    print("Browser smoke tests passed at seven resolutions and without JavaScript")
if __name__=="__main__":
    main()
