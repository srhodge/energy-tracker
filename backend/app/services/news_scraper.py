import re
import logging
from datetime import datetime

import feedparser
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Company, NewsItem

log = logging.getLogger(__name__)

FEEDS = [
    ("Reuters", "https://feeds.reuters.com/reuters/businessNews"),
    ("OilPrice.com", "https://oilprice.com/rss/main"),
]


def _build_indexes(db: Session):
    companies = db.scalars(select(Company)).all()

    ticker_map: dict[str, Company] = {}
    for c in companies:
        if c.ticker:
            ticker_map[c.ticker.upper()] = c
            base = c.ticker.split(".")[0].upper()
            ticker_map[base] = c

    # Sorted longest-first so "ExxonMobil" matches before "Mobil"
    name_list: list[tuple[str, Company]] = sorted(
        [(c.name.lower(), c) for c in companies if len(c.name) >= 5],
        key=lambda x: len(x[0]),
        reverse=True,
    )
    return ticker_map, name_list


def _match(headline: str, ticker_map: dict, name_list: list) -> "Company | None":
    # 1. Ticker in parentheses: (XOM), (SHEL.L)
    for raw in re.findall(r"\(([A-Z]{1,6}(?:\.[A-Z]{1,2})?)\)", headline):
        base = raw.split(".")[0]
        if base in ticker_map:
            return ticker_map[base]

    # 2. Standalone uppercase word matching a known ticker
    for word in re.findall(r"\b([A-Z]{2,5})\b", headline):
        if word in ticker_map:
            return ticker_map[word]

    # 3. Company name substring (case-insensitive)
    hl = headline.lower()
    for name, company in name_list:
        if name in hl:
            return company

    return None


def scrape(db: Session) -> int:
    ticker_map, name_list = _build_indexes(db)
    total_added = 0

    for source_name, url in FEEDS:
        added = 0
        try:
            feed = feedparser.parse(url)
            if feed.bozo and not feed.entries:
                log.warning("[news] %s: feed error — %s", source_name, feed.bozo_exception)
                continue

            for entry in feed.entries:
                headline = (entry.get("title") or "").strip()
                link = (entry.get("link") or "").strip()
                if not headline or not link:
                    continue

                if db.scalar(select(NewsItem.id).where(NewsItem.source_url == link)):
                    continue

                pt = entry.get("published_parsed")
                published_at = datetime(*pt[:6]) if pt else None

                company = _match(headline, ticker_map, name_list)
                db.add(NewsItem(
                    company_id=company.id if company else None,
                    headline=headline,
                    source=source_name,
                    source_url=link,
                    published_at=published_at,
                ))
                added += 1

            db.commit()
            log.info("[news] %s: +%d new items", source_name, added)
            total_added += added

        except Exception:
            log.exception("[news] %s: unexpected error", source_name)

    return total_added
