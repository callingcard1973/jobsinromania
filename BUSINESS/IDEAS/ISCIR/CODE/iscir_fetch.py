#!/usr/bin/env python3
"""Fetch ISCIR pages/PDFs past the Cloudflare managed challenge using a real browser.

curl/cloudscraper get only the 11-71KB JS-challenge page; a headed Chromium solves
the challenge, banks the cf_clearance cookie, then pulls the PDF in-session.
Reusable by registry-scraper for any iscir.ro asset.
"""
import sys, time, pathlib
from playwright.sync_api import sync_playwright

LISTING = "https://iscir.ro/autorizatii-suspendate-retrase"


def fetch(listing_url: str, out_dir: str, want_ext=".pdf") -> list[str]:
    out = pathlib.Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    saved = []
    with sync_playwright() as p:
        # real Chrome + persistent profile: genuine fingerprint banks cf_clearance,
        # far higher pass rate on Cloudflare managed challenge than bundled chromium.
        profile = str(pathlib.Path(out_dir).parent / ".cf_profile")
        ctx = p.chromium.launch_persistent_context(
            profile, channel="chrome", headless=False,
            accept_downloads=True, locale="ro-RO",
            args=["--disable-blink-features=AutomationControlled"],
        )
        pg = ctx.pages[0] if ctx.pages else ctx.new_page()
        pg.goto(listing_url, wait_until="domcontentloaded", timeout=60000)
        # wait out the challenge: poll for real content; tolerate mid-challenge reloads
        pdfs = []
        print("Waiting for Cloudflare to clear (a Chrome window is open — "
              "click the 'I am human' checkbox if it appears)...")
        for _ in range(80):
            try:
                title = (pg.title() or "").lower()
                if "moment" not in title and "verify" not in title:
                    hrefs = pg.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
                    pdfs = [h for h in hrefs if h.lower().endswith(want_ext)]
                    if pdfs:
                        break
            except Exception:
                pass  # page navigating (challenge reload) — retry
            time.sleep(1.5)
        if not pdfs:
            print("NO pdf links found on cleared page. Saving page HTML for inspection.")
            (out / "_listing.html").write_text(pg.content(), encoding="utf-8")
        for url in dict.fromkeys(pdfs):
            name = url.split("/")[-1]
            r = ctx.request.get(url, timeout=60000)  # carries cf_clearance cookie
            ct = r.headers.get("content-type", "")
            if r.ok and "pdf" in ct:
                (out / name).write_bytes(r.body())
                saved.append(str(out / name)); print("SAVED", name, len(r.body()), "bytes")
            else:
                print("SKIP", name, r.status, ct)
        ctx.close()
    return saved


SEEDS = [
    "https://iscir.ro/",
    "https://iscir.ro/sectiune/autorizatii",
    "https://iscir.ro/sectiune/autorizatii/general",
    "https://iscir.ro/autorizatii-suspendate-retrase",
    "https://iscir.ro/persoane-juridice-autorizate",
    "https://iscir.ro/persoane-fizice-autorizate",
    "https://iscir.ro/legislatie",
    "https://iscir.ro/prescriptii-tehnice",
]


def crawl_all(out_dir: str, seeds=SEEDS, max_pages: int = 60) -> list[str]:
    """One persistent Chrome session: clear CF once, BFS internal links depth-1+,
    collect every same-domain .pdf, download all. Cookie persists across navigations."""
    out = pathlib.Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    saved, seen_pdf, visited = [], set(), set()
    profile = str(pathlib.Path(out_dir).parent / ".cf_profile")
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            profile, channel="chrome", headless=False, accept_downloads=True,
            locale="ro-RO", args=["--disable-blink-features=AutomationControlled"])
        pg = ctx.pages[0] if ctx.pages else ctx.new_page()
        queue = list(seeds)
        while queue and len(visited) < max_pages:
            url = queue.pop(0)
            if url in visited:
                continue
            visited.add(url)
            try:
                pg.goto(url, wait_until="domcontentloaded", timeout=60000)
            except Exception as e:
                print("nav-fail", url, str(e)[:60]); continue
            for _ in range(40):  # clear challenge if present
                try:
                    if "moment" not in (pg.title() or "").lower():
                        break
                except Exception:
                    pass
                time.sleep(1.5)
            try:
                hrefs = pg.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
            except Exception:
                continue
            for h in hrefs:
                if h.lower().endswith(".pdf"):
                    seen_pdf.add(h.split("#")[0])
                elif "iscir.ro" in h and h not in visited and len(visited) + len(queue) < max_pages:
                    if any(k in h for k in ("autoriz", "sectiune", "legisl", "prescript",
                                            "registr", "persoane")):
                        queue.append(h.split("#")[0])
            print(f"[{len(visited)}] {url}  pdfs-so-far={len(seen_pdf)} queue={len(queue)}")
        print(f"\nfound {len(seen_pdf)} unique PDF links. downloading...")
        for url in sorted(seen_pdf):
            name = url.split("/")[-1]
            dest = out / name
            if dest.exists():
                saved.append(str(dest)); continue
            try:
                r = ctx.request.get(url, timeout=90000)
                if r.ok and "pdf" in r.headers.get("content-type", ""):
                    dest.write_bytes(r.body()); saved.append(str(dest))
                    print("SAVED", name, len(r.body()))
                else:
                    print("SKIP", name, r.status, r.headers.get("content-type"))
            except Exception as e:
                print("ERR", name, str(e)[:60])
        ctx.close()
    return saved


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--all":
        dest = sys.argv[2] if len(sys.argv) > 2 else "DATA/iscir_pdfs"
        got = crawl_all(dest)
        print(f"\n{len(got)} PDF(s) in {dest}.")
    else:
        url = sys.argv[1] if len(sys.argv) > 1 else LISTING
        dest = sys.argv[2] if len(sys.argv) > 2 else "DATA"
        got = fetch(url, dest)
        print(f"\n{len(got)} file(s) saved.")
