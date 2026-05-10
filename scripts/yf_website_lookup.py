"""
Lookup websites from yfinance for specific tickers and update via API.
"""
import sys, io, time
import requests
import yfinance as yf

BASE = "https://energy-tracker-production-39a1.up.railway.app"

TICKERS = [
    "ERF", "COE.AX", "GIFI", "HUSA", "NR", "NVA.TO", "PHX",
    "PAA", "RZ8G.F", "SRS.MI", "TSE", "TNP", "VTNR", "WEII.V",
    "DNMR", "CLCO", "I3E.L", "BROG",
]

def get_yf_info(ticker):
    old_err = sys.stderr
    sys.stderr = io.StringIO()
    try:
        info = yf.Ticker(ticker).info or {}
        return info
    except Exception:
        return {}
    finally:
        sys.stderr = old_err

def lookup_company(ticker):
    r = requests.get(f"{BASE}/companies/by-ticker/{ticker}", timeout=10)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()

def update_website(company_id, website):
    r = requests.put(f"{BASE}/companies/{company_id}", json={"website": website}, timeout=10)
    return r.ok

print(f"\nFetching yfinance data for {len(TICKERS)} tickers...\n")

results = []
for ticker in TICKERS:
    info = get_yf_info(ticker)
    yf_name = info.get("longName") or info.get("shortName") or ""
    yf_website = (info.get("website") or "").rstrip("/") or None

    company = lookup_company(ticker)
    db_name = company["name"] if company else "NOT IN DB"

    if not info or not yf_name:
        results.append((ticker, db_name, "—", "no yfinance data", "skipped"))
        print(f"  {ticker}: no yfinance data")
        time.sleep(0.3)
        continue

    if not yf_website:
        results.append((ticker, yf_name, "—", "no website in yfinance", "skipped"))
        print(f"  {ticker} ({yf_name}): no website field")
        time.sleep(0.3)
        continue

    if not company:
        results.append((ticker, yf_name, yf_website, "company not in DB", "skipped"))
        print(f"  {ticker} ({yf_name}): {yf_website} — NOT IN DB")
        time.sleep(0.3)
        continue

    ok = update_website(company["id"], yf_website)
    result = "updated" if ok else "FAILED"
    results.append((ticker, yf_name, yf_website, result, result))
    print(f"  {ticker} ({yf_name}): {yf_website} -> {result}")
    time.sleep(0.3)

print("\n" + "=" * 100)
print(f"{'Ticker':<12} {'yfinance Name':<35} {'Website':<40} {'Result'}")
print("-" * 100)
for ticker, name, website, result, _ in results:
    print(f"{ticker:<12} {name[:33]:<35} {website[:38]:<40} {result}")
print()

updated = sum(1 for *_, r in results if r == "updated")
skipped = len(results) - updated
print(f"Updated: {updated}  |  Skipped: {skipped}")
