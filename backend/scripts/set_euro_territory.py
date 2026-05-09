# Run against production: ensure backend/.env contains the public
# DATABASE_URL from Railway (turntable.proxy.rlwy.net) not the internal one.
# Then simply run: python scripts/set_euro_territory.py

import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, update as sa_update, or_
from app.config import settings
from app.database import SessionLocal, engine
from app.models import Company

if not settings.database_url.startswith("postgresql"):
    print("ERROR: This script requires production Postgres.")
    print("Update backend/.env with the public DATABASE_URL from Railway.")
    sys.exit(1)

EURO_COUNTRIES = {
    "United Kingdom", "Norway", "Germany", "France", "Belgium", "Italy",
    "Switzerland", "Greece", "Netherlands", "Spain", "Sweden", "Poland",
    "Portugal", "Denmark", "Finland", "Austria", "Hungary", "Czech Republic",
    "Romania", "Turkey", "Luxembourg", "Monaco", "Cyprus", "Ireland", "Bermuda",
}

STOLA_NAME_PATTERNS = [
    "Noble Corp",
    "TechnipFMC",
    "Technip Energies",
    "Covestro",
    "Evonik Industries",
    "Subsea 7",
    "Transocean",
]


def main():
    print(f"Connected to: {str(engine.url)[:60]}...")
    print()

    with SessionLocal() as db:
        # ── Fetch all candidates: European + Russia + Bermuda, no territory ──────
        all_candidates = db.execute(
            select(Company.id, Company.name, Company.ticker, Company.country, Company.wwt_territory)
            .where(
                Company.country.in_(EURO_COUNTRIES | {"Russia"}),
                (Company.wwt_territory.is_(None)) | (Company.wwt_territory == "")
            )
            .order_by(Company.country, Company.name)
        ).all()

        # ── Split into three groups ───────────────────────────────────────────────
        def is_stola(r):
            name_lower = (r.name or "").lower()
            return any(p.lower() in name_lower for p in STOLA_NAME_PATTERNS)

        stola_rows  = [r for r in all_candidates if is_stola(r)]
        stola_ids   = {r.id for r in stola_rows}

        russia_rows = [r for r in all_candidates if r.country == "Russia" and r.id not in stola_ids]
        russia_ids  = {r.id for r in russia_rows}

        euro_rows   = [r for r in all_candidates if r.id not in stola_ids and r.id not in russia_ids]

        # ── Also count already-assigned companies in these countries ──────────────
        already_assigned = db.execute(
            select(Company.id)
            .where(
                Company.country.in_(EURO_COUNTRIES | {"Russia"}),
                Company.wwt_territory.isnot(None),
                Company.wwt_territory != "",
            )
        ).all()

        col = "{:<50} {:<12} {:<25} {}"

        # ── Preview STOLA ─────────────────────────────────────────────────────────
        print(f"STOLA assignments ({len(stola_rows)} companies):")
        print("-" * 110)
        for r in stola_rows:
            print("  " + col.format(
                (r.name or "")[:49], r.ticker or "-", r.country or "-",
                f"{r.wwt_territory or '(null)'} -> STOLA"
            ))

        # ── Preview RUSSIA ────────────────────────────────────────────────────────
        print(f"\nRUSSIA assignments ({len(russia_rows)} companies):")
        print("-" * 110)
        for r in russia_rows:
            print("  " + col.format(
                (r.name or "")[:49], r.ticker or "-", r.country or "-",
                f"{r.wwt_territory or '(null)'} -> RUSSIA"
            ))

        # ── Preview EURO ──────────────────────────────────────────────────────────
        print(f"\nEURO assignments ({len(euro_rows)} companies):")
        print("-" * 110)
        current_country = None
        for r in euro_rows:
            if r.country != current_country:
                if current_country is not None:
                    print()
                current_country = r.country
                print(f"  [{r.country}]")
            print("  " + col.format(
                (r.name or "")[:49], r.ticker or "-", r.country or "-",
                f"{r.wwt_territory or '(null)'} -> EURO"
            ))

        print(f"\nAlready assigned — no change: {len(already_assigned)} companies")
        print()

        # ── Run all three UPDATEs ─────────────────────────────────────────────────
        if stola_rows:
            db.execute(
                sa_update(Company)
                .where(Company.id.in_(list(stola_ids)))
                .values(wwt_territory="STOLA")
            )
        if russia_rows:
            db.execute(
                sa_update(Company)
                .where(Company.id.in_(list(russia_ids)))
                .values(wwt_territory="RUSSIA")
            )
        if euro_rows:
            db.execute(
                sa_update(Company)
                .where(Company.id.in_([r.id for r in euro_rows]))
                .values(wwt_territory="EURO")
            )
        db.commit()

        # ── Confirmation ──────────────────────────────────────────────────────────
        print(f"Updated {len(euro_rows)} companies to EURO")
        print(f"Updated {len(russia_rows)} companies to RUSSIA")
        print(f"Updated {len(stola_rows)} companies to STOLA")
        print(f"Already assigned — no change: {len(already_assigned)} companies")


if __name__ == "__main__":
    main()
