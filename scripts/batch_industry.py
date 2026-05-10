"""Batch industry update via production API."""
import time
import requests

BASE = "https://energy-tracker-production-39a1.up.railway.app"

UPDATES = [
    ("RRRP3.SA",    "Oil & Gas E&P"),
    ("ABRJ.OM",     "Oil & Gas Equipment & Services"),
    ("ADNOCDIST.AE","Oil & Gas Integrated"),
    ("ADNOCGAS.AE", "Oil & Gas Midstream"),
    ("AOI.TO",      "Oil & Gas E&P"),
    ("MHAS.OM",     "Oil & Gas Refining & Marketing"),
    ("SOOR.KW",     "Oil & Gas Refining & Marketing"),
    ("SUWP.OM",     "Utilities - Independent Power Producers"),
    ("COE.AX",      "Oil & Gas E&P"),
    ("AY",          "Utilities - Renewable"),
    ("BRY",         "Oil & Gas E&P"),
    ("BROG",        "Oil & Gas Midstream"),
    ("CNE.TO",      "Oil & Gas E&P"),
    ("DANA.AE",     "Oil & Gas E&P"),
    ("DRQ",         "Oil & Gas Equipment & Services"),
    ("ESSO.BK",     "Oil & Gas Refining & Marketing"),
    ("GIFI",        "Oil & Gas Equipment & Services"),
    ("HUSA",        "Oil & Gas E&P"),
    ("I3E.L",       "Oil & Gas E&P"),
    ("IPG.KW",      "Oil & Gas Refining & Marketing"),
    ("MARI.PK",     "Oil & Gas E&P"),
    ("MPHC.QA",     "Specialty Chemicals"),
    ("NGCI.OM",     "Oil & Gas Midstream"),
    ("NAPESCO.KW",  "Oil & Gas Equipment & Services"),
    ("NR",          "Oil & Gas Equipment & Services"),
    ("OGDC.PK",     "Oil & Gas E&P"),
    ("OOMS.OM",     "Oil & Gas Refining & Marketing"),
    ("OQGN.OM",     "Oil & Gas Midstream"),
    ("OULAFUEL.KW", "Oil & Gas Refining & Marketing"),
    ("POL.PK",      "Oil & Gas E&P"),
    ("PPL.PK",      "Oil & Gas E&P"),
    ("PSO.PK",      "Oil & Gas Refining & Marketing"),
    ("QGTS.QA",     "Oil & Gas Midstream"),
    ("RZ8G.F",      "Oil & Gas Midstream"),
    ("SRS.MI",      "Oil & Gas Refining & Marketing"),
    ("SENERGY.KW",  "Oil & Gas Equipment & Services"),
    ("STR",         "Oil & Gas E&P"),
    ("SOI",         "Oil & Gas Equipment & Services"),
    ("SMLP",        "Oil & Gas Midstream"),
    ("TAQA.AE",     "Utilities - Regulated Electric"),
    ("TETY.ST",     "Oil & Gas E&P"),
    ("TNP",         "Oil & Gas Midstream"),
    ("VTNR",        "Oil & Gas Refining & Marketing"),
    ("CGG.PA",      "Oil & Gas Equipment & Services"),
]

def lookup_by_ticker(ticker):
    r = requests.get(f"{BASE}/companies/by-ticker/{ticker}", timeout=10)
    return r.json() if r.ok else None

def update(company_id, industry):
    r = requests.put(f"{BASE}/companies/{company_id}", json={"industry": industry}, timeout=10)
    return r.ok

results = []

# Standard ticker lookups
for ticker, industry in UPDATES:
    c = lookup_by_ticker(ticker)
    if not c:
        results.append((ticker, "NOT FOUND", industry, "skipped"))
        continue
    ok = update(c["id"], industry)
    results.append((ticker, c["name"], industry, "updated" if ok else "FAILED"))
    time.sleep(0.15)

# Motiva — ticker is "N/A", look up by ID 26 directly
motiva = requests.get(f"{BASE}/companies/26", timeout=10).json()
ok = update(26, "Oil & Gas Refining & Marketing")
results.append(("N/A", motiva["name"], "Oil & Gas Refining & Marketing", "updated" if ok else "FAILED"))

print("=" * 95)
print(f"{'Ticker':<16} {'Company':<36} {'Industry':<34} Result")
print("-" * 95)
for ticker, name, industry, result in results:
    print(f"{ticker:<16} {name[:34]:<36} {industry[:32]:<34} {result}")

updated = sum(1 for *_, r in results if r == "updated")
failed  = sum(1 for *_, r in results if r == "FAILED")
skipped = sum(1 for *_, r in results if r == "skipped")
print(f"\nTotal: {updated} updated, {failed} failed, {skipped} not found")
