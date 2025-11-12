#!/usr/bin/env python3
import argparse
import json
import re
import sys
from typing import List, Optional

from .adapters import get_adapter, SearchError

def parse_country(argv: List[str]) -> tuple[Optional[str], List[str]]:
    """
    Support shorthands like:
      medreg -de oseltamivir
      medreg --country de tramadol
    """
    country = None
    rest = []
    for token in argv:
        m = re.fullmatch(r"-([a-z]{2})", token.strip())
        if m:
            country = m.group(1)
        else:
            rest.append(token)
    return country, rest

def build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="medreg",
        description="Search national drug registries (SmPC/SPC) by country."
    )
    p.add_argument("query", nargs="+", help="Drug name (INN / brand / synonym)")
    p.add_argument("-c", "--country", help="ISO 2-letter country code, e.g., de, pl, fr")
    p.add_argument("--json", action="store_true", help="Output JSON instead of text")
    p.add_argument("--lang", help="Preferred UI language where supported (e.g., en,de,pl,fr)")
    p.add_argument("--browser", action="store_true",
                   help="Allow headless browser for JS-heavy registries (requires 'medreg[browser]' + 'playwright install')")
    p.add_argument("--timeout", type=float, default=15.0, help="Per-request timeout seconds (default: 15)")
    p.add_argument("--limit", type=int, default=15, help="Max results to return/display (default: 15)")
    return p

def print_human(results: list[dict], query: str, country: str) -> None:
    print(f'Country: {country.upper()}')
    print(f'Query:   "{query}"')
    if not results:
        print("No results.")
        return
    print("")
    for i, r in enumerate(results, 1):
        name = r.get("product_name") or r.get("name") or "(unknown)"
        print(f"{i}. {name}")
        if r.get("inn"):
            print(f"   INN: {r['inn']}")
        if r.get("form") or r.get("strength"):
            form = r.get("form")
            strength = r.get("strength")
            details = " | ".join([x for x in [form, strength] if x])
            if details:
                print(f"   {details}")
        if r.get("mah"):
            print(f"   MAH: {r['mah']}")
        if r.get("spc_url"):
            print(f"   SmPC:  {r['spc_url']}")
        if r.get("pil_url"):
            print(f"   PIL:   {r['pil_url']}")
        if r.get("detail_url"):
            print(f"   Detail:{(' ' + r['detail_url'])}")
        print("")

def main(argv: Optional[List[str]] = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]

    # Parse country shorthands like -de/-pl/-fr
    country_dash, rest = parse_country(argv)
    parser = build_argparser()
    args = parser.parse_args(rest)

    country = (args.country or country_dash or "").lower()
    if not country:
        print("Error: Please pass a country, e.g., -de or --country de", file=sys.stderr)
        return 2

    query = " ".join(args.query).strip()

    try:
        adapter = get_adapter(country)
    except SearchError as e:
        print(f"Search failed: {e}", file=sys.stderr)
        return 1

    try:
        results = adapter.search(
            query=query,
            timeout=args.timeout,
            browser=args.browser,
            lang=args.lang,
            limit=args.limit,
        )
    except SearchError as e:
        print(f"Search failed: {e}", file=sys.stderr)
        return 1

    payload = {"country": country, "query": query, "results": results}
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print_human(results, query, country)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())