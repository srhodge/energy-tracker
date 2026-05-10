from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func, and_, inspect as sa_inspect

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import settings
from app.database import engine, SessionLocal
from app.models import Base, Company, CompanyStatus
from app.routers import companies, events
from app.routers import news as news_router
from app.routers import analytics as analytics_router
from app.routers import crm as crm_router
from app.routers import intelligence as intelligence_router


_SEED_FILE = Path(__file__).parent.parent / "data" / "companies.xlsx"
_ALEMBIC_INI = Path(__file__).parent.parent / "alembic.ini"

_scheduler = BackgroundScheduler()


def _run_scraper():
    from app.services.news_scraper import scrape
    with SessionLocal() as db:
        n = scrape(db)
        if n:
            print(f"[news] +{n} new items", flush=True)


def _run_market_poll():
    from app.services.market_poller import poll_once, is_trading_day
    if not is_trading_day():
        return
    with SessionLocal() as db:
        poll_once(db)


def _run_non_usd_poll():
    """Re-poll non-USD tickers to apply currency conversion — runs once on startup."""
    from app.services.market_poller import poll_non_usd_companies
    with SessionLocal() as db:
        poll_non_usd_companies(db)


def _run_fundamentals_poll():
    """Fetch/refresh revenue for companies with stale or missing quarterly data."""
    from app.services.market_poller import poll_fundamentals
    with SessionLocal() as db:
        poll_fundamentals(db)


