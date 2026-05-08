from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc, func
from sqlalchemy.orm import Session, joinedload
from typing import Optional

from app.database import get_db
from app.models import NewsItem, Company
from app.schemas import NewsItemOut

router = APIRouter(prefix="/news", tags=["news"])


def _enrich(items: list[NewsItem]) -> list[NewsItemOut]:
    result = []
    for item in items:
        out = NewsItemOut.model_validate(item)
        if item.company:
            out.company_name = item.company.name
            out.company_ticker = item.company.ticker
        result.append(out)
    return result


@router.get("", response_model=list[NewsItemOut])
def list_news(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    items = db.scalars(
        select(NewsItem)
        .options(joinedload(NewsItem.company))
        .order_by(desc(NewsItem.published_at))
        .limit(limit)
    ).all()
    return _enrich(items)


@router.get("/{ticker}", response_model=list[NewsItemOut])
def news_by_ticker(
    ticker: str,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    items = db.scalars(
        select(NewsItem)
        .options(joinedload(NewsItem.company))
        .join(Company, NewsItem.company_id == Company.id)
        .where(func.upper(Company.ticker) == ticker.upper())
        .order_by(desc(NewsItem.published_at))
        .limit(limit)
    ).all()
    return _enrich(items)
