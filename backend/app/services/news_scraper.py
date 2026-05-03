"""
News scraper stub — fetches RSS feeds per company and stores events.

Usage:
    python -m app.services.news_scraper

Extend RSS_FEEDS or the per-company website logic to add real feeds.
"""
import logging
from datetime import date, datetime
from typing import Optional

import feedparser
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Company, Event, EventType

logger = logging.getLogger(__name__)

# Global feeds not tied to a single company (industry-wide)
GLOBAL_FEEDS: list[str] = [
    "https://feeds.reuters.com/reuters/businessNews",
    "https://www.offshore-energy.biz/feed/",
    "https://www.naturalgasintel.com/feed/",
]


def _parse_date(entry) -> Optional[date]:
    for attr in ("published_parsed", "updated_parsed"):
        t = getattr(entry, attr, None)
        if t:
            try:
                return datetime(*t[:6]).date()
            except Exception:
                pass
    return date.today()


def scrape_feed(url: str, db: Session, company: Optional[Company] = None, limit: int = 10) -> int:
    try:
        feed = feedparser.parse(url)
    except Exception as exc:
        logger.warning("Failed to parse feed %s: %s", url, exc)
        return 0

    stored = 0
    for entry in feed.entries[:limit]:
        title = getattr(entry, "title", "").strip()
        summary = getattr(entry, "summary", "") or ""
        link = getattr(entry, "link", None)
        event_date = _parse_date(entry)

        if not title:
            continue

        event = Event(
            company_id=company.id if company else None,
            event_type=EventType.news,
            title=title[:500],
            summary=summary[:5000],
            source_url=link,
            event_date=event_date,
        )
        # Deduplicate by source_url
        if link:
            exists = db.scalar(select(Event).where(Event.source_url == link).limit(1))
            if exists:
                continue

        if company:
            db.add(event)
            stored += 1

    db.flush()
    return stored


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    with SessionLocal() as db:
        companies = db.scalars(
            select(Company).where(Company.website.isnot(None)).limit(100)
        ).all()

        total = 0
        for company in companies:
            # Attempt a generic RSS path — real feeds require per-company configuration
            rss_url = company.website.rstrip("/") + "/feed/"
            count = scrape_feed(rss_url, db, company=company)
            if count:
                logger.info("%s: %d new events", company.name, count)
                total += count

        db.commit()
        logger.info("News scrape complete. Total new events: %d", total)


if __name__ == "__main__":
    main()
