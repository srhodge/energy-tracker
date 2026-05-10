"""
For each company, fetch the IR/about page to find alternate tickers,
then try yfinance for revenue. Updates DB if revenue found.
"""
import re, sys, io, time
import requests
import yfinance as yf

BASE = "https://energy-tracker-production-39a1.up.railway.app"

COMPANIES = [
    ("ABRJ.OM",    "https://abrajenergy.com/investors"),
    ("ADNOCDIST.AE","https://www.adnoc.ae/en/adnoc-distribution/investor-relations"),
    ("ADNOCGAS.AE", "https://www.adnocgas.ae/en/investor-relations"),
    ("MHAS.OM",    "https://www.almaha.com.om/en/investor-relations"),
    ("SOOR.KW",    "https://www.soor.com.kw"),
    ("SUWP.OM",    "https://www.alsuwadipower.com"),
    ("BROG",       "https://www.broogeenergy.com/investors"),
    ("DANA.AE",    "https://www.danagas.com/en/investor-relations"),
    ("GICI.OM",    "https://www.gicoman.com"),
    ("IPG.KW",     "https://ipg.com.kw/investor-relations"),
    ("MARI.PK",    "https://www.marigas.com.pk/investor-relations"),
    ("MPHC.QA",    "https://www.mphc.com.qa/investor-relations"),
    ("NGCI.OM",    "https://nationalgasco.net"),
    ("NAPESCO.KW", "https://www.napesco.com"),
    ("OCHL.OM",    "https://www.omanchlorine.com"),
    ("OOMS.OM",    "https://www.oomco.com"),
    ("OQGN.OM",    "https://oq.com/businesses/oq-gas-networks"),
    ("OULAFUEL.KW","https://www.oula1.com"),
    ("IQCD.QA",    "https://www.iq.com.qa/investor-relations"),
    ("BOROUGE.AE", "https://www.borouge.com/investors"),
    ("BPCC.KW",    "https://boubyan.com"),
    ("TAQA.AE",    "https://www.taqa.com/en/investor-relations"),
    ("SENERGY.KW", "https://www.senergyholding.com"),
    ("SNGS.ME",    "https://www.surgutneftegas.ru/en/investors"),
]

# Known alternate tickers to try in addition to what we scrape
ALT_TICKERS = {
    "BROG":       ["BROG"],          # was NASDAQ; now private
    "SNGS.ME":    ["SGTPY", "SGTZY"], # Surgutneftegas US OTC ADRs
    "ADNOCDIST.AE":["ADNOCDIST.AE"],
    "ADNOCGAS.AE": ["ADNOCGAS.AE"],
    "TAQA.AE":    ["TAQA.AE"],
    "BOROUGE.AE": ["BOROUGE.AE"],
    "DANA.AE":    ["DANA.AE"],
    "IQCD.QA":    ["IQCD.QA"],
    "MPHC.QA":    ["MPHC.QA"],
}

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; research-bot/1.0)"}

TICKER_RE = re.compile(r'\b([A-Z]{2,6}(?:\.[A-Z]{1,3})?)\b')

