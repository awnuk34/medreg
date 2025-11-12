from __future__ import annotations
from typing import Optional, List, Dict
from urllib.parse import urljoin

from . import base
from .__init__ import SearchError

# Germany uses PharmNet.Bund / AMIce public modules.
# The UI and endpoints can be dynamic; requests-only is often unreliable.
# We provide a headless-browser flow; for requests-only we return a clear guidance.

PHARMNET_ROOT = "https://www.pharmnet-bund.de/"

def _search_with_browser(query: str, timeout: float, limit: int) -> List[Dict]:
    # Requires extra 'browser' dependency and 'playwright install'
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise SearchError("DE: --browser requested but Playwright is not installed. Install with: pip install 'medreg[browser]' && playwright install")

    results: List[Dict] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            # Go to PharmNet public info system landing
            page.goto("https://www.pharmnet-bund.de/PharmNet/DE/Oeffentlichkeit/Arzneimittel-Informationssystem/_node.html", timeout=int(timeout * 1000))
            # Try to find a link to the public AMIce search (Arzneimittel)
            # Click the first link containing "Arzneimittel-Informationssystem" or "AMIce"
            # Then attempt to find a search field on the resulting page.
            # Note: This is heuristic; adjust selectors if the site updates.
            # Try common paths first:
            # Some pages embed an <iframe> for the search; we navigate to likely search module directly if present.
            # As a fallback, navigate to the AMIce module description and follow "zum Suchformular".
            try:
                # Jump to AMIce module page if present
                page.click("a:has-text('AMIce')", timeout=3000)
            except Exception:
                pass

            # Heuristic: visit the Arzneimittel search module if known path exists
            # We try a set of likely URLs
            candidates = [
                "https://www.bfarm.de/DE/Arzneimittel/Arzneimittelinformationen/Arzneimittel-recherchieren/AMIce/_node.html",
            ]
            for url in candidates:
                try:
                    page.goto(url, timeout=int(timeout * 1000))
                    break
                except Exception:
                    continue

            # Find any input on the page and try searching with ENTER
            # Then collect links that look like product result entries (this may render in an iframe).
            # If iframe exists, switch into it and try again.
            def try_in_context(c):
                try:
                    c.fill("input[type='text']", query, timeout=2000)
                except Exception:
                    inputs = c.query_selector_all("input")
                    if inputs:
                        inputs[0].fill(query)
                try:
                    c.press("input[type='text']", "Enter", timeout=2000)
                except Exception:
                    # Try clicking a button with label 'Suchen' or 'Search'
                    for sel in ["button:has-text('Suchen')", "input[type='submit']", "button"]:
                        try:
                            c.click(sel, timeout=1000)
                            break
                        except Exception:
                            continue

                c.wait_for_timeout(1500)
                anchors = c.query_selector_all("a")
                items = []
                for a in anchors[:400]:
                    href = a.get_attribute("href") or ""
                    text = (a.inner_text() or "").strip()
                    if not text or not href:
                        continue
                    # Heuristic: exclude navigation; keep records that look like drug entries
                    if "Arzneimittel" in text or "Fachinformation" in text or len(text) > 8:
                        items.append({"product_name": text, "detail_url": c.url if href.startswith("#") else (href if href.startswith("http") else urljoin(c.url, href))})
                    if len(items) >= limit:
                        break
                return items

            # Try main context
            items = try_in_context(page)
            # Try inside iframes if needed
            if not items:
                for frame in page.frames:
                    if frame == page.main_frame:
                        continue
                    try:
                        items = try_in_context(frame)
                        if items:
                            break
                    except Exception:
                        continue

            results = items[:limit]
        finally:
            browser.close()
    return results

def search(*, query: str, timeout: float, browser: bool, lang: Optional[str], limit: int) -> list[dict]:
    if not browser:
        raise SearchError("DE: This registry often requires JavaScript/interactive search. Re-run with --browser (and install Playwright).")
    return _search_with_browser(query, timeout=timeout, limit=limit)