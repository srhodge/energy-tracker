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
from sqlalchemy import select, func, and_
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
    ".L":   "GBP",  # United Kingdom
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
    ".TA":  "ILS",  # Israel (TASE)
    ".AT":  "EUR",  # Greece (ATHEX)
    ".OL":  "NOK",  # Norway (Oslo Børs)
    ".ST":  "SEK",  # Sweden (Nasdaq Stockholm)
    ".HE":  "EUR",  # Finland (Nasdaq Helsinki)
    ".CO":  "DKK",  # Denmark (Nasdaq Copenhagen)
    ".IC":  "ISK",  # Iceland
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
    """
    target = {c for c in currencies if c and c != "USD"}
    if not target:
        return {}

    pairs = [f"USD{c}=X" for c in sorted(target)]
    rates: dict[str, float] = {}

    try:
        import pandas as pd
        raw = yf.download(pairs, period="5d", auto_adjust=True, progress=False, threads=False)

        if len(pairs) == 1:
            cur = pairs[0][3:6]  # "USDIDR=X" → "IDR"
            series = raw["Close"].dropna()
            if not series.empty:
                rates[cur] = float(series.iloc[-1])
        else:
            close = raw["Close"]
            for pair in pairs:
                cur = pair[3:6]
                try:
                    col = close[pair] if pair in close.columns else pd.Series(dtype=float)
                    series = col.dropna()
                    if not series.empty:
                        rates[cur] = float(series.iloc[-1])
                except Exception:
                    pass

    except Exception as e:
        print(f"    [market-poll] FX batch download error: {e}", flush=True)

    missing = target - set(rates)
    if missing:
        print(f"    [market-poll] No FX rate for: {missing} — those tickers will be skipped", flush=True)

    return rates


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
                close_series = raw["Close"].dropna()
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

    # Fetch market cap individually — fast_info.market_cap is in the native currency
    for t in list(results.keys()):
        if results[t][0] is not None:
            try:
                mcap = getattr(yf.Ticker(t).fast_info, "market_cap", None)
                price, _, currency = results[t]
                results[t] = (price, float(mcap) if mcap else None, currency)
            except Exception:
                pass

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

    existing_today: dict[int, Financial] = {
        f.company_id: f
        for f in db.scalars(
            select(Financial).where(Financial.snapshot_date == today)
        ).all()
    }

    updated = failed = 0

    for i in range(0, len(pollable), batch_size):
        batch = pollable[i : i + batch_size]
        tickers = [c.ticker.upper() for c in batch if c.ticker]
        if not tickers:
            continue

        batch_results = _fetch_batch(tickers)

        # Collect unique non-USD currencies in this batch and fetch rates once
        currencies = {cur for _, _, cur in batch_results.values() if cur != "USD"}
        fx_rates = _fetch_fx_rates(currencies) if currencies else {}
        if fx_rates:
            print(
                f"    [market-poll] FX rates: "
                f"{', '.join(f'{c}=>{r:.4f} local/USD' for c, r in sorted(fx_rates.items()))}",
                flush=True,
            )

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
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    with SessionLocal() as db:
        skip, active = classify_skip_flags(db)
        print(f"[market-poll] Skip flags: {skip} skipped, {active} pollable", flush=True)
        poll_once(db)


if __name__ == "__main__":
    main()
