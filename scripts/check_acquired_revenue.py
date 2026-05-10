import requests, sys
sys.stdout.reconfigure(encoding='utf-8')

BASE = "https://energy-tracker-production-39a1.up.railway.app"
TICKERS = ["HES","CIVI","MRO","ENLC","ALTM","MEG.TO","PKI.TO","VTLE","VRN","PFIE","ERF","NVA.TO","CLCO"]

print(f"{'Ticker':<10} {'Company':<36} {'Status':<12} {'Annual Rev':<14} {'FY':<8} {'Q Rev':<14} {'Q Label'}")
print("-" * 108)

for ticker in TICKERS:
    c = requests.get(f"{BASE}/companies/by-ticker/{ticker}", timeout=10).json()
    ann  = c.get("latest_revenue")
    fy   = c.get("latest_fiscal_year_label") or "null"
    qrev = c.get("latest_quarterly_revenue")
    ql   = c.get("latest_quarter_label") or "null"
    ann_s  = f"${ann/1e9:.3f}B"  if ann  else "null"
    qrev_s = f"${qrev/1e9:.3f}B" if qrev else "null"
    print(f"{ticker:<10} {c['name'][:34]:<36} {str(c['status']):<12} {ann_s:<14} {fy:<8} {qrev_s:<14} {ql}")
