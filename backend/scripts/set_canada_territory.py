# Run against production: ensure backend/.env contains the public
# DATABASE_URL from Railway (turntable.proxy.rlwy.net) not the internal one.
# Then simply run: python scripts/set_canada_territory.py

import sys
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

def main():
    print(f"Connected to: {str(engine.url)[:60]}...")
    print()

    with SessionLocal() as db:
        # ── 1. All Canadian companies ─────────────────────────────────────────
        candidates = db.execute(
            select(Company.id, Company.name, Company.ticker, Company.country, Company.wwt_territory)
            .where(Company.country == "Canada")
            .order_by(Company.name)
        ).all()

        if not candidates:
            print("No companies found with country = 'Canada'.")
            return

        # ── 2. Split into needs-update vs already-correct ─────────────────────
        to_update    = [r for r in candidates if r.wwt_territory != "CANADA"]
        already_set  = [r for r in candidates if r.wwt_territory == "CANADA"]

        col = "{:<50} {:<12} {:<10} {}"
        header = col.format("Company", "Ticker", "Country", "Territory -> CANADA")
        print(header)
        print("-" * 115)

        if to_update:
            print(f"\n  Will be updated ({len(to_update)}):")
            for r in to_update:
                print("  " + col.format(
                    r.name[:49], r.ticker or "-", r.country or "-",
                    f"{r.wwt_territory or '(null)'} -> CANADA"
                ))

        if already_set:
            print(f"\n  Already CANADA -- no change ({len(already_set)}):")
            for r in already_set:
                print("  " + col.format(
                    r.name[:49], r.ticker or "-", r.country or "-", "CANADA (unchanged)"
                ))

        # ── 3. Counts and update ──────────────────────────────────────────────
        print(f"\nWill update : {len(to_update)}")
        print(f"Already CANADA: {len(already_set)}")

        if not to_update:
            print("\nNothing to do.")
            return

        db.execute(
            sa_update(Company)
            .where(Company.id.in_([r.id for r in to_update]))
            .values(wwt_territory="CANADA")
        )
        db.commit()

        # ── 4. Confirmation ───────────────────────────────────────────────────
        print(f"\nUpdated {len(to_update)} companies to CANADA")
        print(f"{len(already_set)} companies were already set to CANADA -- no change")

if __name__ == "__main__":
    main()
