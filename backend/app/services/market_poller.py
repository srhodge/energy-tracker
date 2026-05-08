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
        # Fallback: UTC-4 (EDT) — close enough for market-hours gate
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
    date(2026, 7, 3),   # Independence Day (observed; July 4 falls on Saturday)
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

# Exchange suffixes with no Yahoo Finance coverage
_SKIP_SUFFIXES = {".PK", ".OM", ".KW", ".QA", ".AE"}

# Statuses for companies that will never have live price data
_SKIP_STATUSES = (
    CompanyStatus.sanctioned,
    CompanyStatus.acquired,
    CompanyStatus.delisted,
)


def classify_skip_flags(db: Session) -> tuple[int, int]:
    """
    Set skip_market_poll=True for companies that can't be polled,
    and False for companies that can. Idempotent — safe to re-run.
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
# Staleness check
# ---------------------------------------------------------------------------

_MAX_PLAUSIBLE_MARKET_CAP_USD = 20e12  # $20T — no company legitimately exceeds this


def is_poll_stale(db: Session) -> bool:
    """
    Return True if we haven't polled today (ET) yet, OR if today's data
    contains obviously wrong values (non-USD currency stored without conversion).
    """
    today = _et_today()
    start_of_today = datetime.combine(today, datetime.min.time())
    count = db.scalar(
        select(func.count(Financial.id)).where(
            Financial.last_market_update >= start_of_today
        )
    )
    if (count or 0) == 0:
        return True
    # Detect bad data: any market_cap above $20T means a non-USD currency was stored raw
    bad = db.scalar(
        select(func.count(Financial.id)).where(
            Financial.market_cap_usd > _MAX_PLAUSIBLE_MARKET_CAP_USD
        )
    )
    if (bad or 0) > 0:
        print(f"[market-poll] {bad} records with implausible market cap — forcing re-poll", flush=True)
        return True
    return False


# ---------------------------------------------------------------------------
# Currency conversion helpers
# ---------------------------------------------------------------------------

def _fetch_fx_rates(currencies: set[str]) -> dict[str, float]:
    """
    Fetch USD conversion rates for a set of non-USD currency codes.
    Returns {CURRENCY_CODE: usd_per_one_unit}.
    Uses {CUR}USD=X pairs; falls back to 1/USD{CUR}=X if the direct pair fails.
    """
    rates: dict[str, float] = {}
    for cur in currencies:
        if not cur or cur == "USD":
            continue
        try:
            direct = getattr(yf.Ticker(f"{cur}USD=X").fast_info, "last_price", None)
            if direct and float(direct) > 0:
                rates[cur] = float(direct)
                continue
            inverse = getattr(yf.Ticker(f"USD{cur}=X").fast_info, "last_price", None)
            if inverse and float(inverse) > 0:
                rates[cur] = 1.0 / float(inverse)
        except Exception:
            pass
    return rates


def _to_usd(value: float | None, currency: str, fx_rates: dict[str, float]) -> float | None:
    """Convert a value from its native currency to USD. Returns None if rate is unknown."""
    if value is None:
        return None
    if currency == "USD":
        return value
    rate = fx_rates.get(currency)
    if rate is None:
        return None
    return value * rate


def _fetch_batch(tickers: list[str]) -> dict[str, tuple[float | None, float | None, str]]:
    """
    Download close price and market cap for a batch of tickers.
    Returns {TICKER: (price, market_cap, currency)} — all values in the ticker's native currency.
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
            results[t] = (price, None, "USD")
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
                results[t] = (price, None, "USD")
    except Exception as e:
        print(f"    [market-poll] Batch download error: {e}", flush=True)
        for t in tickers:
            results[t] = (None, None, "USD")

    # Fetch market cap and currency individually via fast_info
    for t in list(results.keys()):
        price = results[t][0]
        if price is not None:
            try:
                fi = yf.Ticker(t).fast_info
                mcap = getattr(fi, "market_cap", None)
                currency = (getattr(fi, "currency", None) or "USD").upper().strip()
                results[t] = (price, float(mcap) if mcap else None, currency)
            except Exception:
                pass  # leave currency as "USD" placeholder — will fail conversion safely

    return results


def poll_once(db: Session, batch_size: int = 50) -> dict:
    """
    Poll all non-skipped companies and upsert today's Financial record.
    Returns summary dict.
    """
    today = _et_today()
    now = datetime.utcnow()
    t0 = time.monotonic()

    pollable = db.scalars(
        select(Company).where(Company.skip_market_poll == False)
    ).all()
    total = db.scalar(select(func.count(Company.id)))
    skipped = (total or 0) - len(pollable)

    print(
        f"[market-poll] Polling {len(pollable)} of {total} companies "
        f"({skipped} skipped — sanctioned/acquired/no coverage)",
        flush=True,
    )

    # Pre-load today's Financial records to avoid N+1 upserts
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

        # Convert non-USD prices to USD
        currencies = {cur for _, _, cur in batch_results.values() if cur != "USD"}
        fx_rates = _fetch_fx_rates(currencies) if currencies else {}
        if fx_rates:
            print(f"    [market-poll] FX: {', '.join(f'{c}→USD @{r:.6f}' for c, r in fx_rates.items())}", flush=True)
        missing_rates = currencies - set(fx_rates)
        if missing_rates:
            print(f"    [market-poll] No FX rate for: {missing_rates} — those tickers will be skipped", flush=True)

        for company in batch:
            if not company.ticker:
                continue
            price_local, mcap_local, currency = batch_results.get(company.ticker.upper(), (None, None, "USD"))
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
