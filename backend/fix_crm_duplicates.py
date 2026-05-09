# Merges duplicate crm_accounts by re-pointing opportunities to the canonical
# record then deleting the duplicate.
# Run from backend/: python fix_crm_duplicates.py

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select, update, delete
from sqlalchemy.orm import Session
from app.config import settings
from app.database import engine
from app.models import CrmAccount, CrmOpportunity

if not settings.database_url.startswith("postgresql"):
    print("ERROR: This script requires production Postgres.")
    sys.exit(1)

# (keep, discard) — opportunities on 'discard' get re-pointed to 'keep'
MERGES = [
    ("Schlumberger Ltd.",               "Schlumberger Ltd"),
    ("Barrett Steel Energy Product Inc.","Barrett Steel Energy Product Inc"),
    ("Baker Hughes Inc",                 "Baker Hughes"),
    ("Tidewater Inc.",                   "Tidewater Inc"),
    ("Noble Energy Inc.",                "Noble Energy Inc"),
]

with Session(engine) as db:
    for keep_name, discard_name in MERGES:
        keep    = db.scalar(select(CrmAccount).where(CrmAccount.name == keep_name))
        discard = db.scalar(select(CrmAccount).where(CrmAccount.name == discard_name))

        if not keep:
            print(f"  SKIP — canonical not found: '{keep_name}'")
            continue
        if not discard:
            print(f"  SKIP — duplicate not found: '{discard_name}'")
            continue

        moved = db.execute(
            update(CrmOpportunity)
            .where(CrmOpportunity.account_id == discard.id)
            .values(account_id=keep.id, account_name=keep.name)
        ).rowcount

        db.delete(discard)
        print(f"  '{discard_name}' -> '{keep_name}'  ({moved} opps re-pointed, record deleted)")

    db.commit()

    total = db.scalar(select(CrmAccount).with_only_columns(
        __import__("sqlalchemy").func.count(CrmAccount.id)
    ))
    print(f"\nDone. crm_accounts now has {total} rows.")
