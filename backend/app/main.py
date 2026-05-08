from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func, inspect as sa_inspect

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import settings
from app.database import engine, SessionLocal
from app.models import Base, Company, CompanyStatus
from app.routers import companies, events
from app.routers import news as news_router


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

        # Classify skip_market_poll flags (fast — DB queries only, no external calls)
        from app.services.market_poller import classify_skip_flags, is_poll_stale, is_trading_day
        skip, active = classify_skip_flags(db)
        print(f"[market-poll] Skip flags set: {skip} skipped, {active} pollable", flush=True)
        startup_poll_needed = is_poll_stale(db) and is_trading_day()

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

    # If today's data is stale, fire a poll in the background immediately after startup
    # (scheduled job runs in a thread — does NOT block uvicorn from binding)
    if startup_poll_needed:
        print("[market-poll] Stale data — scheduling immediate background poll ...", flush=True)
        _scheduler.add_job(_run_market_poll, "date", run_date=datetime.utcnow())

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


@app.get("/health")
def health():
    return {"status": "ok"}
