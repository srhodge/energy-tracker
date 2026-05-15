from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session, selectinload
from typing import Optional

from app.database import get_db
from app.models import Company, Financial, ValueChainPosition, CompanyStatus
from app.schemas import (
    CompanyOut, CompanyDetail, PaginatedCompanies, TerritoryRollup, StatusSummary,
    CompanyLookupResult, CompanyAddRequest, CompanyAddResponse, CompanyUpdateRequest,
)

router = APIRouter(prefix="/companies", tags=["companies"])

_INACTIVE = (CompanyStatus.acquired, CompanyStatus.merged, CompanyStatus.delisted, CompanyStatus.non_equity)


def _latest_financial_subquery(db: Session):
    return (
        select(Financial.company_id, func.max(Financial.snapshot_date).label("max_date"))
        .group_by(Financial.company_id)
        .subquery()
    )


def _build_order(sort_by: Optional[str], sort_dir: Optional[str]) -> list:
    col, nullable = _SORT_COLUMNS.get(sort_by or "market_cap", _SORT_COLUMNS["market_cap"])
    desc = (sort_dir or "desc").lower() == "desc"
    primary = (col.desc().nullslast() if desc else col.asc().nullsfirst()) if nullable else (col.desc() if desc else col.asc())
    secondary = Company.name if col is not Company.name else Company.id
    return [primary, secondary]


_SORT_COLUMNS = {
    "name":         (Company.name,                          False),
    "ticker":       (Company.ticker,                        False),
    "price":        (Financial.price_usd,                   True),
    "country":      (Company.country,                       False),
    "territory":    (Company.wwt_territory,                 False),
    "supply_chain": (Company.supply_chain_position,         False),
    "segment":      (Company.industry,                      False),
    "q_rev":        (Financial.revenue_quarterly_usd,       True),
    "fy_rev":       (Financial.revenue_annual_usd,          True),
    "market_cap":   (Financial.market_cap_usd,              True),
}


