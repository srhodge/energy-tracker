from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func, inspect as sa_inspect

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import settings
from app.database import engine, SessionLocal
from app.models import Base, Company
from app.routers import companies, events
from app.routers import news as news_router
from app.routers import admin as admin_router

_SEED_FILE = Path(__file__).parent.parent / "data" / "companies.xlsx"
_ALEMBIC_INI = Path(__file__).parent.parent / "alembic.ini"

_scheduler = BackgroundScheduler()


def _run_scraper():
    from app.services.news_scraper import scrape
    with SessionLocal() as db:
        n = scrape(db)
        if n:
            print(f"[news] +{n} new items", flush=True)


def _run_migrations():
    from alembic.config import Config
    from alembic import command

    alembic_cfg = Config(str(_ALEMBIC_INI))

    # If tables exist but alembic_version doesn't (pre-alembic local SQLite),
    # stamp as current rather than trying to re-create everything.
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

    # Scrape immediately on startup, then every 6 hours
    _scheduler.add_job(_run_scraper, "interval", hours=6, next_run_time=datetime.utcnow())
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
app.include_router(admin_router.router)


@app.get("/health")
def health():
    return {"status": "ok"}
