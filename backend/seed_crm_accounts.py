# Inserts missing CRM account names into crm_accounts table.
# Run from backend/: python seed_crm_accounts.py

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select, text
from sqlalchemy.orm import Session
from app.config import settings
from app.database import engine
from app.models import CrmAccount

if not settings.database_url.startswith("postgresql"):
    print("ERROR: This script requires production Postgres.")
    print("Update backend/.env with the public DATABASE_URL from Railway.")
    sys.exit(1)

ACCOUNTS = [
    "American Air Liquide",
    "American Intelligence & Power Corporation (AIP Corp)",
    "APA Corporation",
    "Apache Corporation",
    "Baker Hughes Inc",
    "Barrett Steel Energy Product Inc",
    "Buckeye Partners",
    "Chevron Corporation",
    "Chord Energy",
    "Cognomotiv",
    "ConocoPhillips",
    "Continental Resources",
    "Coterra Energy",
    "CVR Energy",
    "Diamondback Energy Inc",
    "Direct Energy",
    "Engie North America",
    "ENI Petroleum",
    "EnLink Midstream LLC",
    "EOG Resources",
    "Exterran Energy Holdings",
    "ExxonMobil Global Services Company",
    "Fermi America",
    "Fidelis New Energy",
    "Fluor Corporation",
    "G2 Integrated Solutions LLC",
    "Ion Geophysical Corporation",
    "Mears Group Inc",
    "Midcoast Energy Resources Inc",
    "MODEC International",
    "MRC Global",
    "Nabors Industries Ltd",
    "NCS Multistage",
    "Noble Corporation",
    "Noble Energy Inc",
    "NuStar Energy",
    "Oceaneering International",
    "Opportune LLP",
    "Oxy",
    "Par Pacific Holdings",
    "Parker Wellbore",
    "Parsley Energy Inc",
    "Pedernales Electric Cooperative Inc",
    "Pemex",
    "Petrobras America Inc",
    "Phillips 66",
    "Plains All-American Pipeline LP",
    "PSC Industrial Services Inc",
    "Quanta Services",
    "Sasol",
    "Schlumberger Ltd",
    "Seadrill Limited",
    "Stratum Reservoir",
    "Tidewater Inc",
    "The Williams Companies Inc",
    "Tesoro Petroleum Companies Inc",
    "Ranger Energy",
    "Motiva Enterprises LLC",
    "Halliburton",
    "NSCALE OPERATIONS UK LIMITED",
    "Worley",
    "New Era Energy & Digital Inc",
    "Terraflow Energy",
    "Independence Power Holdings",
    "Tallgrass Energy",
    "Baker Hughes",
    "Golden Pass LNG",
    "TechnipFMC",
    "OGE Energy",
    "Enbridge",
    "Helmerich & Payne",
    "Mitsubishi Heavy Industries Ltd",
    "Armada.ai",
    "CLEAResult",
]

with Session(engine) as db:
    existing = {
        r[0] for r in db.execute(text("SELECT name FROM crm_accounts")).fetchall()
    }

    to_insert = [n for n in ACCOUNTS if n not in existing]

    if to_insert:
        db.add_all([CrmAccount(name=n) for n in to_insert])
        db.commit()

    print(f"Already in DB:   {len(existing)}")
    print(f"Newly inserted:  {len(to_insert)}")
    print(f"Total accounts:  {len(existing) + len(to_insert)}")

    if to_insert:
        print("\nInserted:")
        for n in sorted(to_insert):
            print(f"  + {n}")
