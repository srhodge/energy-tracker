"""
Market data poller — updates price and market cap for all pollable companies.

Runs on a schedule (see main.py) at:
  9:30, 11:30, 13:30, 15:30, 16:35 ET — Monday-Friday, non-NYSE-holiday

CLI usage (run from backend/):
    python -m app.services.market_poller
"""
import time
from datetime import date, datetime, timedelta

import yfinance as yf
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Company, Financial, CompanyStatus

# ---------------------------------------------------------------------------
# Timezone helpers
# ---------------------------------------------------------------------------

def _et_now() -> datetime:
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/New_York"))
    except Exception:
        return datetime.utcnow() - timedelta(hours=4)


def _et_today() -> date:
    return _et_now().date()


# ---------------------------------------------------------------------------
# NYSE holiday calendar 2025–2026
# ---------------------------------------------------------------------------

NYSE_HOLIDAYS: set[date] = {
    # 2025
    date(2025, 1, 1),   # New Year's Day
    date(2025, 1, 20),  # MLK Day
    date(2025, 2, 17),  # Presidents' Day
    date(2025, 4, 18),  # Good Friday
    date(2025, 5, 26),  # Memorial Day
    date(2025, 6, 19),  # Juneteenth
    date(2025, 7, 4),   # Independence Day
    date(2025, 9, 1),   # Labor Day
    date(2025, 11, 27), # Thanksgiving
    date(2025, 12, 25), # Christmas
    # 2026
    date(2026, 1, 1),   # New Year's Day
    date(2026, 1, 19),  # MLK Day
    date(2026, 2, 16),  # Presidents' Day
    date(2026, 4, 3),   # Good Friday
    date(2026, 5, 25),  # Memorial Day
    date(2026, 6, 19),  # Juneteenth
    date(2026, 7, 3),   # Independence Day (observed)
    date(2026, 9, 7),   # Labor Day
    date(2026, 11, 26), # Thanksgiving
    date(2026, 12, 25), # Christmas
}


def is_trading_day(d: date | None = None) -> bool:
    if d is None:
        d = _et_today()
    return d.weekday() < 5 and d not in NYSE_HOLIDAYS


# ---------------------------------------------------------------------------
# Exclusion / skip-flag classification
# ---------------------------------------------------------------------------

_SKIP_SUFFIXES = {".PK", ".OM", ".KW", ".QA", ".AE"}

_SKIP_STATUSES = (
    CompanyStatus.sanctioned,
    CompanyStatus.acquired,
    CompanyStatus.delisted,
)


def classify_skip_flags(db: Session) -> tuple[int, int]:
    """
    Set skip_market_poll=True for companies that can't be polled.
    Returns (marked_skip, marked_active).
    """
    companies = db.scalars(select(Company)).all()
    skip = active = 0

    for company in companies:
        ticker = (company.ticker or "").strip().upper()
        should_skip = (
            not ticker
            or ticker == "N/A"
            or any(ticker.endswith(s) for s in _SKIP_SUFFIXES)
            or company.status in _SKIP_STATUSES
        )
        if should_skip != company.skip_market_poll:
            company.skip_market_poll = should_skip
        if should_skip:
            skip += 1
        else:
            active += 1

    db.commit()
    return skip, active


# ---------------------------------------------------------------------------
# Currency detection — exchange suffix map
# ---------------------------------------------------------------------------

