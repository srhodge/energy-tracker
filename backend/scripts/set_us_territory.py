# Run against production: ensure backend/.env contains the public
# DATABASE_URL from Railway (turntable.proxy.rlwy.net) not the internal one.
# Then simply run: python scripts/set_us_territory.py

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

import yfinance as yf

TICKERS = [
    "AMPY", "BATL", "BRY", "CEIN", "CLNE", "CAPL", "DEC.L", "DTI", "DRQ",
    "EPSN", "FET", "GNE", "GRNT", "GIFI", "HUSA", "KLXE", "KGEI", "MMLP",
    "NESR", "NCSM", "NR", "NGL", "NINE", "OIS", "OPAL", "OSG", "PED", "PRT",
    "PHX", "PROP", "PNRG", "PFIE", "PUMP", "RNGR", "RGCO", "REPX", "REI",
    "SD", "SND", "SOI", "SLNG", "SGU", "SMLP", "TTI", "TPET", "TXO", "UTL",
    "USDP", "EGY", "VTNR", "VTS", "VIVK", "WTI", "ZNOG",
]

DFW_CITIES = {
    "dallas", "fort worth", "irving", "plano", "arlington", "frisco",
    "mckinney", "southlake", "grapevine", "addison", "flower mound",
}

EAST_STATES = {"AL", "NH", "NJ", "NY", "PA", "VA"}


def assign_territory(city: str, state: str) -> str:
    c = (city or "").strip().lower()
    s = (state or "").strip().upper()

    if s == "TX":
        return "NTOLA" if c in DFW_CITIES else "STOLA"
    if s == "OK":
        return "NTOLA"
    if s == "CO":
        return "DENVER"
    if s == "CA":
        return "WEST"
    if s in EAST_STATES:
        return "EAST"
    return "UNASSIGNED"


def main():
    print(f"Connected to: {str(engine.url)[:60]}...")
    print()

    # ── Pull company names from DB ────────────────────────────────────────────
    db = SessionLocal()
    name_rows = db.execute(
        select(Company.id, Company.ticker, Company.name)
        .where(Company.ticker.in_(TICKERS))
    ).all()
    db.close()

    id_map   = {r.ticker: r.id   for r in name_rows}
    name_map = {r.ticker: r.name for r in name_rows}

    # ── yfinance lookup ───────────────────────────────────────────────────────
    print(f"Looking up {len(TICKERS)} tickers via yfinance...")
    records = []
    for i, ticker in enumerate(TICKERS, 1):
        try:
            info  = yf.Ticker(ticker).info or {}
            city  = info.get("city")  or "Unknown"
            state = info.get("state") or "Unknown"
        except Exception:
            city, state = "Unknown", "Unknown"
        territory = assign_territory(city, state)
        name      = name_map.get(ticker, ticker)
        cid       = id_map.get(ticker)
        print(f"  [{i:>2}/{len(TICKERS)}] {ticker:<8} {city}, {state}  ->  {territory}")
        records.append((cid, name, ticker, city, state, territory))

    # ── Split into assigned vs unassigned ─────────────────────────────────────
    assigned   = [r for r in records if r[5] != "UNASSIGNED" and r[0] is not None]
    unassigned = [r for r in records if r[5] == "UNASSIGNED" or r[0] is None]

    col = "{:<48} {:<10} {:<22} {:<8} {}"

    # ── Preview by territory ──────────────────────────────────────────────────
    from collections import defaultdict, Counter
    by_terr = defaultdict(list)
    for r in assigned:
        by_terr[r[5]].append(r)

    print()
    for terr in ["NTOLA", "STOLA", "DENVER", "WEST", "EAST"]:
        group = by_terr.get(terr, [])
        print(f"{terr} ({len(group)} companies):")
        print("-" * 100)
        for cid, name, ticker, city, state, t in group:
            print("  " + col.format(name[:47], ticker, city, state, f"-> {t}"))
        print()

    if unassigned:
        print(f"UNASSIGNED — needs manual review ({len(unassigned)} companies):")
        print("-" * 100)
        for cid, name, ticker, city, state, t in unassigned:
            reason = "no DB id" if cid is None else f"{city}, {state}"
            print(f"  {col.format(name[:47], ticker, city, state, '-> UNASSIGNED')}")
        print()

    # ── Run UPDATE ────────────────────────────────────────────────────────────
    counts = Counter(r[5] for r in assigned)
    with SessionLocal() as db:
        for terr in ["NTOLA", "STOLA", "DENVER", "WEST", "EAST"]:
            ids = [r[0] for r in assigned if r[5] == terr]
            if ids:
                db.execute(
                    sa_update(Company)
                    .where(Company.id.in_(ids))
                    .values(wwt_territory=terr)
                )
        db.commit()

    # ── Confirmation ──────────────────────────────────────────────────────────
    print("=" * 60)
    for terr in ["NTOLA", "STOLA", "DENVER", "WEST", "EAST"]:
        print(f"  {terr}:       {counts.get(terr, 0):>3} companies updated")
    print(f"  UNASSIGNED:  {len(unassigned):>3} companies (need manual review)")
    print("=" * 60)


if __name__ == "__main__":
    main()
