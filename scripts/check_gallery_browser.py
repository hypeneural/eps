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
            for w,h in ((800,600),(1024,600),(1024,768),(1366,768),(390,844),(320,568)):
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
                page.screenshot(path=a.screenshots/f"gallery-{w}x{h}.png")
                page.locator("#search").fill("not-a-real-model-999")
                assert page.locator("#empty").is_visible()
                page.locator("#reset-filters").click()
                assert page.locator(".model-card").first.is_visible()
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
                if len(item["images"])>1:
                    page.locator("#lightbox-next").click()
                    assert page.locator("#image-count").inner_text().startswith("2 /")
                page.keyboard.press("Escape")
                assert not page.locator("#lightbox").is_visible()
                page.screenshot(path=a.screenshots/f"detail-{w}x{h}.png",full_page=True)
                with page.expect_download() as download:
                    page.locator(".download-panel a[download]").last.click()
                assert download.value.suggested_filename.endswith(".zip")
                if not item["machine"]:
                    assert page.locator("a[href$='.dxf']").count()==0
                assert not any(x.endswith(".glb") or "model-viewer.min.js" in x for x in requests)
                assert not errors, errors
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
            context.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
    print("Browser smoke tests passed at six resolutions and without JavaScript")
if __name__=="__main__":
    main()
