from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session, selectinload
from typing import Optional

from app.database import get_db
from app.models import Company, Financial, EnergySegment, ValueChainPosition, CompanyStatus
from app.schemas import CompanyOut, CompanyDetail, PaginatedCompanies, TerritoryRollup, StatusSummary

router = APIRouter(prefix="/companies", tags=["companies"])

_INACTIVE = (CompanyStatus.acquired, CompanyStatus.merged, CompanyStatus.delisted, CompanyStatus.non_equity)


def _latest_financial_subquery(db: Session):
    return (
        select(Financial.company_id, func.max(Financial.snapshot_date).label("max_date"))
        .group_by(Financial.company_id)
        .subquery()
    )


@router.get("", response_model=PaginatedCompanies)
def list_companies(
    wwt_territory: Optional[str] = Query(None),
    energy_segment: Optional[EnergySegment] = Query(None),
    value_chain_position: Optional[ValueChainPosition] = Query(None),
    supply_chain_position: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    include_inactive: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    filters = []
    if wwt_territory:
        filters.append(Company.wwt_territory == wwt_territory)
    if energy_segment:
        filters.append(Company.energy_segment == energy_segment)
    if value_chain_position:
        filters.append(Company.value_chain_position == value_chain_position)
    if supply_chain_position:
        filters.append(Company.supply_chain_position == supply_chain_position)
    if country:
        filters.append(Company.country == country)
    if search:
        filters.append(Company.name.ilike(f"%{search}%"))
    if not include_inactive:
        filters.append(Company.status.notin_(_INACTIVE))

    base_q = select(Company).where(and_(*filters)) if filters else select(Company)
    total = db.scalar(select(func.count()).select_from(base_q.subquery()))

    latest_sq = _latest_financial_subquery(db)
    companies_q = (
        base_q.outerjoin(latest_sq, Company.id == latest_sq.c.company_id)
        .outerjoin(
            Financial,
            and_(
                Financial.company_id == Company.id,
                Financial.snapshot_date == latest_sq.c.max_date,
            ),
        )
        .add_columns(Financial.market_cap_usd, Financial.price_usd)
        .order_by(Financial.market_cap_usd.desc().nullslast(), Company.name)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    rows = db.execute(companies_q).all()
    items = []
    for row in rows:
        company = row[0]
        out = CompanyOut.model_validate(company)
        out.latest_market_cap = row[1]
        out.latest_price = row[2]
        items.append(out)

    return PaginatedCompanies(total=total, page=page, page_size=page_size, items=items)


@router.get("/status-summary", response_model=StatusSummary)
def status_summary(db: Session = Depends(get_db)):
    rows = db.execute(
        select(Company.status, func.count(Company.id).label("n"))
        .group_by(Company.status)
    ).all()
    counts = {str(r.status): r.n for r in rows}
    return StatusSummary(
        Active=counts.get("Active", 0),
        Acquired=counts.get("Acquired", 0),
        Merged=counts.get("Merged", 0),
        Delisted=counts.get("Delisted", 0),
        Unknown=counts.get("Unknown", 0),
    )


@router.get("/territory-rollup", response_model=list[TerritoryRollup])
def territory_rollup(db: Session = Depends(get_db)):
    latest_sq = _latest_financial_subquery(db)
    rows = db.execute(
        select(
            Company.wwt_territory,
            func.count(Company.id).label("company_count"),
            func.sum(Financial.market_cap_usd).label("total_market_cap_usd"),
        )
        .outerjoin(latest_sq, Company.id == latest_sq.c.company_id)
        .outerjoin(
            Financial,
            and_(
                Financial.company_id == Company.id,
                Financial.snapshot_date == latest_sq.c.max_date,
            ),
        )
        .where(Company.wwt_territory.isnot(None))
        .group_by(Company.wwt_territory)
        .order_by(func.sum(Financial.market_cap_usd).desc().nullslast())
    ).all()

    return [
        TerritoryRollup(
            wwt_territory=r.wwt_territory,
            company_count=r.company_count,
            total_market_cap_usd=r.total_market_cap_usd,
        )
        for r in rows
    ]


@router.get("/supply-chain-rollup")
def supply_chain_rollup(db: Session = Depends(get_db)):
    latest_sq = _latest_financial_subquery(db)
    rows = db.execute(
        select(
            Company.supply_chain_position,
            func.count(Company.id).label("company_count"),
            func.sum(Financial.market_cap_usd).label("total_market_cap_usd"),
        )
        .outerjoin(latest_sq, Company.id == latest_sq.c.company_id)
        .outerjoin(
            Financial,
            and_(
                Financial.company_id == Company.id,
                Financial.snapshot_date == latest_sq.c.max_date,
            ),
        )
        .where(Company.supply_chain_position.isnot(None))
        .group_by(Company.supply_chain_position)
        .order_by(func.sum(Financial.market_cap_usd).desc().nullslast())
    ).all()
    return [
        {
            "supply_chain_position": r.supply_chain_position,
            "company_count": r.company_count,
            "total_market_cap_usd": r.total_market_cap_usd,
        }
        for r in rows
    ]


@router.get("/filter-options")
def filter_options(db: Session = Depends(get_db)):
    territories = db.scalars(
        select(Company.wwt_territory).distinct().where(Company.wwt_territory.isnot(None)).order_by(Company.wwt_territory)
    ).all()
    countries = db.scalars(
        select(Company.country).distinct().where(Company.country.isnot(None)).order_by(Company.country)
    ).all()
    supply_chain_positions = db.scalars(
        select(Company.supply_chain_position).distinct()
        .where(Company.supply_chain_position.isnot(None))
        .order_by(Company.supply_chain_position)
    ).all()
    return {
        "wwt_territories": territories,
        "countries": countries,
        "energy_segments": [e.value for e in EnergySegment],
        "value_chain_positions": [v.value for v in ValueChainPosition],
        "supply_chain_positions": supply_chain_positions,
    }


@router.get("/{company_id}", response_model=CompanyDetail)
def get_company(company_id: int, db: Session = Depends(get_db)):
    company = db.scalar(
        select(Company)
        .options(selectinload(Company.financials), selectinload(Company.events))
        .where(Company.id == company_id)
    )
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    out = CompanyDetail.model_validate(company)
    if company.financials:
        latest = max(company.financials, key=lambda f: f.snapshot_date)
        out.latest_market_cap = latest.market_cap_usd
        out.latest_price = latest.price_usd
        out.latest_revenue = latest.revenue_annual_usd
    return out


@router.get("/by-ticker/{ticker}", response_model=CompanyDetail)
def get_company_by_ticker(ticker: str, db: Session = Depends(get_db)):
    company = db.scalar(
        select(Company)
        .options(selectinload(Company.financials), selectinload(Company.events))
        .where(func.upper(Company.ticker) == ticker.upper())
    )
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    out = CompanyDetail.model_validate(company)
    if company.financials:
        latest = max(company.financials, key=lambda f: f.snapshot_date)
        out.latest_market_cap = latest.market_cap_usd
        out.latest_price = latest.price_usd
        out.latest_revenue = latest.revenue_annual_usd
    return out