# Maps Yahoo Finance exchange suffixes to their native ISO currency codes.
# This is the primary currency source: reliable, instant, no API call required.
_EXCHANGE_CURRENCY: dict[str, str] = {
    ".JK":  "IDR",  # Indonesia (IDX)
    ".KS":  "KRW",  # Korea (KRX)
    ".KQ":  "KRW",  # Korea (KOSDAQ)
    ".T":   "JPY",  # Japan (TSE)
    ".OS":  "JPY",  # Japan (OSE)
    ".L":   "GBX",  # United Kingdom — yfinance quotes .L prices in pence, not pounds
    ".PA":  "EUR",  # France (Euronext Paris)
    ".AS":  "EUR",  # Netherlands (Euronext Amsterdam)
    ".BR":  "EUR",  # Belgium
    ".MI":  "EUR",  # Italy
    ".MC":  "EUR",  # Spain (BME)
    ".SW":  "CHF",  # Switzerland
    ".DE":  "EUR",  # Germany (XETRA)
    ".F":   "EUR",  # Germany (Frankfurt)
    ".HM":  "EUR",  # Germany (Hamburg)
    ".BE":  "EUR",  # Germany (Berlin)
    ".MU":  "EUR",  # Germany (Munich)
    ".TO":  "CAD",  # Canada (TSX)
    ".V":   "CAD",  # Canada (TSXV)
    ".CN":  "CAD",  # Canada (CSE)
    ".AX":  "AUD",  # Australia (ASX)
    ".HK":  "HKD",  # Hong Kong
    ".SS":  "CNY",  # China (Shanghai)
    ".SZ":  "CNY",  # China (Shenzhen)
    ".NS":  "INR",  # India (NSE)
    ".BO":  "INR",  # India (BSE)
    ".SA":  "BRL",  # Brazil (B3)
    ".MX":  "MXN",  # Mexico (BMV)
    ".SI":  "SGD",  # Singapore
    ".NZ":  "NZD",  # New Zealand
    ".KL":  "MYR",  # Malaysia (Bursa)
    ".BK":  "THB",  # Thailand (SET)
    ".TW":  "TWD",  # Taiwan (TWSE)
    ".TWO": "TWD",  # Taiwan (TPEx)
    ".TA":  "ILA",  # Israel (TASE) — quoted in agorot (1/100 shekel), not ILS
    ".AT":  "EUR",  # Greece (ATHEX)
    ".OL":  "NOK",  # Norway (Oslo Børs)
    ".ST":  "SEK",  # Sweden (Nasdaq Stockholm)
    ".HE":  "EUR",  # Finland (Nasdaq Helsinki)
    ".CO":  "DKK",  # Denmark (Nasdaq Copenhagen)
    ".IC":  "ISK",  # Iceland
    ".VN":  "VND",  # Vietnam (HOSE/HNX)
    ".BD":  "HUF",  # Hungary (Budapest Stock Exchange)
    ".PR":  "CZK",  # Czech Republic (Prague Stock Exchange)
    ".IS":  "TRY",  # Turkey (Borsa Istanbul)
    ".WA":  "PLN",  # Poland (Warsaw Stock Exchange)
    ".SR":  "SAR",  # Saudi Arabia (Tadawul)
    ".QA":  "QAR",  # Qatar (QSE) — added for completeness
    ".CA":  "CAD",  # Canada (alternate suffix)
    ".ZA":  "ZAR",  # South Africa (JSE)
    ".EG":  "EGP",  # Egypt (EGX)
    ".JO":  "ZAR",  # Johannesburg (JSE alt)
}

# yfinance fast_info.currency values that need normalisation to our internal codes.
# "GBp" is the most common: Yahoo returns lowercase 'p' for pence-denominated UK stocks.
_YFINANCE_CURRENCY_NORM: dict[str, str] = {
    "GBp": "GBX",  # British pence — same subunit as .L suffix
    "ILA": "ILA",  # Israeli agorot — fast_info already returns the right code
}


def _ticker_currency(ticker: str) -> str:
    """Return the native currency for a ticker based on its exchange suffix."""
    upper = ticker.upper()
    # Check longest suffixes first to avoid ".T" matching ".AT"
    for suffix in sorted(_EXCHANGE_CURRENCY, key=len, reverse=True):
        if upper.endswith(suffix.upper()):
            return _EXCHANGE_CURRENCY[suffix]
    return "USD"


# ---------------------------------------------------------------------------
# FX rate fetching
# ---------------------------------------------------------------------------

