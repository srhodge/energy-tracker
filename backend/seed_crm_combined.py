# Reads three Salesforce XLS exports, combines them, deduplicates on
# (opportunity_name, account_name, close_date), then truncates and reloads
# crm_accounts and crm_opportunities in production Postgres.
# Run from backend/: python seed_crm_combined.py

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
from sqlalchemy import (
    Column, Integer, String, Float, Date, Text, ForeignKey,
    create_engine, text
)
from sqlalchemy.orm import declarative_base, Session

from app.config import settings

if not settings.database_url.startswith("postgresql"):
    print("ERROR: This script requires production Postgres.")
    print("Update backend/.env with the public DATABASE_URL from Railway.")
    sys.exit(1)

XLS_FILES = [
    r"C:\Users\sfsal\Downloads\report1778359099779.xls",
    r"C:\Users\sfsal\Downloads\report1778360280346.xls",
    r"C:\Users\sfsal\Downloads\report1778365957341.xls",
]

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

# ── Load and combine files ────────────────────────────────────────────────────

frames = []
for path in XLS_FILES:
    df = pd.read_html(path)[0]
    print(f"  {Path(path).name}: {len(df)} rows")
    frames.append(df)

combined = pd.concat(frames, ignore_index=True)
total_before = len(combined)
print(f"\nCombined total:      {total_before} rows")

combined = combined.drop_duplicates(
    subset=["Opportunity Name", "Account Name", "Close Date"]
)
total_after = len(combined)
removed = total_before - total_after
print(f"Duplicates removed:  {removed}")
print(f"Rows after dedup:    {total_after}")

# ── Helpers ───────────────────────────────────────────────────────────────────

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

# ── Recreate tables ───────────────────────────────────────────────────────────

engine = create_engine(settings.database_url)

with engine.begin() as conn:
    conn.execute(text("DROP TABLE IF EXISTS crm_opportunities CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS crm_accounts CASCADE"))
Base.metadata.create_all(bind=engine)
print("\nTables dropped and recreated.")

# ── Seed accounts ─────────────────────────────────────────────────────────────

account_names = sorted({str(n).strip() for n in combined["Account Name"].dropna() if str(n).strip()})

with Session(engine) as db:
    db.execute(
        CrmAccount.__table__.insert(),
        [{"name": n} for n in account_names]
    )
    db.commit()

    rows = db.execute(text("SELECT id, name FROM crm_accounts")).fetchall()
    account_id_map = {r[1]: r[0] for r in rows}

print(f"Accounts inserted:   {len(account_names)}")

# ── Seed opportunities ────────────────────────────────────────────────────────

records = []
for _, row in combined.iterrows():
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

with Session(engine) as db:
    db.execute(CrmOpportunity.__table__.insert(), records)
    db.commit()

print(f"Opportunities inserted: {len(records)}")
print(f"\nDone.")
print(f"  crm_accounts:      {len(account_names)} rows")
print(f"  crm_opportunities: {len(records)} rows")
