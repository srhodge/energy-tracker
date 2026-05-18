import sys; sys.path.insert(0, ".")
from app.config import settings
from sqlalchemy import create_engine, text
e = create_engine(settings.database_url)
with e.connect() as c:
    rows = c.execute(text(
        "SELECT id, name, ticker, country, sub_sector, revenue_ttm, revenue_annual_usd, data_enrichment_tier "
        "FROM companies co "
        "LEFT JOIN LATERAL (SELECT revenue_annual_usd FROM financials f WHERE f.company_id = co.id ORDER BY snapshot_date DESC LIMIT 1) fin ON true "
        "WHERE co.name ILIKE '%exxon%' ORDER BY co.id"
    )).fetchall()
    for r in rows:
        print(r)