def _fetch_fx_rates(currencies: set[str]) -> dict[str, float]:
    """
    Fetch local-currency-per-USD rates for a set of non-USD currencies.
    Returns {CURRENCY: local_units_per_1_USD}.

    Uses yf.download("USDIDR=X", ...) — the same batch-download mechanism
    used for stock prices, which is far more reliable than fast_info.last_price
    for FX tickers.

    Special case: GBX (British pence) has no direct Yahoo pair — rate is
    derived from USDGBP=X × 100 (100 pence = 1 pound).
    """
    target = {c for c in currencies if c and c != "USD"}
    if not target:
        return {}

    # GBX (pence) and ILA (agorot) have no direct Yahoo FX pairs — substitute parent currencies
    needs_gbx = "GBX" in target
    needs_ila = "ILA" in target
    fetch_set = (target - {"GBX", "ILA"}) | ({"GBP"} if needs_gbx else set()) | ({"ILS"} if needs_ila else set())

    pairs = [f"USD{c}=X" for c in sorted(fetch_set)]
    rates: dict[str, float] = {}

    try:
        import pandas as pd
        raw = yf.download(pairs, period="5d", auto_adjust=True, progress=False, threads=False)

        if len(pairs) == 1:
            cur = pairs[0][3:6]  # "USDIDR=X" → "IDR"
            # .squeeze() collapses a single-column DataFrame to a Series
            series = raw["Close"].squeeze().dropna()
            if not series.empty:
                rates[cur] = float(series.iloc[-1])
        else:
            close = raw["Close"]
            for pair in pairs:
                cur = pair[3:6]
                try:
                    col = close[pair] if pair in close.columns else pd.Series(dtype=float)
                    series = col.squeeze().dropna()
                    if not series.empty:
                        rates[cur] = float(series.iloc[-1])
                except Exception:
                    pass

    except Exception as e:
        print(f"    [market-poll] FX batch download error: {e}", flush=True)

    # Derive subunit rates: 100 pence per pound, 100 agorot per shekel
    if needs_gbx and "GBP" in rates:
        rates["GBX"] = rates["GBP"] * 100
    if needs_ila and "ILS" in rates:
        rates["ILA"] = rates["ILS"] * 100

    missing = target - set(rates)
    if missing:
        print(f"    [market-poll] No FX rate for: {missing} — those tickers will be skipped", flush=True)

    return rates


def _revenue_currency(ticker_currency: str) -> str:
    """Financial statements are reported in major currency units, never subunits."""
    return {"GBX": "GBP", "ILA": "ILS"}.get(ticker_currency, ticker_currency)


def _fetch_revenue(
    ticker: str, currency: str, fx_rates: dict[str, float], t=None
) -> tuple[float | None, float | None, str | None, str | None]:
    """
    Fetch quarterly and annual total revenue from yfinance income statements.
    Returns (quarterly_usd, annual_usd, q_label, fy_label).
    currency should be the major currency (GBP not GBX, ILS not ILA).
    Pass t to reuse an existing yf.Ticker object.
    """
    try:
        if t is None:
            t = yf.Ticker(ticker)
        q_rev_usd = q_label = a_rev_usd = fy_label = None

        REV_NAMES = ("Total Revenue", "TotalRevenue", "totalRevenue")

        def _extract(df) -> tuple[float | None, str | None]:
            if df is None or df.empty:
                return None, None
            for name in REV_NAMES:
                if name in df.index:
                    series = df.loc[name].dropna()
                    if not series.empty:
                        period_date = series.index[0]
                        rev_val = float(series.iloc[0])
                        return rev_val, period_date
            return None, None

        # Quarterly
        try:
            qf = t.quarterly_income_stmt
        except Exception:
            qf = None
        if qf is None or (hasattr(qf, "empty") and qf.empty):
            try:
                qf = t.quarterly_financials
            except Exception:
                qf = None

        q_rev, q_date = _extract(qf)
        if q_rev is not None and q_date is not None:
            q_num = (q_date.month - 1) // 3 + 1
            q_label = f"Q{q_num} {q_date.year}"
            q_rev_usd = _to_usd(q_rev, currency, fx_rates) if currency != "USD" else q_rev

        # Annual
        try:
            af = t.income_stmt
        except Exception:
            af = None
        if af is None or (hasattr(af, "empty") and af.empty):
            try:
                af = t.financials
            except Exception:
                af = None

        a_rev, a_date = _extract(af)
        if a_rev is not None and a_date is not None:
            fy_label = f"FY{a_date.year}"
            a_rev_usd = _to_usd(a_rev, currency, fx_rates) if currency != "USD" else a_rev

        return q_rev_usd, a_rev_usd, q_label, fy_label
    except Exception:
        return None, None, None, None


