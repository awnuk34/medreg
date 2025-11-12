### medreg

A simple CLI to search national drug registries for medicinal products and SmPC/SPC links.

- Example: `medreg -fr oseltamivir` (France)
- Example: `medreg -de tramadol` (Germany)
- Example: `medreg -pl tramadol` (Poland)

Note:
- The EMA page lists national registries but does not give direct search endpoints. Each registry has different forms, parameters, languages, and occasionally JS-only rendering or anti-bot protections.
- This CLI uses per-country adapters. France works with requests-only. Germany and Poland often need headless browser automation; enable with `--browser` and install the optional dependency.

References:
- EMA national registries list: [EMA — National registers of authorised medicines](https://www.ema.europa.eu/en/medicines/national-registers-authorised-medicines)
- Germany (BfArM/PharmNet.Bund, AMIce public DB): [BfArM AMIce](https://www.bfarm.de/DE/Arzneimittel/Arzneimittelinformationen/Arzneimittel-recherchieren/AMIce/_node.html), [PharmNet.Bund](https://www.pharmnet-bund.de/PharmNet/DE/Oeffentlichkeit/Arzneimittel-Informationssystem/_node.html)
- Poland (RPL public search): [RPL public search](https://rejestry.ezdrowie.gov.pl/rpl/search/public), [Gov.pl info](https://www.gov.pl/web/urpl/rejestr-produktow-leczniczych3)
  
Install (recommended with pipx):
- `pipx install git+https://github.com/<your-org-or-user>/medreg.git`

Or pip:
- `pip install git+https://github.com/<your-org-or-user>/medreg.git`

Usage:
- `medreg -fr oseltamivir`
- `medreg -de tramadol`
- `medreg -pl tramadol`
- JSON output: `medreg --json -fr oseltamivir`
- Allow headless browser for JS-heavy searches (DE/PL):  
  1) `pip install "medreg[browser]"`  
  2) `playwright install`  
  3) `medreg --browser -pl tramadol`

Notes and limitations:
- Respect each agency’s Terms and robots rules. Keep queries modest; medreg uses a friendly User-Agent and conservative timeouts.
- Not all products have an SmPC PDF exposed; sometimes a detail page must be visited to access docs.
- France generally works with plain HTTP parsing. Germany and Poland may require `--browser` for reliable results due to dynamic interfaces or anti-bot measures.
- Contributions welcome: add adapters for more countries under `medreg/adapters/`.

License: MIT