def _run_migrations():
    from alembic.config import Config
    from alembic import command

    alembic_cfg = Config(str(_ALEMBIC_INI))

    with engine.connect() as conn:
        tables = sa_inspect(conn).get_table_names()
        if "companies" in tables and "alembic_version" not in tables:
            print("[migrations] Existing DB detected — stamping alembic head", flush=True)
            command.stamp(alembic_cfg, "head")
            return

    print("[migrations] Running alembic upgrade head ...", flush=True)
    command.upgrade(alembic_cfg, "head")
    print("[migrations] Done.", flush=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _run_migrations()

    with SessionLocal() as db:
        count = db.scalar(select(func.count(Company.id)))
        if count == 0 and _SEED_FILE.exists():
            print(f"[seed] No companies found — loading {_SEED_FILE} ...")
            from app.services.seed_loader import load_excel
            loaded = load_excel(_SEED_FILE, db)
            print(f"[seed] Loaded {loaded} companies.")

        from app.services.seed_loader import clean_company_names
        fixed = clean_company_names(db)
        if fixed:
            print(f"[cleanup] Fixed encoding/artifacts in {fixed} company names.", flush=True)

        unclassified = db.scalar(
            select(func.count(Company.id)).where(Company.supply_chain_position.is_(None))
        )
        if unclassified > 0:
            print(f"[classify] Classifying {unclassified} companies...")
            from app.services.classify_supply_chain import classify_all
            n = classify_all(db)
            print(f"[classify] Done — {n} companies classified.")

        total = db.scalar(select(func.count(Company.id)))
        unknown = db.scalar(
            select(func.count(Company.id)).where(Company.status == CompanyStatus.unknown)
        )
        if total and unknown and unknown > total // 2:
            print(f"[status] {unknown}/{total} companies Unknown — running enrichment...")
            from app.services.status_checker import run_phase1, run_phase2_deep
            run_phase1(db)
            changed, _ = run_phase2_deep(db)
            print(f"[status] Done — {changed} companies enriched beyond Unknown.")

        # One-time backfill: protect all existing revenue data as manually set
        from app.models import Financial as _Financial
        needs_backfill = db.scalar(
            select(func.count(Company.id)).where(
                Company.revenue_manually_set == False,
                Company.id.in_(
                    select(_Financial.company_id).where(_Financial.revenue_annual_usd.isnot(None))
                )
            )
        )
        if needs_backfill and needs_backfill > 0:
            print(f"[backfill] Marking {needs_backfill} companies with existing revenue as manually set ...", flush=True)
            to_backfill = db.scalars(
                select(Company).where(
                    Company.revenue_manually_set == False,
                    Company.id.in_(
                        select(_Financial.company_id).where(_Financial.revenue_annual_usd.isnot(None))
                    )
                )
            ).all()
            for c in to_backfill:
                c.revenue_manually_set = True
            db.commit()
            print(f"[backfill] Done — {needs_backfill} companies protected.", flush=True)

        # Classify skip_market_poll flags (fast — DB queries only, no external calls)
        from app.services.market_poller import classify_skip_flags, is_poll_stale, is_trading_day, needs_initial_fundamentals, needs_industry_population, needs_website_population
        skip, active = classify_skip_flags(db)
        print(f"[market-poll] Skip flags set: {skip} skipped, {active} pollable", flush=True)
        startup_poll_needed = is_poll_stale(db) and is_trading_day()
        fundamentals_needed = needs_initial_fundamentals(db) or needs_industry_population(db) or needs_website_population(db)

    # News scraper: immediately on startup, then every 6 hours
    _scheduler.add_job(_run_scraper, "interval", hours=6, next_run_time=datetime.utcnow())

    # Market poller: 9:30, 11:30, 13:30, 15:30, 16:35 ET — Mon–Fri
    for hour, minute in [(9, 30), (11, 30), (13, 30), (15, 30), (16, 35)]:
        _scheduler.add_job(
            _run_market_poll,
            CronTrigger(
                day_of_week="mon-fri",
                hour=hour,
                minute=minute,
                timezone="America/New_York",
            ),
        )

    # Always re-poll non-USD tickers on startup to correct any pre-fix currency data.
    # Runs in a background thread; only covers ~100 non-USD companies so takes ~2 min.
    print("[market-poll] Scheduling startup non-USD currency correction poll ...", flush=True)
    _scheduler.add_job(_run_non_usd_poll, "date", run_date=datetime.utcnow())

    # If today's full data is stale, fire a complete poll (runs concurrently with non-USD poll)
    if startup_poll_needed:
        print("[market-poll] Stale data — scheduling full background poll ...", flush=True)
        _scheduler.add_job(_run_market_poll, "date", run_date=datetime.utcnow())

    # Fundamentals poll: every Saturday at 8am ET
    _scheduler.add_job(
        _run_fundamentals_poll,
        CronTrigger(
            day_of_week="sat",
            hour=8,
            minute=0,
            timezone="America/New_York",
        ),
    )

    # On startup, run fundamentals immediately if companies are missing revenue, industry, or websites
    if fundamentals_needed:
        print("[fundamentals] Missing data (revenue/industry/website) — scheduling startup fundamentals poll ...", flush=True)
        _scheduler.add_job(_run_fundamentals_poll, "date", run_date=datetime.utcnow())

    _scheduler.start()

    yield

    _scheduler.shutdown(wait=False)


app = FastAPI(
    title="Energy Tracker API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(companies.router)
app.include_router(events.router)
app.include_router(news_router.router)
app.include_router(analytics_router.router)
app.include_router(crm_router.router)
app.include_router(intelligence_router.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/admin/status")
def admin_status():
    from app.services.market_poller import needs_industry_population, needs_initial_fundamentals
    from sqlalchemy import select, func, or_
    from app.services.market_poller import _ENERGY_SEGMENT_VALUES
    with SessionLocal() as db:
        total = db.scalar(select(func.count(Company.id)))
        null_industry = db.scalar(
            select(func.count(Company.id)).where(Company.industry.is_(None))
        )
        seeded_industry = db.scalar(
            select(func.count(Company.id)).where(
                Company.industry.isnot(None),
                Company.industry.in_(_ENERGY_SEGMENT_VALUES),
            )
        )
        yf_industry = total - null_industry - seeded_industry
        needs_industry = needs_industry_population(db)
        needs_fundamentals = needs_initial_fundamentals(db)
    return {
        "total_companies": total,
        "null_industry": null_industry,
        "seeded_from_energy_segment": seeded_industry,
        "populated_from_yfinance": yf_industry,
        "needs_industry_population": needs_industry,
        "needs_initial_fundamentals": needs_fundamentals,
    }


_fundamentals_run_result: dict = {}


@app.post("/admin/trigger-fundamentals")
def admin_trigger_fundamentals():
    import threading
    global _fundamentals_run_result
    _fundamentals_run_result = {"status": "running"}

    def _run():
        global _fundamentals_run_result
        try:
            from app.services.market_poller import poll_fundamentals
            with SessionLocal() as db:
                result = poll_fundamentals(db)
            _fundamentals_run_result = {"status": "complete", **result}
            print(f"[admin] fundamentals poll complete: {result}", flush=True)
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            _fundamentals_run_result = {"status": "error", "error": str(e), "traceback": tb}
            print(f"[admin] fundamentals poll FAILED: {e}\n{tb}", flush=True)

    threading.Thread(target=_run, daemon=True).start()
    return {"status": "fundamentals poll started in background"}


@app.get("/admin/fundamentals-result")
def admin_fundamentals_result():
    return _fundamentals_run_result


@app.post("/admin/trigger-fundamentals-targeted")
def admin_trigger_fundamentals_targeted(body: dict):
    """Run fundamentals poll for a specific list of tickers (forced, ignores staleness)."""
    import threading
    tickers = set(body.get("tickers", []))
    if not tickers:
        return {"error": "No tickers provided"}
    global _fundamentals_run_result
    _fundamentals_run_result = {"status": "running", "tickers": list(tickers)}

    def _run():
        global _fundamentals_run_result
        try:
            from app.services.market_poller import poll_fundamentals
            with SessionLocal() as db:
                result = poll_fundamentals(db, ticker_filter=tickers)
            _fundamentals_run_result = {"status": "complete", **result}
            print(f"[admin] targeted fundamentals poll complete: {result}", flush=True)
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            _fundamentals_run_result = {"status": "error", "error": str(e), "traceback": tb}
            print(f"[admin] targeted fundamentals poll FAILED: {e}\n{tb}", flush=True)

    threading.Thread(target=_run, daemon=True).start()
    return {"status": f"targeted fundamentals poll started for {len(tickers)} tickers"}


@app.post("/admin/set-revenue")
def admin_set_revenue(body: dict):
    """Manually set revenue fields on a company's latest (or new) Financial record."""
    from sqlalchemy import select, func
    from app.models import Financial
    from app.services.market_poller import _et_today
    company_id = body.get("company_id")
    if not company_id:
        return {"error": "company_id required"}
    annual_usd  = body.get("revenue_annual_usd")
    quarterly_usd = body.get("revenue_quarterly_usd")
    fy_label    = body.get("revenue_fiscal_year_label")
    q_label     = body.get("revenue_quarter_label")
    with SessionLocal() as db:
        latest_sq = (
            select(Financial.company_id, func.max(Financial.snapshot_date).label("max_date"))
            .group_by(Financial.company_id).subquery()
        )
        rec = db.scalars(
            select(Financial).join(latest_sq, and_(
                Financial.company_id == latest_sq.c.company_id,
                Financial.snapshot_date == latest_sq.c.max_date,
            )).where(Financial.company_id == company_id)
        ).first()
        if rec is None:
            from datetime import datetime
            rec = Financial(company_id=company_id, snapshot_date=_et_today(), last_market_update=datetime.utcnow())
            db.add(rec)
        if annual_usd  is not None: rec.revenue_annual_usd    = annual_usd
        if quarterly_usd is not None: rec.revenue_quarterly_usd = quarterly_usd
        if fy_label    is not None: rec.revenue_fiscal_year_label = fy_label
        if q_label     is not None: rec.revenue_quarter_label = q_label
        company_rec = db.get(Company, company_id)
        if company_rec:
            company_rec.revenue_manually_set = True
        db.commit()
    return {"status": "ok", "company_id": company_id, "revenue_annual_usd": annual_usd, "revenue_fiscal_year_label": fy_label}


@app.get("/admin/test-industry")
def admin_test_industry():
    """Synchronously test yfinance industry fetch on the first 5 pollable companies."""
    import yfinance as yf
    from sqlalchemy import select
    with SessionLocal() as db:
        companies = db.scalars(
            select(Company).where(
                Company.skip_market_poll == False,
                Company.ticker.isnot(None),
            ).limit(5)
        ).all()
        results = []
        for c in companies:
            try:
                info = yf.Ticker(c.ticker).info or {}
                results.append({
                    "ticker": c.ticker,
                    "current_industry": c.industry,
                    "yf_industry": info.get("industry"),
                    "yf_keys_count": len(info),
                })
            except Exception as e:
                results.append({"ticker": c.ticker, "current_industry": c.industry, "error": str(e)})
    return {"results": results}
