"""Batch website and name updates via production API."""
import time
import requests

BASE = "https://energy-tracker-production-39a1.up.railway.app"

WEBSITE_UPDATES = [
    ("BOROUGE.AE", "https://www.borouge.com"),
    ("DANA.AE",    "https://www.danagas.com"),
    ("TAQA.AE",    "https://www.taqa.com"),
    ("IQCD.QA",    "https://www.iq.com.qa"),
    ("MPHC.QA",    "https://www.mphc.com.qa"),
    ("RZ8G.F",     "https://www.romgaz.ro"),
    ("SRS.MI",     "https://www.saras.it"),
    ("PSO.PK",     "https://www.psopk.com"),
    ("PPL.PK",     "https://www.ppl.com.pk"),
    ("DNMR",       "https://www.danimerscientific.com"),
    ("HUSA",       "https://www.houstonamerican.com"),
    ("OGDC.PK",    "https://www.ogdcl.com"),
    ("MARI.PK",    "https://www.marigas.com.pk"),
    ("LCI.PK",     "https://www.luckycoreindustries.com"),
]

NAME_UPDATES = [
    ("COE.AX", "Amplitude Energy (formerly Cooper Energy)"),
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

for ticker, new_name in NAME_UPDATES:
    c = lookup(ticker)
    if not c:
        results.append(("name", ticker, "NOT FOUND", new_name, "skipped"))
        continue
    ok = update(c["id"], {"name": new_name})
    results.append(("name", ticker, c["name"], new_name, "updated" if ok else "FAILED"))
    time.sleep(0.2)

print("=" * 98)
print(f"{'Type':<8} {'Ticker':<14} {'DB Name':<36} {'Value':<30} {'Result'}")
print("-" * 98)
for type_, ticker, name, value, result in results:
    print(f"{type_:<8} {ticker:<14} {name[:34]:<36} {value[:28]:<30} {result}")

updated = sum(1 for *_, r in results if r == "updated")
failed  = sum(1 for *_, r in results if r == "FAILED")
skipped = sum(1 for *_, r in results if r == "skipped")
print(f"\nTotal: {updated} updated, {failed} failed, {skipped} not found")
