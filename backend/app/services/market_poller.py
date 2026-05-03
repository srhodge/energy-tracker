"""
Daily market data poller using yfinance.

Usage:
    python -m app.services.market_poller

Run this daily via Task Scheduler / cron / GitHub Actions.
"""
import logging
from datetime import date

import yfinance as yf
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Company, Financial

logger = logging.getLogger(__name__)


def _search_ticker(company_name: str) -> str | None:
    """Search yfinance by company name and return the best matching ticker symbol."""
    try:
        results = yf.Search(company_name, max_results=5, news_count=0)
        quotes = results.quotes
        if not quotes:
            return None
        for q in quotes:
            if q.get("quoteType") == "EQUITY":
                return q.get("symbol")
        return quotes[0].get("symbol")
    except Exception as exc:
        logger.debug("Ticker search failed for %r: %s", company_name, exc)
        return None


def _fetch_single(company_id: int, ticker: str, today: date) -> Financial | None:
    """Fetch price and market cap for one ticker outside of a batch download."""
    try:
        info = yf.Ticker(ticker).fast_info
        price = getattr(info, "last_price", None) or getattr(info, "previous_close", None)
        market_cap = getattr(info, "market_cap", None)
        if price is None:
            return None
        return Financial(
            company_id=company_id,
            price_usd=float(price),
            market_cap_usd=float(market_cap) if market_cap else None,
            snapshot_date=today,
        )
    except Exception as exc:
        logger.debug("Single-ticker fetch failed for %s: %s", ticker, exc)
        return None


def poll_once(db: Session, batch_size: int = 50) -> dict:
    companies = db.scalars(
        select(Company).where(Company.ticker.isnot(None))
    ).all()

    today = date.today()
    updated = 0
    failed = 0

    # Batch tickers to reduce API calls
    for i in range(0, len(companies), batch_size):
        batch = companies[i : i + batch_size]
        tickers = [c.ticker for c in batch if c.ticker]
        if not tickers:
            continue

        try:
            data = yf.download(
                tickers,
                period="1d",
                auto_adjust=True,
                progress=False,
                threads=True,
            )
        except Exception as exc:
            logger.warning("yfinance batch download failed: %s", exc)
            failed += len(batch)
            continue

        for company in batch:
            if not company.ticker:
                continue
            try:
                if len(tickers) == 1:
                    price = float(data["Close"].iloc[-1])
                else:
                    price = float(data["Close"][company.ticker].iloc[-1])

                info = yf.Ticker(company.ticker).fast_info
                market_cap = getattr(info, "market_cap", None)

                db.add(Financial(
                    company_id=company.id,
                    price_usd=price,
                    market_cap_usd=float(market_cap) if market_cap else None,
                    snapshot_date=today,
                ))
                updated += 1
            except Exception as exc:
                logger.debug("Could not update %s (%s): %s", company.ticker, company.name, exc)
                # Fall back: search for the correct ticker by company name
                new_ticker = _search_ticker(company.name)
                if new_ticker and new_ticker != company.ticker:
                    logger.info(
                        "Ticker updated for %s: %s -> %s",
                        company.name, company.ticker, new_ticker,
                    )
                    company.ticker = new_ticker
                    db.flush()
                    financial = _fetch_single(company.id, new_ticker, today)
                    if financial:
                        db.add(financial)
                        updated += 1
                    else:
                        logger.debug("Retry also failed for %s (%s)", new_ticker, company.name)
                        failed += 1
                else:
                    failed += 1

    db.commit()
    return {"updated": updated, "failed": failed, "date": str(today)}


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    with SessionLocal() as db:
        result = poll_once(db)
        logger.info("Market poll complete: %s", result)


if __name__ == "__main__":
    main()
