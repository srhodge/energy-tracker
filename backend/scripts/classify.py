# Run against production: ensure backend/.env contains the public
# DATABASE_URL from Railway (turntable.proxy.rlwy.net) not the internal one.
# Then simply run: python scripts/classify.py

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from collections import Counter
from sqlalchemy import select, text
from app.config import settings
from app.database import engine, SessionLocal
from app.models import Base, Company
from app.services.classify_supply_chain import _classify

if not settings.database_url.startswith("postgresql"):
    print("ERROR: This script requires production Postgres.")
    print("Update backend/.env with the public DATABASE_URL from Railway.")
    sys.exit(1)

Base.metadata.create_all(bind=engine)

with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE companies ADD COLUMN supply_chain_position VARCHAR(50)"))
        conn.commit()
        print("Column added.")
    except Exception as e:
        print(f"Column already exists ({type(e).__name__})")

with SessionLocal() as db:
    companies = list(db.scalars(select(Company)).all())
    counts: Counter = Counter()
    for c in companies:
        pos = _classify(c)
        c.supply_chain_position = pos
        counts[pos] += 1
    db.commit()

print(f"\nClassified {sum(counts.values())} companies:")
for pos, n in sorted(counts.items()):
    print(f"  {pos:<25} {n:>4}")
