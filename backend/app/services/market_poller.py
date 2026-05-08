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

def _fetch_batch(tickers: list[str]) -> dict[str, tuple[float | None, float | None]]:
    """
    Download close price and market cap for a batch of tickers.
    Returns {TICKER: (price, market_cap)}.
    """
    if not tickers:
        return {}

    results: dict[str, tuple[float | None, float | None]] = {}

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
            results[t] = (price, None)
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
                results[t] = (price, None)
    except Exception as e:
        print(f"    [market-poll] Batch download error: {e}", flush=True)
        for t in tickers:
            results[t] = (None, None)

    # Fetch market caps individually (not in batch download)
    for t in list(results.keys()):
        if results[t][0] is not None:
            try:
                mcap = getattr(yf.Ticker(t).fast_info, "market_cap", None)
                results[t] = (results[t][0], float(mcap) if mcap else None)
            except Exception:
                pass

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

        for company in batch:
            if not company.ticker:
                continue
            price, market_cap = batch_results.get(company.ticker.upper(), (None, None))
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
