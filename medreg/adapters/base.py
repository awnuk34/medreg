from __future__ import annotations
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from typing import Optional
from ..utils.http import get_session

def absolutize(base: str, href: str) -> str:
    return urljoin(base, href)

def soupify(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")

def default_headers() -> dict[str, str]:
    return {
        "User-Agent": "Mozilla/5.0 (compatible; medreg/0.1; +https://example.invalid/medreg)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

def simple_get(url: str, *, timeout: float, headers: Optional[dict] = None, params: Optional[dict] = None):
    sess = get_session()
    hdrs = default_headers()
    if headers:
        hdrs.update(headers)
    resp = sess.get(url, headers=hdrs, timeout=timeout, params=params, allow_redirects=True)
    resp.raise_for_status()
    return resp