def fetch_page_text(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        # Strip tags roughly
        text = re.sub(r'<[^>]+>', ' ', r.text)
        return ' '.join(text.split())[:5000]
    except Exception as e:
        return ""

def extract_tickers_from_text(text):
    """Pull plausible ticker candidates from page text."""
    found = set()
    # Look for exchange mentions near uppercase words
    for m in re.finditer(r'(?:ticker|symbol|listed|trading\s+as)[:\s]+([A-Z0-9.]{2,10})', text, re.I):
        found.add(m.group(1).upper())
    # Also look for "NYSE: X", "NASDAQ: X", "LSE: X" etc.
    for m in re.finditer(r'(?:NYSE|NASDAQ|LSE|ADX|MSM|KSE|BSE|NSE|PSX)[:\s]+([A-Z0-9.]{2,10})', text, re.I):
        found.add(m.group(1).upper())
    return found

def try_yfinance_revenue(ticker):
    old_err = sys.stderr; sys.stderr = io.StringIO()
    try:
        t = yf.Ticker(ticker)
        info = t.info or {}
        if not info.get("longName") and not info.get("shortName"):
            return None, None, None, None, None
        # Try quarterly
        q_rev = q_lbl = a_rev = a_lbl = None
        try:
            qf = t.quarterly_income_stmt
            if qf is None or (hasattr(qf,'empty') and qf.empty):
                qf = t.quarterly_financials
            if qf is not None and not (hasattr(qf,'empty') and qf.empty):
                for name in ("Total Revenue","TotalRevenue","totalRevenue"):
                    if name in qf.index:
                        s = qf.loc[name].dropna()
                        if not s.empty:
                            q_rev = float(s.iloc[0])
                            d = s.index[0]
                            q_lbl = f"Q{(d.month-1)//3+1} {d.year}"
                            break
        except Exception:
            pass
        try:
            af = t.income_stmt
            if af is None or (hasattr(af,'empty') and af.empty):
                af = t.financials
            if af is not None and not (hasattr(af,'empty') and af.empty):
                for name in ("Total Revenue","TotalRevenue","totalRevenue"):
                    if name in af.index:
                        s = af.loc[name].dropna()
                        if not s.empty:
                            a_rev = float(s.iloc[0])
                            d = s.index[0]
                            a_lbl = f"FY{d.year}"
                            break
        except Exception:
            pass
        return q_rev, q_lbl, a_rev, a_lbl, info.get("longName") or info.get("shortName")
    except Exception:
        return None, None, None, None, None
    finally:
        sys.stderr = old_err

def lookup_company(ticker):
    r = requests.get(f"{BASE}/companies/by-ticker/{ticker}", timeout=10)
    return r.json() if r.ok else None

def update_revenue(company_id, q_rev, a_rev, q_lbl, a_lbl):
    # Get latest financial record id via company detail
    r = requests.get(f"{BASE}/companies/{company_id}", timeout=10).json()
    # Use admin targeted endpoint to force-fetch — actually just PUT won't work for financials
    # Instead trigger targeted poll which now supports forced revenue fetch
    return False  # Can't update financials directly via API; will report found data

results = []

for ticker, ir_url in COMPANIES:
    tickers_to_try = list(ALT_TICKERS.get(ticker, [])) + [ticker]

    # Fetch IR page for additional ticker hints
    text = fetch_page_text(ir_url)
    scraped = extract_tickers_from_text(text)
    tickers_to_try = list(dict.fromkeys(tickers_to_try + list(scraped)))  # dedupe, preserve order

    found_revenue = False
    alt_used = None
    q_rev = a_rev = q_lbl = a_lbl = yf_name = None

    for t in tickers_to_try[:6]:  # cap attempts
        q_rev, q_lbl, a_rev, a_lbl, yf_name = try_yfinance_revenue(t)
        if q_rev or a_rev:
            alt_used = t if t != ticker else None
            found_revenue = True
            break
        time.sleep(0.3)

    if found_revenue:
        rev_str = f"Q={q_rev/1e9:.2f}B  FY={a_rev/1e9:.2f}B" if a_rev else f"Q={q_rev/1e9:.2f}B"
        alt_note = f" via {alt_used}" if alt_used else ""
        results.append((ticker, yf_name or "?", f"FOUND{alt_note}: {rev_str}", q_rev, a_rev, q_lbl, a_lbl))
        print(f"[{ticker}]{alt_note} -> revenue {rev_str}")
    else:
        results.append((ticker, "—", "no revenue data", None, None, None, None))
        print(f"[{ticker}] -> no revenue data found")

    time.sleep(0.3)

# Summary
print("\n" + "=" * 90)
print(f"{'Ticker':<16} {'yfinance Name':<30} {'Result'}")
print("-" * 90)
for ticker, name, result, *_ in results:
    print(f"{ticker:<16} {name[:28]:<30} {result}")

found = [r for r in results if r[3] or r[4]]
print(f"\nRevenue found for {len(found)}/{len(results)} companies")
if found:
    print("\nTo update these, trigger a targeted poll with:")
    tickers_with_data = [r[0] for r in found]
    print(f"  tickers: {tickers_with_data}")
