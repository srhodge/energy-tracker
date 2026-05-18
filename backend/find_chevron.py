import sys; sys.path.insert(0, ".")
from app.config import settings
from sqlalchemy import create_engine, text
e = create_engine(settings.database_url)
with e.connect() as c:
    rows = c.execute(text(
        "SELECT id, name, ticker, country, sub_sector, revenue_ttm, data_enrichment_tier "
        "FROM companies WHERE name ILIKE '%chevron%' ORDER BY id"
    )).fetchall()
    for r in rows:
        print(r)
