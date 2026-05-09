# Run against production: ensure backend/.env contains the public
# DATABASE_URL from Railway (turntable.proxy.rlwy.net) not the internal one.
# Then simply run: python scripts/set_mena_territory.py

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, update as sa_update
from app.config import settings
from app.database import SessionLocal, engine
from app.models import Company

if not settings.database_url.startswith("postgresql"):
    print("ERROR: This script requires production Postgres.")
    print("Update backend/.env with the public DATABASE_URL from Railway.")
    sys.exit(1)

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
        to_update   = [r for r in candidates if r.wwt_territory != "MENA"]
        already_mena = [r for r in candidates if r.wwt_territory == "MENA"]

        col = "{:<45} {:<10} {:<25} {}"
        header = col.format("Company", "Ticker", "Country", "Territory -> MENA")
        print(header)
        print("-" * 110)

        if to_update:
            print(f"\n  Will be updated ({len(to_update)}):")
            for r in to_update:
                print("  " + col.format(
                    r.name[:44], r.ticker or "-", r.country or "-",
                    f"{r.wwt_territory or '(null)'} -> MENA"
                ))

        if already_mena:
            print(f"\n  Already MENA -- no change ({len(already_mena)}):")
            for r in already_mena:
                print("  " + col.format(
                    r.name[:44], r.ticker or "-", r.country or "-", "MENA (unchanged)"
                ))

        # ── 4. Counts and update ──────────────────────────────────────────────
        print(f"\nWill update : {len(to_update)}")
        print(f"Already MENA: {len(already_mena)}")

        if not to_update:
            print("\nNothing to do.")
            return

        db.execute(
            sa_update(Company)
            .where(Company.id.in_([r.id for r in to_update]))
            .values(wwt_territory="MENA")
        )
        db.commit()

        # ── 5. Confirmation ───────────────────────────────────────────────────
        print(f"\nUpdated {len(to_update)} companies to MENA")
        print(f"{len(already_mena)} companies were already set to MENA -- no change")

if __name__ == "__main__":
    main()
