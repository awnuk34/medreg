from __future__ import annotations

from typing import Optional, List, Dict
from urllib.parse import urljoin

from . import base
from .__init__ import SearchError

SEARCH_URL = "https://rejestry.ezdrowie.gov.pl/rpl/search/public"
API_SEARCH_PREFIX = "https://rejestry.ezdrowie.gov.pl/api/rpl/public/medicinal-products/search"
API_PRODUCT = "https://rejestry.ezdrowie.gov.pl/api/rpl/medicinal-products/{product_id}"
API_DOCUMENTS = "https://rejestry.ezdrowie.gov.pl/api/rpl/medicinal-products/{product_id}/documents"


def _search_with_browser(query: str, timeout: float, limit: int) -> List[Dict]:
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    except ImportError:
        raise SearchError(
            "PL: browser automation requested but Playwright is not installed. "
            "Install medreg[browser] and run 'playwright install chromium'."
        )

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.goto(SEARCH_URL, timeout=int(timeout * 1000))
            page.wait_for_load_state("domcontentloaded")

            # Accept cookie banners if present
            for selector in [
                "button:has-text('Akceptuj')",
                "button:has-text('Zaakceptuj')",
                "button:has-text('Accept')",
                "button:has-text('Zgadzam się')",
            ]:
                try:
                    page.click(selector, timeout=1500)
                except Exception:
                    pass

            # Find the iframe that actually hosts the search app
            target_frame = None
            for _ in range(12):
                for frame in page.frames:
                    url = (frame.url or "").lower()
                    if "registry/rpl" in url or "rpl" in frame.name.lower():
                        target_frame = frame
                        break
                if target_frame:
                    break
                page.wait_for_timeout(250)

            if target_frame is None:
                target_frame = page.main_frame

            # Locate the search input inside the target frame
            field = None
            selectors = [
                "input[formcontrolname='phrase']",
                "input[formcontrolname='query']",
                "input[formcontrolname='searchPhrase']",
                "input[placeholder*='szuk']",
                "input[type='search']",
                "input.mat-input-element",
                "input[type='text']",
            ]
            for sel in selectors:
                try:
                    field = target_frame.wait_for_selector(
                        sel, timeout=2000, state="visible"
                    )
                    if field:
                        break
                except PlaywrightTimeout:
                    continue

            if field is None:
                raise SearchError("PL: could not locate the search box on the RPL page.")

            field.fill("")
            field.type(query)

            clicked = False
            for btn in [
                "button[type='submit']",
                "button:has-text('Szukaj')",
                "button:has-text('Szukaj produktu')",
                "button:has-text('Wyszukaj')",
                "button.mat-raised-button",
            ]:
                try:
                    target_frame.click(btn, timeout=1500)
                    clicked = True
                    break
                except Exception:
                    continue

            if not clicked:
                field.press("Enter")

            response = page.wait_for_response(
                lambda r: r.url.startswith(API_SEARCH_PREFIX) and r.request.method == "POST",
                timeout=int(timeout * 1000),
            )
            data = response.json()
        finally:
            browser.close()

    records = data.get("content") or data.get("items") or []
    results: List[Dict] = []

    for item in records:
        product_id = item.get("id") or item.get("medicinalProductId")
        name = (
            item.get("tradeName")
            or item.get("fullName")
            or item.get("name")
            or item.get("displayName")
        )
        substances = item.get("activeSubstances") or item.get("substances") or []
        inn = ", ".join(
            s.get("name") if isinstance(s, dict) else str(s) for s in substances
        ) or None
        form = item.get("pharmaceuticalForm") or item.get("form")
        strength = item.get("strength") or item.get("dose")
        mah = item.get("marketingAuthorisationHolder") or item.get("mahName")

        detail_url = None
        if product_id:
            detail_url = (
                SEARCH_URL.rstrip("/") + f"/details/{product_id}"
            )

        entry: Dict[str, Optional[str]] = {
            "product_name": name,
            "inn": inn,
            "form": form,
            "strength": strength,
            "mah": mah,
            "detail_url": detail_url,
        }

        if product_id:
            try:
                detail = base.simple_get(
                    API_PRODUCT.format(product_id=product_id), timeout=timeout
                ).json()
                entry["mah"] = entry["mah"] or detail.get("marketingAuthorisationHolder")
            except Exception:
                pass

            try:
                docs = base.simple_get(
                    API_DOCUMENTS.format(product_id=product_id), timeout=timeout
                ).json() or []
                for doc in docs:
                    doc_type = (doc.get("documentType") or "").lower()
                    url = doc.get("downloadUrl")
                    if not url:
                        continue
                    full_url = urljoin(SEARCH_URL, url)
                    if "rcp" in doc_type or "charakterystyka" in doc_type:
                        entry["spc_url"] = full_url
                    if "ulotka" in doc_type or "pil" in doc_type or "patient" in doc_type:
                        entry["pil_url"] = full_url
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