@router.get("", response_model=PaginatedCompanies)
def list_companies(
    wwt_territory: Optional[str] = Query(None),
    industry: Optional[str] = Query(None),
    value_chain_position: Optional[ValueChainPosition] = Query(None),
    supply_chain_position: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    include_inactive: bool = Query(False),
    status: Optional[str] = Query(None),
    sort_by: Optional[str] = Query("market_cap"),
    sort_dir: Optional[str] = Query("desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    filters = []
    if wwt_territory:
        filters.append(Company.wwt_territory == wwt_territory)
    if industry:
        filters.append(Company.industry == industry)
    if value_chain_position:
        filters.append(Company.value_chain_position == value_chain_position)
    if supply_chain_position:
        filters.append(Company.supply_chain_position == supply_chain_position)
    if country:
        filters.append(Company.country == country)
    if search:
        filters.append(Company.name.ilike(f"%{search}%"))
    if status and status != "all":
        filters.append(Company.status == status)
    elif not status and not include_inactive:
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
        .add_columns(
            Financial.market_cap_usd, Financial.price_usd,
            Financial.revenue_quarterly_usd, Financial.revenue_annual_usd,
            Financial.revenue_quarter_label, Financial.revenue_fiscal_year_label,
        )
        .order_by(*_build_order(sort_by, sort_dir))
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
        out.latest_quarterly_revenue = row[3]
        out.latest_revenue = row[4]
        out.latest_quarter_label = row[5]
        out.latest_fiscal_year_label = row[6]
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
            func.sum(Financial.revenue_annual_usd).label("total_revenue_usd"),
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
            total_revenue_usd=r.total_revenue_usd,
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
    industries = db.scalars(
        select(Company.industry).distinct()
        .where(Company.industry.isnot(None))
        .order_by(Company.industry)
    ).all()
    return {
        "wwt_territories": territories,
        "countries": countries,
        "industries": industries,
        "value_chain_positions": [v.value for v in ValueChainPosition],
        "supply_chain_positions": supply_chain_positions,
    }


# ---------------------------------------------------------------------------
# Country → WWT territory inference (best-effort; confidence=low)
# ---------------------------------------------------------------------------

_COUNTRY_TERRITORY: dict[str, str] = {
    # North America (US territories assigned by city/state — default STOLA)
    "United States": "STOLA", "USA": "STOLA",
    # Canada
    "Canada": "CANADA",
    # Latin America
    "Mexico": "LATAM", "Brazil": "LATAM", "Colombia": "LATAM", "Argentina": "LATAM",
    "Chile": "LATAM", "Peru": "LATAM", "Venezuela": "LATAM",
    "Trinidad and Tobago": "LATAM", "Ecuador": "LATAM", "Bolivia": "LATAM",
    "Guyana": "LATAM", "Suriname": "LATAM",
    # Europe
    "United Kingdom": "EURO", "Germany": "EURO", "France": "EURO", "Netherlands": "EURO",
    "Norway": "EURO", "Italy": "EURO", "Spain": "EURO", "Sweden": "EURO",
    "Denmark": "EURO", "Finland": "EURO", "Belgium": "EURO", "Austria": "EURO",
    "Switzerland": "EURO", "Portugal": "EURO", "Poland": "EURO", "Greece": "EURO",
    "Czech Republic": "EURO", "Hungary": "EURO", "Romania": "EURO", "Turkey": "EURO",
    "Ireland": "EURO", "Luxembourg": "EURO", "Monaco": "EURO", "Cyprus": "EURO",
    "Bermuda": "EURO",
    # Middle East / North Africa
    "Saudi Arabia": "MENA", "United Arab Emirates": "MENA", "UAE": "MENA",
    "Qatar": "MENA", "Kuwait": "MENA", "Iraq": "MENA", "Iran": "MENA",
    "Oman": "MENA", "Bahrain": "MENA", "Jordan": "MENA", "Israel": "MENA",
    "Egypt": "MENA", "Lebanon": "MENA", "Syria": "MENA", "Yemen": "MENA",
    "Palestine": "MENA",
    # Africa
    "Nigeria": "EURO", "South Africa": "EURO", "Algeria": "EURO", "Angola": "EURO",
    "Libya": "EURO", "Ghana": "EURO", "Mozambique": "EURO", "Tanzania": "EURO",
    "Kenya": "EURO", "Senegal": "EURO", "Equatorial Guinea": "EURO",
    # Asia Pacific
    "China": "APAC", "Japan": "APAC", "India": "APAC", "Australia": "APAC",
    "South Korea": "APAC", "Korea": "APAC", "Indonesia": "APAC", "Malaysia": "APAC",
    "Singapore": "APAC", "Thailand": "APAC", "Vietnam": "APAC", "Philippines": "APAC",
    "Taiwan": "APAC", "Hong Kong": "APAC", "New Zealand": "APAC", "Bangladesh": "APAC",
    "Pakistan": "APAC", "Myanmar": "APAC", "Sri Lanka": "APAC", "Cambodia": "APAC",
    "Laos": "APAC", "Mongolia": "APAC", "Papua New Guinea": "APAC", "Fiji": "APAC",
    # Russia
    "Russia": "RUSSIA", "Kazakhstan": "RUSSIA", "Azerbaijan": "RUSSIA",
}


def _infer_wwt_territory(country: str | None) -> str | None:
    if not country:
        return None
    return _COUNTRY_TERRITORY.get(country)


@router.get("/missing-data")
def missing_data(db: Session = Depends(get_db)):
    """Return active companies grouped by which key fields are null/empty."""
    latest_sq = _latest_financial_subquery(db)

    rows = db.execute(
        select(
            Company.id,
            Company.name,
            Company.ticker,
            Company.country,
            Company.website,
            Company.industry,
            Financial.revenue_quarterly_usd,
            Financial.revenue_annual_usd,
        )
        .outerjoin(latest_sq, Company.id == latest_sq.c.company_id)
        .outerjoin(
            Financial,
            and_(
                Financial.company_id == Company.id,
                Financial.snapshot_date == latest_sq.c.max_date,
            ),
        )
        .where(Company.status.notin_(_INACTIVE))
        .order_by(Company.name)
    ).all()

    def _stub(row):
        return {"id": row.id, "name": row.name, "ticker": row.ticker, "country": row.country}

    missing_website = []
    missing_industry = []
    missing_revenue = []
    missing_all = []

    for row in rows:
        no_website = not row.website
        no_industry = not row.industry
        no_revenue = row.revenue_quarterly_usd is None and row.revenue_annual_usd is None

        if no_website:
            missing_website.append(_stub(row))
        if no_industry:
            missing_industry.append(_stub(row))
        if no_revenue:
            missing_revenue.append(_stub(row))
        if no_website and no_industry and no_revenue:
            missing_all.append(_stub(row))

    return {
        "missing_website": missing_website,
        "missing_industry": missing_industry,
        "missing_revenue": missing_revenue,
        "missing_all": missing_all,
    }


@router.get("/lookup", response_model=CompanyLookupResult)
def lookup_company(ticker: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    ticker = ticker.strip().upper()

    # Check duplicate
    existing = db.scalar(
        select(Company).where(func.upper(Company.ticker) == ticker)
    )
    if existing:
        return CompanyLookupResult(
            name=existing.name,
            ticker=existing.ticker,
            country=existing.country,
            already_exists=True,
            existing_id=existing.id,
        )

    # Fetch from yfinance
    try:
        import yfinance as yf
        info = yf.Ticker(ticker).info or {}
    except Exception:
        info = {}

    long_name = info.get("longName") or info.get("shortName") or ""
    if not long_name:
        return CompanyLookupResult(
            name=ticker,
            ticker=ticker,
            error="Ticker not found — check the symbol and try again.",
        )

    from app.services.seed_loader import _fix_text
    name = _fix_text(long_name) or ticker
    country = info.get("country")
    exchange = info.get("exchange")
    website = info.get("website")
    raw_desc = _fix_text(info.get("longBusinessSummary") or "")
    description = (raw_desc[:500] + "…") if raw_desc and len(raw_desc) > 500 else raw_desc or None

    # Currency + FX conversion
    from app.services.market_poller import _ticker_currency, _fetch_fx_rates, _to_usd
    raw_currency = info.get("currency") or ""
    currency = raw_currency if raw_currency else _ticker_currency(ticker)

    market_cap_local = info.get("marketCap")
    price_local = info.get("currentPrice") or info.get("regularMarketPrice")
    market_cap_usd = price_usd = None

    if currency == "USD":
        market_cap_usd = market_cap_local
        price_usd = price_local
    elif currency and (market_cap_local or price_local):
        try:
            fx = _fetch_fx_rates({currency})
            market_cap_usd = _to_usd(market_cap_local, currency, fx)
            price_usd = _to_usd(price_local, currency, fx)
        except Exception:
            pass

    # Supply chain classification (name-based, low confidence)
    from app.services.classify_supply_chain import _classify

    class _FakeCompany:
        energy_segment = None
        value_chain_position = None
        energy_category = None

    fake = _FakeCompany()
    fake.name = name  # type: ignore[attr-defined]
    supply_chain = _classify(fake)  # type: ignore[arg-type]

    wwt_territory = _infer_wwt_territory(country)

    industry = info.get("industry") or None

    return CompanyLookupResult(
        name=name,
        ticker=ticker,
        exchange=exchange,
        country=country,
        website=website,
        description=description,
        market_cap_usd=market_cap_usd,
        price_usd=price_usd,
        currency=currency,
        industry=industry,
        supply_chain_position=supply_chain,
        wwt_territory=wwt_territory,
        supply_chain_confidence="low",
        wwt_territory_confidence="low" if wwt_territory else "low",
    )


@router.post("/add", response_model=CompanyAddResponse, status_code=201)
def add_company(req: CompanyAddRequest, db: Session = Depends(get_db)):
    ticker_upper = req.ticker.strip().upper() if req.ticker else None

    # Duplicate check
    if ticker_upper:
        existing = db.scalar(
            select(Company).where(func.upper(Company.ticker) == ticker_upper)
        )
        if existing:
            raise HTTPException(status_code=409, detail=f"Company with ticker {ticker_upper} already exists (id={existing.id})")

    company = Company(
        name=req.name.strip(),
        ticker=ticker_upper,
        exchange=req.exchange,
        country=req.country,
        website=req.website,
        description=req.description,
        wwt_territory=req.wwt_territory,
        wwt_model=req.wwt_model,
        energy_maturity=req.energy_maturity,
        industry=req.industry,
        value_chain_position=req.value_chain_position,
        supply_chain_position=req.supply_chain_position,
        status=CompanyStatus.active,
        skip_market_poll=not req.is_public or not ticker_upper,
    )
    db.add(company)
    db.flush()

    # Classify supply chain if not supplied
    if not company.supply_chain_position:
        from app.services.classify_supply_chain import _classify
        company.supply_chain_position = _classify(company)

    db.commit()

    # Kick off market poll for public companies in background
    if req.is_public and ticker_upper:
        try:
            from app.services.market_poller import poll_once
            from app.database import SessionLocal
            import threading
            company_id = company.id

            def _bg_poll():
                with SessionLocal() as s:
                    poll_once(s, company_ids={company_id})

            threading.Thread(target=_bg_poll, daemon=True).start()
        except Exception:
            pass

    return CompanyAddResponse(id=company.id, name=company.name, ticker=company.ticker)


@router.put("/{company_id}", response_model=CompanyOut)
def update_company(company_id: int, req: CompanyUpdateRequest, db: Session = Depends(get_db)):
    company = db.scalar(select(Company).where(Company.id == company_id))
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Ticker uniqueness check if ticker is changing
    if req.ticker is not None:
        new_ticker = req.ticker.strip().upper() if req.ticker.strip() else None
        if new_ticker and new_ticker != (company.ticker or "").upper():
            conflict = db.scalar(
                select(Company).where(func.upper(Company.ticker) == new_ticker, Company.id != company_id)
            )
            if conflict:
                raise HTTPException(status_code=409, detail=f"Ticker {new_ticker} already used by company id={conflict.id}")
        company.ticker = new_ticker
        company.skip_market_poll = not new_ticker

    for field in ("name", "exchange", "country", "website", "description",
                  "wwt_territory", "wwt_model", "energy_maturity", "industry",
                  "value_chain_position", "supply_chain_position", "sub_sector",
                  "status", "acquired_by", "acquisition_notes", "skip_market_poll",
                  "revenue_manually_set", "ce_name", "ce_email", "ce_phone"):
        val = getattr(req, field)
        if val is not None:
            setattr(company, field, val)

    if req.name is not None and not req.name.strip():
        raise HTTPException(status_code=422, detail="Name cannot be blank")
    if req.name is not None:
        company.name = req.name.strip()

    db.commit()
    out = CompanyOut.model_validate(company)
    return out


@router.delete("/{company_id}", status_code=204)
def delete_company(company_id: int, db: Session = Depends(get_db)):
    company = db.scalar(select(Company).where(Company.id == company_id))
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    db.delete(company)
    db.commit()


@router.post("/{company_id}/repoll")
def repoll_company(
    company_id: int,
    ticker: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Set skip_market_poll=False (optionally update ticker) and immediately poll yfinance."""
    company = db.scalar(select(Company).where(Company.id == company_id))
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    if ticker is not None:
        new_ticker = ticker.strip().upper() if ticker.strip() else None
        if new_ticker and new_ticker != (company.ticker or "").upper():
            conflict = db.scalar(
                select(Company).where(func.upper(Company.ticker) == new_ticker, Company.id != company_id)
            )
            if conflict:
                raise HTTPException(status_code=409, detail=f"Ticker {new_ticker} already used by id={conflict.id}")
        company.ticker = new_ticker

    company.skip_market_poll = False
    db.commit()

    import threading
    from app.services.market_poller import poll_once
    from app.database import SessionLocal

    def _bg():
        with SessionLocal() as s:
            poll_once(s, company_ids={company_id})

    threading.Thread(target=_bg, daemon=True).start()

    return {"id": company.id, "name": company.name, "ticker": company.ticker, "poll_scheduled": True}


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
        out.latest_quarterly_revenue = latest.revenue_quarterly_usd
        out.latest_quarter_label = latest.revenue_quarter_label
        out.latest_fiscal_year_label = latest.revenue_fiscal_year_label
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
        out.latest_quarterly_revenue = latest.revenue_quarterly_usd
        out.latest_quarter_label = latest.revenue_quarter_label
        out.latest_fiscal_year_label = latest.revenue_fiscal_year_label
    return out
