from __future__ import annotations

from typing import Optional, List, Dict
from urllib.parse import urljoin

from . import base
from .__init__ import SearchError

SEARCH_URL = "https://rejestry.ezdrowie.gov.pl/rpl/search/public"
API_SEARCH = "https://rejestry.ezdrowie.gov.pl/api/rpl/public/medicinal-products/search"
API_PRODUCT = "https://rejestry.ezdrowie.gov.pl/api/rpl/medicinal-products/{product_id}"
API_DOCUMENTS = "https://rejestry.ezdrowie.gov.pl/api/rpl/medicinal-products/{product_id}/documents"


def _search_with_browser(query: str, timeout: float, limit: int) -> List[Dict]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise SearchError(
            "PL: browser automation requested but Playwright is not installed. "
            "Install medreg[browser] and run 'playwright install'."
        )

    results: List[Dict] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.goto(SEARCH_URL, timeout=int(timeout * 1000))

            for sel in [
                "button:has-text('Akceptuj')",
                "button:has-text('Zaakceptuj')",
                "button:has-text('Accept')",
            ]:
                try:
                    page.click(sel, timeout=1500)
                except Exception:
                    pass

            search_selector = "input[formcontrolname='query']"
            page.wait_for_selector(search_selector, timeout=int(timeout * 1000))
            page.fill(search_selector, query)
            page.click("button[type='submit']", timeout=int(timeout * 1000))

            response = page.wait_for_response(
                lambda r: r.url.startswith(API_SEARCH) and r.request.method == "POST",
                timeout=int(timeout * 1000),
            )
            data = response.json()
        finally:
            browser.close()

    items = data.get("content") or data.get("items") or []
    for item in items:
        product_id = item.get("id") or item.get("medicinalProductId")
        name = item.get("tradeName") or item.get("fullName") or item.get("name")
        substances = item.get("activeSubstances") or item.get("substances") or []
        inn = ", ".join(s.get("name") if isinstance(s, dict) else s for s in substances)
        form = item.get("pharmaceuticalForm") or item.get("form")
        strength = item.get("strength")
        mah = item.get("marketingAuthorisationHolder") or item.get("mahName")

        detail_url = (
            SEARCH_URL.rstrip("/") + f"/details/{product_id}"
            if product_id
            else None
        )

        entry = {
            "product_name": name,
            "inn": inn or None,
            "form": form or None,
            "strength": strength or None,
            "mah": mah or None,
            "detail_url": detail_url,
        }

        if product_id:
            try:
                detail = base.simple_get(API_PRODUCT.format(product_id=product_id), timeout=timeout)
                detail_json = detail.json()
                entry["mah"] = entry["mah"] or detail_json.get("marketingAuthorisationHolder")
            except Exception:
                pass

            try:
                docs = base.simple_get(API_DOCUMENTS.format(product_id=product_id), timeout=timeout).json()
                for doc in docs or []:
                    doc_type = (doc.get("documentType") or "").lower()
                    url = doc.get("downloadUrl")
                    if not url:
                        continue
                    if "rcp" in doc_type or "charakterystyka" in doc_type:
                        entry["spc_url"] = urljoin(SEARCH_URL, url)
                    if "ulotka" in doc_type or "pil" in doc_type or "patient" in doc_type:
                        entry["pil_url"] = urljoin(SEARCH_URL, url)
            except Exception:
                pass

        results.append(entry)
        if len(results) >= limit:
            break

    return results


def search(*, query: str, timeout: float, browser: bool, lang: Optional[str], limit: int) -> list[dict]:
    if not browser:
        raise SearchError(
            "PL: registry is JavaScript-driven. Re-run with --browser "
            "after installing 'medreg[browser]' and running 'playwright install chromium'."
        )
    return _search_with_browser(query=query, timeout=timeout, limit=limit)