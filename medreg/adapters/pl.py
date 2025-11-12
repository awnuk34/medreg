from __future__ import annotations
from typing import Optional, List, Dict
from urllib.parse import urljoin

from . import base
from .__init__ import SearchError

# Poland registry (RPL) public search:
RPL_ROOT = "https://rejestry.ezdrowie.gov.pl/"

def _search_with_browser(query: str, timeout: float, limit: int) -> List[Dict]:
    # Requires extra 'browser' dependency and 'playwright install'
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise SearchError("PL: --browser requested but Playwright is not installed. Install with: pip install 'medreg[browser]' && playwright install")

    results: List[Dict] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.goto(urljoin(RPL_ROOT, "rpl/search/public"), timeout=int(timeout * 1000))
            # Accept cookies if banner present
            for sel in ["button:has-text('Akceptuj')", "button:has-text('Zaakceptuj')", "button:has-text('Accept')"]:
                try:
                    page.click(sel, timeout=1000)
                except Exception:
                    pass

            # Fill the generic search input (heuristic)
            # Try common selectors
            candidates = [
                "input[placeholder*='Szukaj']",
                "input[placeholder*='wyszuk']",
                "input[type='search']",
                "input[type='text']",
                "input[name*='query']",
            ]
            filled = False
            for sel in candidates:
                try:
                    page.fill(sel, query, timeout=2000)
                    filled = True
                    try:
                        page.press(sel, "Enter", timeout=1500)
                    except Exception:
                        pass
                    break
                except Exception:
                    continue
            if not filled:
                # last resort: pick first input
                inputs = page.query_selector_all("input")
                if inputs:
                    inputs[0].fill(query)
                    try:
                        inputs[0].press("Enter")
                    except Exception:
                        pass

            # Try clicking a search button
            for sel in ["button:has-text('Szukaj')", "button:has-text('Wyszukaj')", "button:has-text('Search')", "button[type='submit']"]:
                try:
                    page.click(sel, timeout=1000)
                    break
                except Exception:
                    continue

            page.wait_for_timeout(1800)

            # Collect result entries (anchors within result container)
            anchors = page.query_selector_all("a")
            items: List[Dict] = []
            for a in anchors[:500]:
                href = a.get_attribute("href") or ""
                text = (a.inner_text() or "").strip()
                if not href or not text:
                    continue
                # Heuristics to skip navigation
                low = text.lower()
                if any(w in low for w in ["polityka", "cookies", "kontakt", "logowanie", "rejestry", "pomoc"]):
                    continue
                # Keep likely drug entries
                if len(text) >= 3:
                    items.append({"product_name": text, "detail_url": href if href.startswith("http") else urljoin(page.url, href)})
                if len(items) >= limit:
                    break

            results = items[:limit]
        finally:
            browser.close()
    return results

def search(*, query: str, timeout: float, browser: bool, lang: Optional[str], limit: int) -> list[dict]:
    # The PL RPL public search frequently uses JS-rendered components and dynamic queries.
    # requests-only scraping is unreliable. Use --browser for robust results.
    if not browser:
        raise SearchError("PL: This registry typically requires JavaScript. Re-run with --browser (and install Playwright).")
    return _search_with_browser(query, timeout=timeout, limit=limit)