"""
Batch website + status updater — uses the production API (no direct DB access needed).
Run from: backend/ or any directory with requests + yfinance installed.
"""
import time
import requests
import yfinance as yf

BASE = "https://energy-tracker-production-39a1.up.railway.app"

# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

WEBSITE_UPDATES = [
    ("RRRP3.SA", "https://www.3rpetroleum.com.br"),
    ("AOI.TO",   "https://africaoilcorp.com"),
    ("AY",       "https://atlantica.com"),
    ("BRY",      "https://bry.com"),
    ("CNE.TO",   "https://canacolenergy.com"),
    ("CGG.PA",   "https://www.cgg.com"),
    ("DRQ",      "https://www.dril-quip.com"),
    ("MEG.TO",   "https://www.megenergy.com"),
    ("PKI.TO",   "https://www.parkland.ca"),
    ("STR",      "https://www.sitio.com"),
    ("SOI",      "https://www.solarisoilfield.com"),
    ("SMLP",     "https://www.summitmidstream.com"),
    ("TETY.ST",  "https://www.tethysoil.com"),
    ("VTLE",     "https://www.vitalenergy.com"),
]

STATUS_UPDATES = [
    ("ALTM",   "Acquired", "Rio Tinto",        "Acquired by Rio Tinto on March 6 2025 for $6.7B all-cash, delisted from NYSE"),
    ("MEG.TO", "Acquired", "Cenovus Energy",   "Acquired by Cenovus Energy on November 13 2025 for CA$7.9B cash-and-stock"),
    ("PKI.TO", "Acquired", "Sunoco",           "Acquired by Sunoco in 2025"),
    ("VTLE",   "Acquired", "Crescent Energy",  "Acquired by Crescent Energy on December 15 2025 for $3.1B all-stock, delisted from NYSE"),
    ("VRN",    "Acquired", "Whitecap Resources","Acquired by Whitecap Resources on May 12 2025"),
    ("PFIE",   "Acquired", "CECO Environmental","Acquired by CECO Environmental in 2025 for $122.7M"),
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def lookup_company(ticker: str) -> dict | None:
    r = requests.get(f"{BASE}/companies/by-ticker/{ticker}", timeout=10)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()

def update_company(company_id: int, payload: dict) -> bool:
    r = requests.put(f"{BASE}/companies/{company_id}", json=payload, timeout=10)
    return r.ok

def verify_ticker(ticker: str) -> tuple[str | None, str | None]:
    """Returns (longName, yfinance_website) or (None, None) on failure."""
    import sys, io
    try:
        # Suppress yfinance stderr noise (404s for delisted tickers)
        old_stderr = sys.stderr
        sys.stderr = io.StringIO()
        try:
            info = yf.Ticker(ticker).info or {}
        finally:
            sys.stderr = old_stderr
        name = info.get("longName") or info.get("shortName")
        website = info.get("website")
        return name, website
    except Exception:
        return None, None

# ---------------------------------------------------------------------------
# Website updates
# ---------------------------------------------------------------------------

print("\n=== WEBSITE UPDATES ===\n")
web_results = []

all_tickers = {t for t, _ in WEBSITE_UPDATES} | {t for t, *_ in STATUS_UPDATES}
print(f"Fetching yfinance data for {len(all_tickers)} tickers ...")
yf_cache: dict[str, tuple] = {}
for ticker in sorted(all_tickers):
    yf_cache[ticker] = verify_ticker(ticker)
    time.sleep(0.3)

for ticker, website in WEBSITE_UPDATES:
    company = lookup_company(ticker)
    if not company:
        web_results.append((ticker, "NOT FOUND", "—", "skipped"))
        continue

    yf_name, yf_website = yf_cache.get(ticker, (None, None))
    db_name = company["name"]

    # Flag if yfinance returns nothing (possible bad ticker)
    flag = ""
    if not yf_name:
        flag = " [WARN: yfinance no data]"
    elif yf_website and yf_website.rstrip("/") != website.rstrip("/"):
        flag = f" [NOTE: yfinance={yf_website}]"

    ok = update_company(company["id"], {"website": website})
    status = "updated" if ok else "FAILED"
    web_results.append((ticker, db_name, website, status + flag))

# ---------------------------------------------------------------------------
# Status updates
# ---------------------------------------------------------------------------

print("\n=== STATUS UPDATES ===\n")
status_results = []

for ticker, status, acquired_by, notes in STATUS_UPDATES:
    company = lookup_company(ticker)
    if not company:
        status_results.append((ticker, "NOT FOUND", "—", "skipped"))
        continue

    db_name = company["name"]
    payload = {
        "status": status,
        "acquired_by": acquired_by,
        "acquisition_notes": notes,
    }
    ok = update_company(company["id"], payload)
    result = "updated" if ok else "FAILED"
    status_results.append((ticker, db_name, acquired_by, result))

# ---------------------------------------------------------------------------
# Summary table
# ---------------------------------------------------------------------------

print("\n" + "=" * 80)
print("WEBSITE UPDATE RESULTS")
print("=" * 80)
print(f"{'Ticker':<12} {'DB Name':<40} {'Result'}")
print("-" * 80)
for ticker, name, website, result in web_results:
    print(f"{ticker:<12} {name[:38]:<40} {result}")

print("\n" + "=" * 80)
print("STATUS UPDATE RESULTS")
print("=" * 80)
print(f"{'Ticker':<12} {'DB Name':<40} {'Acquired By':<22} {'Result'}")
print("-" * 80)
for ticker, name, acquired_by, result in status_results:
    print(f"{ticker:<12} {name[:38]:<40} {acquired_by:<22} {result}")

print()
