"""Batch website, status, and name updates via production API."""
import time
import requests

BASE = "https://energy-tracker-production-39a1.up.railway.app"

WEBSITE_UPDATES = [
    ("NVA.TO",  "https://nvaenergy.com"),
    ("GIFI",    "https://www.gulfisland.com"),
    ("NR",      "https://www.newpark.com"),
    ("TNP",     "https://www.tenn.gr"),
    ("VTNR",    "https://www.vertexenergy.com"),
    ("TSE",     "https://www.trinseo.com"),
    ("TETY.ST", "https://www.tethysoil.com"),
    ("HUSA",    "https://www.houstonamerican.com"),
    ("COE.AX",  "https://www.cooperenergy.com.au"),
    ("I3E.L",   "https://www.i3.energy"),
    ("BROG",    "https://www.broogeenergy.com"),
]

STATUS_UPDATES = [
    ("ERF",    "Acquired", "Chord Energy",    "Acquired by Chord Energy on May 31 2024 for $11B cash-and-stock, delisted from NYSE and TSX"),
    ("NVA.TO", "Acquired", "Ovintiv",         "Acquired by Ovintiv in November 2025 for CA$3.8B cash-and-stock"),
    ("PHX",    "Acquired", "WhiteHawk Energy", "PHX Minerals acquired by WhiteHawk Energy, website redirects to whitehawkenergy.com"),
]

NAME_UPDATES = [
    ("CGG.PA", "Viridien (formerly CGG)"),
    ("COE.AX", "Amplitude Energy (formerly Cooper Energy)"),
]

def lookup(ticker):
    r = requests.get(f"{BASE}/companies/by-ticker/{ticker}", timeout=10)
    return r.json() if r.ok else None

def update(company_id, payload):
    r = requests.put(f"{BASE}/companies/{company_id}", json=payload, timeout=10)
    return r.ok

results = []

print("\n--- Website updates ---")
for ticker, website in WEBSITE_UPDATES:
    c = lookup(ticker)
    if not c:
        results.append(("website", ticker, "—", website, "NOT FOUND"))
        continue
    ok = update(c["id"], {"website": website})
    results.append(("website", ticker, c["name"], website, "updated" if ok else "FAILED"))
    print(f"  {ticker}: {'ok' if ok else 'FAILED'}")
    time.sleep(0.2)

print("\n--- Status updates ---")
for ticker, status, acquired_by, notes in STATUS_UPDATES:
    c = lookup(ticker)
    if not c:
        results.append(("status", ticker, "—", acquired_by, "NOT FOUND"))
        continue
    ok = update(c["id"], {"status": status, "acquired_by": acquired_by, "acquisition_notes": notes})
    results.append(("status", ticker, c["name"], acquired_by, "updated" if ok else "FAILED"))
    print(f"  {ticker}: {'ok' if ok else 'FAILED'}")
    time.sleep(0.2)

print("\n--- Name updates (rebrands) ---")
for ticker, new_name in NAME_UPDATES:
    c = lookup(ticker)
    if not c:
        results.append(("name", ticker, "—", new_name, "NOT FOUND"))
        continue
    ok = update(c["id"], {"name": new_name})
    results.append(("name", ticker, c["name"], new_name, "updated" if ok else "FAILED"))
    print(f"  {ticker}: {c['name']} -> {new_name} {'ok' if ok else 'FAILED'}")
    time.sleep(0.2)

print("\n" + "=" * 95)
print(f"{'Type':<8} {'Ticker':<10} {'DB Name':<38} {'Value':<28} {'Result'}")
print("-" * 95)
for type_, ticker, name, value, result in results:
    print(f"{type_:<8} {ticker:<10} {name[:36]:<38} {value[:26]:<28} {result}")

updated = sum(1 for *_, r in results if r == "updated")
failed  = sum(1 for *_, r in results if r == "FAILED")
print(f"\nTotal: {updated} updated, {failed} failed, {len(results)-updated-failed} not found")
