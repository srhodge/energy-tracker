"""
Migration: set wwt_territory = 'MENA' for all Middle-East companies.

Run against production:
    $env:DATABASE_URL="postgresql://..." ; python scripts/set_mena_territory.py

Or put DATABASE_URL in backend/.env and run:
    python scripts/set_mena_territory.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, update
from app.database import SessionLocal, engine
from app.models import Company

MENA_COUNTRIES = {
    "Saudi Arabia",
    "United Arab Emirates",
    "UAE",
    "Qatar",
    "Kuwait",
    "Bahrain",
    "Oman",
    "Iraq",
    "Iran",
    "Jordan",
    "Lebanon",
    "Syria",
    "Yemen",
    "Israel",
    "Palestine",
    "Egypt",
}

def main():
    db_url = str(engine.url)
    if "sqlite" in db_url:
        print("ERROR: Connected to local SQLite, not production Postgres.")
        print("Set DATABASE_URL to the Railway connection string and re-run.")
        print(f"  Current URL: {db_url}")
        sys.exit(1)

    print(f"Connected to: {db_url[:60]}...")
    print()

    with SessionLocal() as db:
        # ── 1. Current distinct territory values ──────────────────────────────
        rows = db.execute(
            select(Company.wwt_territory)
            .where(Company.wwt_territory.isnot(None))
            .distinct()
            .order_by(Company.wwt_territory)
        ).all()
        print("Current territory values in database:")
        for (t,) in rows:
            print(f"  {t}")
        print()

        # ── 2. All companies whose country is in the MENA list ────────────────
        candidates = db.execute(
            select(Company.id, Company.name, Company.ticker, Company.country, Company.wwt_territory)
            .where(Company.country.in_(MENA_COUNTRIES))
            .order_by(Company.country, Company.name)
        ).all()

        if not candidates:
            print("No companies found matching MENA country list.")
            return

        # ── 3. Split into needs-update vs already-correct ─────────────────────
        to_update = [r for r in candidates if r.wwt_territory != "MENA"]
        already_mena = [r for r in candidates if r.wwt_territory == "MENA"]

        col = "{:<45} {:<10} {:<25} {}"
        header = col.format("Company", "Ticker", "Country", "Territory -> MENA")
        print(header)
        print("-" * 110)

        if to_update:
            print(f"\n  Will be updated ({len(to_update)}):")
            for r in to_update:
                print("  " + col.format(
                    r.name[:44], r.ticker or "—", r.country or "—",
                    f"{r.wwt_territory or '(null)'} → MENA"
                ))

        if already_mena:
            print(f"\n  Already MENA — no change ({len(already_mena)}):")
            for r in already_mena:
                print("  " + col.format(
                    r.name[:44], r.ticker or "—", r.country or "—", "MENA (unchanged)"
                ))

        # ── 4. Counts and update ──────────────────────────────────────────────
        print(f"\nWill update : {len(to_update)}")
        print(f"Already MENA: {len(already_mena)}")

        if not to_update:
            print("\nNothing to do.")
            return

        ids_to_update = [r.id for r in to_update]
        db.execute(
            update(Company)
            .where(Company.id.in_(ids_to_update))
            .values(wwt_territory="MENA")
        )
        db.commit()

        # ── 5. Confirmation ───────────────────────────────────────────────────
        print(f"\nUpdated {len(to_update)} companies to MENA")
        print(f"{len(already_mena)} companies were already set to MENA — no change")

if __name__ == "__main__":
    main()