def _to_usd(value: float | None, currency: str, fx_rates: dict[str, float]) -> float | None:
    """
    Convert value from native currency to USD.
    fx_rates[currency] = local_units_per_1_USD, so we divide.
    Returns None if the rate is unavailable (don't store bad data).
    """
    if value is None:
        return None
    if currency == "USD":
        return value
    rate = fx_rates.get(currency)
    if not rate:
        return None
    return value / rate


# ---------------------------------------------------------------------------
# Staleness check
# ---------------------------------------------------------------------------

def is_poll_stale(db: Session) -> bool:
    """Return True if we haven't polled today (ET) yet."""
    today = _et_today()
    start_of_today = datetime.combine(today, datetime.min.time())
    count = db.scalar(
        select(func.count(Financial.id)).where(
            Financial.last_market_update >= start_of_today
        )
    )
    return (count or 0) == 0


def has_missing_revenue(db: Session) -> bool:
    """Return True if any pollable company has never had revenue data fetched."""
    pollable_ids = db.scalars(
        select(Company.id).where(Company.skip_market_poll == False)
    ).all()
    if not pollable_ids:
        return False
    filled = db.scalar(
        select(func.count(Financial.company_id.distinct())).where(
            Financial.company_id.in_(pollable_ids),
            Financial.revenue_annual_usd.isnot(None),
        )
    )
    return (filled or 0) < len(pollable_ids)


# Values seeded by migration from energy_segment — not yet from yfinance
_ENERGY_SEGMENT_VALUES: frozenset[str] = frozenset({
    "Integrated Gas", "Onshore", "Offshore", "Combustion Energy",
    "Midstream Infrastructure", "Petrochemicals", "Chemicals",
    "Refined Fuels", "Specialty Chemicals", "Fuel Transport",
    "Bulk Minerals", "Agriculture Plants", "Resource Infrastructure",
    "Metals", "Low Carbon Hydrogen", "Renewable Energy", "Energy Storage",
    "Nuclear SMR", "Power to X", "Low Carbon Fuels", "Direct Air Capture",
    "Ammonia/Methanol", "Plastics Recovery", "Energy Transition Materials",
    "Battery Materials", "Water Recycling",
})


def needs_industry_population(db: Session) -> bool:
    """Return True if any pollable company has a null or migration-seeded industry value."""
    pollable_ids = db.scalars(
        select(Company.id).where(Company.skip_market_poll == False)
    ).all()
    if not pollable_ids:
        return False
    count = db.scalar(
        select(func.count(Company.id)).where(
            Company.id.in_(pollable_ids),
            or_(
                Company.industry.is_(None),
                Company.industry.in_(_ENERGY_SEGMENT_VALUES),
            ),
        )
    )
    return (count or 0) > 0


def needs_initial_fundamentals(db: Session) -> bool:
    """Return True if more than half of pollable companies lack quarterly revenue data."""
    pollable_ids = db.scalars(
        select(Company.id).where(Company.skip_market_poll == False)
    ).all()
    if not pollable_ids:
        return False
    filled = db.scalar(
        select(func.count(Financial.company_id.distinct())).where(
            Financial.company_id.in_(pollable_ids),
            Financial.revenue_quarterly_usd.isnot(None),
        )
    )
    return (filled or 0) < len(pollable_ids) // 2


# ---------------------------------------------------------------------------
# Core poll logic
# ---------------------------------------------------------------------------

