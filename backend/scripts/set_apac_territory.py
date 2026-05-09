# Run against production: ensure backend/.env contains the public
# DATABASE_URL from Railway (turntable.proxy.rlwy.net) not the internal one.
# Then simply run: python scripts/set_apac_territory.py

import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, update as sa_update
from app.config import settings
from app.database import SessionLocal, engine
from app.models import Company

if not settings.database_url.startswith("postgresql"):
    print("ERROR: This script requires production Postgres.")
    print("Update backend/.env with the public DATABASE_URL from Railway.")
    sys.exit(1)

APAC_COUNTRIES = {
    "China",
    "Japan",
    "South Korea",
    "Korea",
    "Australia",
    "New Zealand",
    "India",
    "Indonesia",
    "Malaysia",
    "Thailand",
    "Vietnam",
    "Philippines",
    "Singapore",
    "Taiwan",
    "Hong Kong",
    "Pakistan",
    "Bangladesh",
    "Sri Lanka",
    "Myanmar",
    "Cambodia",
    "Laos",
    "Mongolia",
    "Papua New Guinea",
    "Fiji",
}

def main():
    print(f"Connected to: {str(engine.url)[:60]}...")
    print()

    with SessionLocal() as db:
        # ── 1. All APAC companies ─────────────────────────────────────────────
        candidates = db.execute(
            select(Company.id, Company.name, Company.ticker, Company.country, Company.wwt_territory)
            .where(Company.country.in_(APAC_COUNTRIES))
            .order_by(Company.country, Company.name)
        ).all()

        if not candidates:
            print("No companies found matching APAC country list.")
            return

        # ── 2. Split into needs-update vs already-correct ─────────────────────
        # Explicit exclusions: tickers whose territory must not be overwritten
        EXCLUDE_TICKERS = {"WOR.AX"}  # Worley — intentionally tagged STOLA

        to_update    = [r for r in candidates if r.wwt_territory != "APAC" and r.ticker not in EXCLUDE_TICKERS]
        already_set  = [r for r in candidates if r.wwt_territory == "APAC"]
        skipped      = [r for r in candidates if r.ticker in EXCLUDE_TICKERS]

        col = "{:<50} {:<12} {:<25} {}"
        header = col.format("Company", "Ticker", "Country", "Territory -> APAC")
        print(header)
        print("-" * 120)

        if to_update:
            print(f"\n  Will be updated ({len(to_update)}):")
            for r in to_update:
                print("  " + col.format(
                    r.name[:49], r.ticker or "-", r.country or "-",
                    f"{r.wwt_territory or '(null)'} -> APAC"
                ))

        if already_set:
            print(f"\n  Already APAC -- no change ({len(already_set)}):")
            for r in already_set:
                print("  " + col.format(
                    r.name[:49], r.ticker or "-", r.country or "-", "APAC (unchanged)"
                ))

        if skipped:
            print(f"\n  Skipped -- explicit exclusion ({len(skipped)}):")
            for r in skipped:
                print("  " + col.format(
                    r.name[:49], r.ticker or "-", r.country or "-",
                    f"{r.wwt_territory or '(null)'} (kept)"
                ))

        # ── 3. Counts and update ──────────────────────────────────────────────
        print(f"\nWill update : {len(to_update)}")
        print(f"Already APAC: {len(already_set)}")
        print(f"Skipped     : {len(skipped)}")

        if not to_update:
            print("\nNothing to do.")
            return

        db.execute(
            sa_update(Company)
            .where(Company.id.in_([r.id for r in to_update]))
            .values(wwt_territory="APAC")
        )
        db.commit()

        # ── 4. Confirmation ───────────────────────────────────────────────────
        print(f"\nUpdated {len(to_update)} companies to APAC")
        print(f"{len(already_set)} companies were already set to APAC -- no change")

if __name__ == "__main__":
    main()
