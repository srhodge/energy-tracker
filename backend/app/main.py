from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func, text
from apscheduler.schedulers.background import BackgroundScheduler

from app.config import settings
from app.database import engine, SessionLocal
from app.models import Base, Company
from app.routers import companies, events
from app.routers import news as news_router

_SEED_FILE = Path(__file__).parent.parent / "data" / "companies.xlsx"

_scheduler = BackgroundScheduler()


def _run_scraper():
    from app.services.news_scraper import scrape
    with SessionLocal() as db:
        n = scrape(db)
        if n:
            print(f"[news] +{n} new items", flush=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)

    # Add supply_chain_position column on existing DBs that pre-date it
    db_url = settings.database_url
    migration_sql = (
        "ALTER TABLE companies ADD COLUMN IF NOT EXISTS supply_chain_position VARCHAR(50)"
        if ("postgresql" in db_url or "postgres" in db_url)
        else "ALTER TABLE companies ADD COLUMN supply_chain_position VARCHAR(50)"
    )
    with engine.connect() as conn:
        try:
            conn.execute(text(migration_sql))
            conn.commit()
        except Exception:
            pass

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


@app.get("/health")
def health():
    return {"status": "ok"}