def _fetch_batch(tickers: list[str]) -> dict[str, tuple[float | None, float | None, str]]:
    """
    Download close price and market cap for a batch of tickers.
    Returns {TICKER: (price, market_cap, currency)} — all in the ticker's native currency.

    Currency is derived from the ticker's exchange suffix (reliable, no API call).
    market_cap comes from fast_info and is also in the native currency.
    """
    if not tickers:
        return {}

    results: dict[str, tuple[float | None, float | None, str]] = {}

    try:
        import pandas as pd
        raw = yf.download(tickers, period="1d", auto_adjust=True, progress=False, threads=True)

        if len(tickers) == 1:
            t = tickers[0]
            try:
                close_series = raw["Close"].squeeze().dropna()
                price = float(close_series.iloc[-1]) if not close_series.empty else None
            except Exception:
                price = None
            results[t] = (price, None, _ticker_currency(t))
        else:
            try:
                close_df = raw["Close"]
            except Exception:
                close_df = pd.DataFrame()
            for t in tickers:
                try:
                    series = close_df[t].dropna() if t in close_df.columns else pd.Series()
                    price = float(series.iloc[-1]) if not series.empty else None
                except Exception:
                    price = None
                results[t] = (price, None, _ticker_currency(t))
    except Exception as e:
        print(f"    [market-poll] Batch download error: {e}", flush=True)
        for t in tickers:
            results[t] = (None, None, _ticker_currency(t))

    # Fetch market cap and confirm currency via fast_info.
    # fast_info.currency is the primary source; suffix map is the fallback.
    # Subunit currencies (GBp → GBX, ILA) are normalised via _YFINANCE_CURRENCY_NORM.
    for t in list(results.keys()):
        if results[t][0] is not None:
            price, _, suffix_currency = results[t]
            mcap = None
            currency = suffix_currency  # start with suffix map value
            try:
                fi = yf.Ticker(t).fast_info
                mcap_raw = getattr(fi, "market_cap", None)
                if mcap_raw:
                    mcap = float(mcap_raw)
                fi_cur = (getattr(fi, "currency", None) or "").strip()
                if fi_cur:
                    # Normalise known variants (GBp → GBX, etc.)
                    fi_cur = _YFINANCE_CURRENCY_NORM.get(fi_cur, fi_cur.upper())
                    # Trust fast_info when it returns a non-USD currency,
                    # or when the suffix map defaulted to USD (unknown exchange).
                    if fi_cur != "USD" or suffix_currency == "USD":
                        currency = fi_cur
            except Exception:
                pass
            results[t] = (price, mcap, currency)

    return results


