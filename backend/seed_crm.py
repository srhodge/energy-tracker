# Reads C:\Users\sfsal\Downloads\report1778360280346.xls and seeds
# crm_accounts + crm_opportunities tables in production Postgres.
# Run from backend/: python seed_crm.py

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
from datetime import date
from sqlalchemy import (
    Column, Integer, String, Float, Date, Text, ForeignKey,
    create_engine, inspect as sa_inspect, text
)
from sqlalchemy.orm import declarative_base, Session

from app.config import settings

if not settings.database_url.startswith("postgresql"):
    print("ERROR: This script requires production Postgres.")
    print("Update backend/.env with the public DATABASE_URL from Railway.")
    sys.exit(1)

XLS_PATH = r"C:\Users\sfsal\Downloads\report1778360280346.xls"

# ── Models ────────────────────────────────────────────────────────────────────

Base = declarative_base()

class CrmAccount(Base):
    __tablename__ = "crm_accounts"
    id   = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(500), nullable=False, unique=True)

class CrmOpportunity(Base):
    __tablename__ = "crm_opportunities"
    id                 = Column(Integer, primary_key=True, autoincrement=True)
    account_id         = Column(Integer, ForeignKey("crm_accounts.id"), nullable=True)
    account_name       = Column(String(500))
    owner_role         = Column(String(200))
    opportunity_owner  = Column(String(200))
    opportunity_name   = Column(Text)
    stage              = Column(String(200))
    fiscal_period      = Column(String(50))
    amount             = Column(Float)
    probability        = Column(Float)
    age                = Column(Float)
    close_date         = Column(Date)
    created_date       = Column(Date)
    next_step          = Column(Text)
    lead_source        = Column(String(200))
    opp_type           = Column(String(200))

# ── Setup ─────────────────────────────────────────────────────────────────────

engine = create_engine(settings.database_url)

# Drop and recreate to ensure clean schema
with engine.begin() as conn:
    conn.execute(text("DROP TABLE IF EXISTS crm_opportunities CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS crm_accounts CASCADE"))
Base.metadata.create_all(bind=engine)
print("Tables created: crm_accounts, crm_opportunities")

# ── Load Excel ────────────────────────────────────────────────────────────────

print(f"Reading {XLS_PATH} ...")
df = pd.read_html(XLS_PATH)[0]
print(f"Loaded {len(df)} rows, {len(df.columns)} columns")

def parse_date(val):
    if pd.isna(val):
        return None
    try:
        return pd.to_datetime(val).date()
    except Exception:
        return None

def clean(val):
    if pd.isna(val):
        return None
    s = str(val).strip()
    return s if s else None

# ── Seed accounts ─────────────────────────────────────────────────────────────

account_names = sorted({str(n).strip() for n in df["Account Name"].dropna() if str(n).strip()})
print(f"Unique accounts: {len(account_names)}")

with Session(engine) as db:
    # Check which accounts already exist
    existing = {r[0] for r in db.execute(text("SELECT name FROM crm_accounts")).fetchall()}
    new_accounts = [n for n in account_names if n not in existing]

    if new_accounts:
        db.execute(
            CrmAccount.__table__.insert(),
            [{"name": n} for n in new_accounts]
        )
        db.commit()
        print(f"Inserted {len(new_accounts)} accounts ({len(existing)} already existed)")
    else:
        print(f"All {len(existing)} accounts already exist — skipping")

    # Build name→id map
    rows = db.execute(text("SELECT id, name FROM crm_accounts")).fetchall()
    account_id_map = {r[1]: r[0] for r in rows}

# ── Seed opportunities ────────────────────────────────────────────────────────

with Session(engine) as db:
    existing_count = db.execute(text("SELECT COUNT(*) FROM crm_opportunities")).scalar()
    if existing_count > 0:
        print(f"crm_opportunities already has {existing_count} rows — truncating and re-seeding")
        db.execute(text("TRUNCATE TABLE crm_opportunities RESTART IDENTITY CASCADE"))
        db.commit()

    records = []
    for _, row in df.iterrows():
        acct_name = clean(row["Account Name"])
        records.append({
            "account_id":        account_id_map.get(acct_name) if acct_name else None,
            "account_name":      acct_name,
            "owner_role":        clean(row["Owner Role"]),
            "opportunity_owner": clean(row["Opportunity Owner"]),
            "opportunity_name":  clean(row["Opportunity Name"]),
            "stage":             clean(row["Stage"]),
            "fiscal_period":     clean(row["Fiscal Period"]),
            "amount":            None if pd.isna(row["Amount"]) else float(row["Amount"]),
            "probability":       None if pd.isna(row["Probability (%)"]) else float(row["Probability (%)"]),
            "age":               None if pd.isna(row["Age"]) else float(row["Age"]),
            "close_date":        parse_date(row["Close Date"]),
            "created_date":      parse_date(row["Created Date"]),
            "next_step":         clean(row["Next Step"]),
            "lead_source":       clean(row["Lead Source"]),
            "opp_type":          clean(row["Type"]),
        })

    db.execute(CrmOpportunity.__table__.insert(), records)
    db.commit()
    print(f"Inserted {len(records)} opportunities")

print("\nDone.")
print(f"  crm_accounts:      {len(account_id_map)} rows")
print(f"  crm_opportunities: {len(records)} rows")
