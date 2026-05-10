"""Final batch website, status, name, and skip-flag updates via production API."""
import time
import requests

BASE = "https://energy-tracker-production-39a1.up.railway.app"

WEBSITE_UPDATES = [
    ("CLCO",     "https://www.coolcoltd.com"),
    ("POL.PK",   "https://www.pakoil.com.pk"),
    ("ALKEM.PA", "https://www.berkem.com"),
    ("ESSO.BK",  "https://www.exxonmobil.co.th"),
]

STATUS_UPDATES = [
    ("CLCO", "Acquired", "EPS Ventures Ltd",
     "Cool Company taken private through merger with EPS Ventures Ltd subsidiary, delisted from NYSE and Euronext Oslo"),
]

NAME_UPDATES = [
    ("ESSO.BK", "Esso (Thailand)"),
]

NO_WEB_TICKERS = [
    "ABRJ.OM", "MHAS.OM", "SOOR.KW", "SUWP.OM", "BPCC.KW",
    "GICI.OM", "IPG.KW",  "NGCI.OM", "NAPESCO.KW", "OCHL.OM",
    "OOMS.OM", "OQGN.OM", "OULAFUEL.KW", "SENERGY.KW", "WEII.V",
]

def lookup(ticker):
    r = requests.get(f"{BASE}/companies/by-ticker/{ticker}", timeout=10)
    return r.json() if r.ok else None

def update(company_id, payload):
    r = requests.put(f"{BASE}/companies/{company_id}", json=payload, timeout=10)
    return r.ok

results = []

for ticker, website in WEBSITE_UPDATES:
    c = lookup(ticker)
    if not c:
        results.append(("website", ticker, "NOT FOUND", website, "skipped"))
        continue
    ok = update(c["id"], {"website": website})
    results.append(("website", ticker, c["name"], website, "updated" if ok else "FAILED"))
    time.sleep(0.2)

for ticker, status, acquired_by, notes in STATUS_UPDATES:
    c = lookup(ticker)
    if not c:
        results.append(("status", ticker, "NOT FOUND", acquired_by, "skipped"))
        continue
    ok = update(c["id"], {"status": status, "acquired_by": acquired_by, "acquisition_notes": notes})
    results.append(("status", ticker, c["name"], acquired_by, "updated" if ok else "FAILED"))
    time.sleep(0.2)

for ticker, new_name in NAME_UPDATES:
    c = lookup(ticker)
    if not c:
        results.append(("name", ticker, "NOT FOUND", new_name, "skipped"))
        continue
    ok = update(c["id"], {"name": new_name})
    results.append(("name", ticker, c["name"], new_name, "updated" if ok else "FAILED"))
    time.sleep(0.2)

for ticker in NO_WEB_TICKERS:
    c = lookup(ticker)
    if not c:
        results.append(("no-web", ticker, "NOT FOUND", "—", "skipped"))
        continue
    already_skip = c.get("skip_market_poll", False)
    # Always set acquisition_notes; only flip skip flag if not already set
    payload = {"acquisition_notes": "No web presence found - regional exchange only"}
    ok = update(c["id"], payload)
    flag = "already set" if already_skip else "flagged"
    results.append(("no-web", ticker, c["name"], "skip+note", f"{flag}" if ok else "FAILED"))
    time.sleep(0.2)

print("=" * 100)
print(f"{'Type':<8} {'Ticker':<14} {'DB Name':<36} {'Value':<24} {'Result'}")
print("-" * 100)
for type_, ticker, name, value, result in results:
    print(f"{type_:<8} {ticker:<14} {name[:34]:<36} {value[:22]:<24} {result}")

updated  = sum(1 for *_, r in results if r in ("updated", "already set", "flagged"))
failed   = sum(1 for *_, r in results if r == "FAILED")
skipped  = sum(1 for *_, r in results if r == "skipped")
print(f"\nTotal: {updated} updated/flagged, {failed} failed, {skipped} not found")
