from fastapi import APIRouter, Depends
from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Company, Financial

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/scatter")
def scatter(db: Session = Depends(get_db)):
    total = db.scalar(select(func.count(Company.id)))

    latest_sq = (
        select(Financial.company_id, func.max(Financial.snapshot_date).label("max_date"))
        .group_by(Financial.company_id)
        .subquery()
    )

    rows = db.execute(
        select(
            Company.name,
            Company.ticker,
            Company.supply_chain_position,
            Company.country,
            Company.wwt_territory,
            Financial.revenue_annual_usd,
            Financial.revenue_fiscal_year_label,
            Financial.market_cap_usd,
        )
        .join(latest_sq, and_(
            Financial.company_id == latest_sq.c.company_id,
            Financial.snapshot_date == latest_sq.c.max_date,
        ))
        .join(Company, Company.id == Financial.company_id)
        .where(
            Financial.revenue_annual_usd.isnot(None),
            Financial.revenue_annual_usd > 0,
            Financial.market_cap_usd.isnot(None),
            Financial.market_cap_usd > 0,
        )
        .order_by(Company.name)
    ).all()

    items = [
        {
            "name": r.name,
            "ticker": r.ticker,
            "supply_chain_position": r.supply_chain_position,
            "country": r.country,
            "territory": r.wwt_territory,
            "revenue_annual_usd": r.revenue_annual_usd,
            "revenue_fiscal_year_label": r.revenue_fiscal_year_label,
            "market_cap_usd": r.market_cap_usd,
        }
        for r in rows
    ]

    return {
        "total_companies": total or 0,
        "included_count": len(items),
        "items": items,
    }
