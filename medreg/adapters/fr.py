from __future__ import annotations
from typing import Optional, List, Dict
import re
from urllib.parse import urljoin

from . import base
from .__init__ import SearchError

BASE = "https://base-donnees-publique.medicaments.gouv.fr/"

def _extract_results_from_search(html: str, limit: int) -> List[Dict]:
    soup = base.soupify(html)
    results: List[Dict] = []
    # The FR BDPM search typically lists "spécialités" with links to detail pages.
    # Heuristic: search for anchors whose href contains 'affichageDoc.php' or '/extrait.php'
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)
        if not text:
            continue
        if "affichageDoc.php" in href or "extrait.php" in href or "fiche" in href:
            url = urljoin(BASE, href)
            # Filter obvious navigation links
            if "telechargement" in href.lower():
                continue
            if text and len(text) >= 3:
                results.append({"product_name": text, "detail_url": url})
        if len(results) >= limit:
            break
    # De-duplicate by URL
    seen = set()
    uniq = []
    for r in results:
        u = r["detail_url"]
        if u not in seen:
            uniq.append(r)
            seen.add(u)
    return uniq[:limit]

def _maybe_extract_docs(detail_html: str) -> Dict[str, str]:
    soup = base.soupify(detail_html)
    out: Dict[str, str] = {}
    # On FR BDPM, RCP (SmPC) links often reference PDF or have label 'RCP' or 'Résumé des caractéristiques du produit'.
    for a in soup.find_all("a", href=True):
        label = a.get_text(" ", strip=True)
        href = a["href"]
        low = label.lower()
        if "rcp" in low or "caractéristiques du produit" in low or "résumé" in low:
            out["spc_url"] = urljoin(BASE, href)
        if "notice" in low or "PIL" in low or "notice patient" in low:
            out["pil_url"] = urljoin(BASE, href)
    return out

def search(*, query: str, timeout: float, browser: bool, lang: Optional[str], limit: int) -> list[dict]:
    # FR search endpoint (server-rendered) - try broad query field by characters
    # Known pattern: 'recherche-de-specialites?txtCaracteres=<q>'
    params = {
        "txtCaracteres": query,
        "page": "1",
        "affNomSubstances": "1",   # include substance names
        "affListe": "0",
        "isDisponibilite": "0",
    }
    try:
        resp = base.simple_get(urljoin(BASE, "recherche-de-specialites"), timeout=timeout, params=params)
    except Exception as e:
        raise SearchError(f"FR: search request failed: {e}")

    results = _extract_results_from_search(resp.text, limit=limit)
    # Optionally enrich each result with RCP/PIL links by visiting the detail page (best-effort)
    enriched = []
    for r in results:
        out = dict(r)
        detail_url = r.get("detail_url")
        if detail_url:
            try:
                det = base.simple_get(detail_url, timeout=timeout)
                docs = _maybe_extract_docs(det.text)
                out.update(docs)
            except Exception:
                pass
        enriched.append(out)
    return enriched