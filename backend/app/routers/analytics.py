from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Company, Financial

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _median(vals: list) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    mid = len(s) // 2
    return s[mid] if len(s) % 2 else (s[mid - 1] + s[mid]) / 2


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
            Company.id,
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
            "id": r.id,
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


@router.get("/charts")
def charts(
    territory: str = Query(default=""),
    country: str = Query(default=""),
    value_chain: str = Query(default=""),
    ps_filter: str = Query(default=""),
    db: Session = Depends(get_db),
):
    latest_sq = (
        select(Financial.company_id, func.max(Financial.snapshot_date).label("max_date"))
        .group_by(Financial.company_id)
        .subquery()
    )

    q = (
        select(
            Company.supply_chain_position,
            Company.wwt_territory,
            Company.country,
            Financial.revenue_annual_usd,
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
    )

    if territory:
        q = q.where(Company.wwt_territory == territory)
    if country:
        q = q.where(Company.country == country)
    if value_chain:
        q = q.where(Company.supply_chain_position == value_chain)

    rows = db.execute(q).all()

    def ps(r):
        return r.market_cap_usd / r.revenue_annual_usd

    if ps_filter == "under1":
        rows = [r for r in rows if ps(r) < 1]
    elif ps_filter == "1to3":
        rows = [r for r in rows if 1 <= ps(r) <= 3]
    elif ps_filter == "over3":
        rows = [r for r in rows if ps(r) > 3]

    total_rev = sum(r.revenue_annual_usd for r in rows) or 1
    total_cap = sum(r.market_cap_usd for r in rows) or 1
    overall_median_ps = _median([ps(r) for r in rows])

    # Aggregate by segment
    seg: dict[str, dict] = {}
    for r in rows:
        k = r.supply_chain_position or "Other"
        if k not in seg:
            seg[k] = {"rev": 0.0, "cap": 0.0, "ps_vals": [], "count": 0}
        seg[k]["rev"] += r.revenue_annual_usd
        seg[k]["cap"] += r.market_cap_usd
        seg[k]["ps_vals"].append(ps(r))
        seg[k]["count"] += 1

    by_segment = sorted(
        [
            {
                "segment": k,
                "company_count": v["count"],
                "median_ps": _median(v["ps_vals"]),
                "revenue_share": v["rev"] / total_rev,
                "cap_share": v["cap"] / total_cap,
                "total_revenue": v["rev"],
                "total_cap": v["cap"],
                "implied_ps": v["cap"] / v["rev"] if v["rev"] else 0,
            }
            for k, v in seg.items()
        ],
        key=lambda x: x["implied_ps"],
        reverse=True,
    )

    # Aggregate by territory
    terr: dict[str, dict] = {}
    for r in rows:
        k = r.wwt_territory or "Other"
        if k not in terr:
            terr[k] = {"caps": [], "count": 0}
        terr[k]["caps"].append(r.market_cap_usd)
        terr[k]["count"] += 1

    by_territory = [
        {
            "territory": k,
            "company_count": v["count"],
            "median_cap": _median(v["caps"]),
            "total_cap": sum(v["caps"]),
        }
        for k, v in terr.items()
    ]

    return {
        "by_segment": by_segment,
        "by_territory": by_territory,
        "overall_median_ps": overall_median_ps,
        "filters_applied": {
            "territory": territory,
            "country": country,
            "value_chain": value_chain,
            "ps_filter": ps_filter,
        },
    }