def poll_once(db: Session, batch_size: int = 50, company_ids: set[int] | None = None) -> dict:
    """
    Poll all non-skipped companies and upsert today's Financial record.
    If company_ids is given, only those companies are polled.
    Returns summary dict.
    """
    today = _et_today()
    now = datetime.utcnow()
    t0 = time.monotonic()

    q = select(Company).where(Company.skip_market_poll == False)
    pollable = db.scalars(q).all()
    if company_ids is not None:
        pollable = [c for c in pollable if c.id in company_ids]

    total = db.scalar(select(func.count(Company.id)))
    skipped = (total or 0) - len(pollable)

    print(
        f"[market-poll] Polling {len(pollable)} of {total} companies "
        f"({skipped} skipped — sanctioned/acquired/no coverage)",
        flush=True,
    )

    # Fetch all exchange rates once per poll run — fresh at every scheduled execution,
    # reused across batches so we don't re-request the same GBP/USD rate 10 times.
    all_currencies = {_ticker_currency(c.ticker or "") for c in pollable} - {"USD"}
    fx_rates: dict[str, float] = _fetch_fx_rates(all_currencies) if all_currencies else {}
    if fx_rates:
        # Display as USD-per-local-unit (inverted), parent currencies only
        display = {
            cur: round(1.0 / rate, 6)
            for cur, rate in fx_rates.items()
            if cur not in ("GBX", "ILA") and rate > 0
        }
        rate_str = ", ".join(f"{c}={v}" for c, v in sorted(display.items()))
        print(f"[market-poll] Exchange rates fetched: {rate_str}", flush=True)

    existing_today: dict[int, Financial] = {
        f.company_id: f
        for f in db.scalars(
            select(Financial).where(Financial.snapshot_date == today)
        ).all()
    }

    # Latest revenue per company (carry-forward: avoids re-fetching every day)
    latest_rev_sq = (
        select(Financial.company_id, func.max(Financial.snapshot_date).label("max_date"))
        .where(Financial.revenue_annual_usd.isnot(None))
        .group_by(Financial.company_id)
        .subquery()
    )
    prev_revenue: dict[int, tuple] = {
        row.company_id: (
            row.revenue_quarterly_usd, row.revenue_annual_usd,
            row.revenue_quarter_label, row.revenue_fiscal_year_label,
        )
        for row in db.execute(
            select(
                Financial.company_id,
                Financial.revenue_quarterly_usd,
                Financial.revenue_annual_usd,
                Financial.revenue_quarter_label,
                Financial.revenue_fiscal_year_label,
            ).join(latest_rev_sq, and_(
                Financial.company_id == latest_rev_sq.c.company_id,
                Financial.snapshot_date == latest_rev_sq.c.max_date,
            ))
        ).all()
    }

    updated = failed = 0

    for i in range(0, len(pollable), batch_size):
        batch = pollable[i : i + batch_size]
        tickers = [c.ticker.upper() for c in batch if c.ticker]
        if not tickers:
            continue

        batch_results = _fetch_batch(tickers)

        # Dynamically fetch rates for any currencies discovered via fast_info
        # that weren't covered by the upfront suffix-map scan.
        new_currencies = (
            {cur for _, _, cur in batch_results.values() if cur != "USD"} - set(fx_rates)
        )
        if new_currencies:
            new_rates = _fetch_fx_rates(new_currencies)
            fx_rates.update(new_rates)
            if new_rates:
                extra = {c: round(1.0 / r, 6) for c, r in new_rates.items() if r > 0 and c not in ("GBX", "ILA")}
                print(f"[market-poll] Additional FX rates: {', '.join(f'{c}={v}' for c, v in sorted(extra.items()))}", flush=True)

        for company in batch:
            if not company.ticker:
                continue
            price_local, mcap_local, currency = batch_results.get(
                company.ticker.upper(), (None, None, "USD")
            )
            price = _to_usd(price_local, currency, fx_rates)
            market_cap = _to_usd(mcap_local, currency, fx_rates)

            if price is None:
                failed += 1
                continue

            # Revenue: carry forward from previous record (fundamentals poll updates separately)
            prev = prev_revenue.get(company.id)

            if company.id in existing_today:
                rec = existing_today[company.id]
                rec.price_usd = price
                rec.market_cap_usd = market_cap
                rec.last_market_update = now
            else:
                rec = Financial(
                    company_id=company.id,
                    price_usd=price,
                    market_cap_usd=market_cap,
                    snapshot_date=today,
                    last_market_update=now,
                    revenue_quarterly_usd=prev[0] if prev else None,
                    revenue_annual_usd=prev[1] if prev else None,
                    revenue_quarter_label=prev[2] if prev else None,
                    revenue_fiscal_year_label=prev[3] if prev else None,
                )
                db.add(rec)
                existing_today[company.id] = rec

            updated += 1

        db.commit()
        time.sleep(1)

    elapsed = round(time.monotonic() - t0)
    print(
        f"[market-poll] Done — updated {updated} tickers in {elapsed}s "
        f"({failed} returned no price data)",
        flush=True,
    )
    return {"updated": updated, "failed": failed, "skipped": skipped, "date": str(today)}


def poll_non_usd_companies(db: Session) -> dict:
    """
    Re-poll only companies whose tickers are listed on non-USD exchanges.
    Used on startup to correct any data stored before the currency fix.
    """
    pollable = db.scalars(
        select(Company).where(Company.skip_market_poll == False)
    ).all()
    non_usd_ids = {c.id for c in pollable if _ticker_currency(c.ticker or "") != "USD"}

    if not non_usd_ids:
        print("[market-poll] No non-USD companies to re-poll.", flush=True)
        return {}

    print(f"[market-poll] Re-polling {len(non_usd_ids)} non-USD companies for currency correction...", flush=True)
    return poll_once(db, company_ids=non_usd_ids)


# ---------------------------------------------------------------------------
# Fundamentals poller (revenue — runs weekly, Saturday 8am ET)
# ---------------------------------------------------------------------------

def _is_stale(label: str | None) -> bool:
    """Return True if a quarter label is null or older than 4 months."""
    if not label:
        return True
    try:
        parts = label.split()
        if len(parts) != 2 or not parts[0].startswith("Q"):
            return True
        q_num = int(parts[0][1:])
        year = int(parts[1])
        q_end_month = q_num * 3
        cutoff_month = q_end_month + 4
        cutoff_year = year + (cutoff_month - 1) // 12
        cutoff_month = (cutoff_month - 1) % 12 + 1
        return date.today() >= date(cutoff_year, cutoff_month, 1)
    except Exception:
        return True


