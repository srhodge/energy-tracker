"""Diagnose yfinance revenue coverage for specific tickers — read-only, no DB updates."""
import sys, io, time
import yfinance as yf

TICKERS = [
    "BRY", "CNE.TO", "DRQ", "GIFI", "HUSA", "NR", "STR", "SOI", "SMLP",
    "TSE", "TNP", "VTNR", "CGG.PA", "AY", "AOI.TO", "COE.AX", "I3E.L",
    "TETY.ST", "DNMR", "ALKEM.PA", "RZ8G.F", "SRS.MI", "RRRP3.SA", "CVN.AX",
    "QGTS.QA",
]

def silent(fn):
    old = sys.stderr; sys.stderr = io.StringIO()
    try:    return fn(), None
    except Exception as e: return None, str(e)
    finally: sys.stderr = old

def fmt_rev(val):
    if val is None: return "None"
    try: return f"${float(val)/1e9:.3f}B"
    except: return str(val)

def has_rows(df, label):
    if df is None: return f"{label}=None"
    try:
        if df.empty: return f"{label}=empty"
        rev_rows = [r for r in df.index if "revenue" in str(r).lower()]
        return f"{label}=OK({len(df.columns)}cols, rev_rows={rev_rows[:2]})"
    except Exception as e:
        return f"{label}=ERR({e})"

print(f"\n{'Ticker':<12} {'longName':<32} {'totalRevenue':<14} {'revenueGrowth':<16} {'quarterly_financials':<40} {'financials':<40} Notes")
print("-" * 180)

for ticker in TICKERS:
    t = yf.Ticker(ticker)

    info, info_err = silent(lambda: t.info or {})
    info = info or {}

    name  = (info.get("longName") or info.get("shortName") or "")[:30]
    tr    = fmt_rev(info.get("totalRevenue"))
    rg    = str(info.get("revenueGrowth") or "None")
    note  = info_err or ("no name" if not name else "")

    qf, qf_err = silent(lambda: t.quarterly_financials)
    af, af_err = silent(lambda: t.financials)

    qf_str = has_rows(qf, "QF") if not qf_err else f"QF=ERR({qf_err[:30]})"
    af_str = has_rows(af, "AF") if not af_err else f"AF=ERR({af_err[:30]})"

    print(f"{ticker:<12} {name:<32} {tr:<14} {rg:<16} {qf_str:<40} {af_str:<40} {note}")
    time.sleep(0.5)

print()