def poll_fundamentals(db: Session) -> dict:
    """
    Fetch/refresh quarterly and annual revenue for all pollable companies.
    Only re-fetches companies whose revenue_quarter_label is null or >4 months old.
    """
    pollable = db.scalars(
        select(Company).where(Company.skip_market_poll == False)
    ).all()

    if not pollable:
        print("[fundamentals] No pollable companies.", flush=True)
        return {}

    # Fetch FX rates upfront for all non-USD currencies
    all_currencies = {_ticker_currency(c.ticker or "") for c in pollable} - {"USD"}
    fx_rates: dict[str, float] = _fetch_fx_rates(all_currencies) if all_currencies else {}

    # Latest Financial record per company
    latest_sq = (
        select(Financial.company_id, func.max(Financial.snapshot_date).label("max_date"))
        .group_by(Financial.company_id)
        .subquery()
    )
    latest_records: dict[int, Financial] = {
        f.company_id: f
        for f in db.scalars(
            select(Financial).join(latest_sq, and_(
                Financial.company_id == latest_sq.c.company_id,
                Financial.snapshot_date == latest_sq.c.max_date,
            ))
        ).all()
    }

    today = _et_today()
    rev_updated = rev_failed = ind_updated = skipped = 0

    for i, company in enumerate(pollable):
        if not company.ticker:
            skipped += 1
            continue

        rec = latest_records.get(company.id)
        q_label = rec.revenue_quarter_label if rec else None
        needs_revenue = _is_stale(q_label)
        needs_industry = (
            company.industry is None or company.industry in _ENERGY_SEGMENT_VALUES
        )

        if not needs_revenue and not needs_industry:
            skipped += 1
            continue

        ticker = company.ticker.upper()
        currency = _ticker_currency(ticker)
        rev_currency = _revenue_currency(currency)

        try:
            t = yf.Ticker(ticker)

            if needs_industry:
                try:
                    info = t.info or {}
                    ind = info.get("industry") or None
                    if ind:
                        company.industry = ind
                        ind_updated += 1
                except Exception:
                    pass

            if needs_revenue:
                if rev_currency != "USD" and rev_currency not in fx_rates:
                    extra = _fetch_fx_rates({rev_currency})
                    fx_rates.update(extra)

                q_rev, a_rev, q_lbl, fy_lbl = _fetch_revenue(ticker, rev_currency, fx_rates, t)

                if q_rev is not None or a_rev is not None:
                    if rec is None:
                        rec = Financial(
                            company_id=company.id,
                            snapshot_date=today,
                            revenue_quarterly_usd=q_rev,
                            revenue_annual_usd=a_rev,
                            revenue_quarter_label=q_lbl,
                            revenue_fiscal_year_label=fy_lbl,
                        )
                        db.add(rec)
                        latest_records[company.id] = rec
                    else:
                        rec.revenue_quarterly_usd = q_rev
                        rec.revenue_annual_usd = a_rev
                        rec.revenue_quarter_label = q_lbl
                        rec.revenue_fiscal_year_label = fy_lbl
                    rev_updated += 1
                else:
                    rev_failed += 1
        except Exception:
            pass

        if (i + 1) % 10 == 0:
            print(f"[fundamentals] {i + 1}/{len(pollable)} processed ...", flush=True)
            db.commit()

        time.sleep(0.4)

    db.commit()
    print(
        f"[fundamentals] Done — industry: {ind_updated} updated; "
        f"revenue: {rev_updated} updated, {rev_failed} failed; {skipped} skipped",
        flush=True,
    )
    return {"ind_updated": ind_updated, "rev_updated": rev_updated, "rev_failed": rev_failed, "skipped": skipped}


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    with SessionLocal() as db:
        skip, active = classify_skip_flags(db)
        print(f"[market-poll] Skip flags: {skip} skipped, {active} pollable", flush=True)
        poll_once(db)


if __name__ == "__main__":
    main()
