from app.database import SessionLocal
from sqlalchemy import text

with SessionLocal() as db:
    rows = db.execute(text("""
        SELECT name, ticker, country, wwt_territory, energy_category, energy_maturity
        FROM companies
        WHERE wwt_model IS NULL
        ORDER BY country, name
        LIMIT 60
    """)).fetchall()
    print(f"{'Name':<45} {'Ticker':<8} {'Country':<20} {'Territory':<10} {'Category':<12} Maturity")
    print("-" * 115)
    for r in rows:
        name = (r[0] or "").encode("ascii", "replace").decode()
        print(f"{name:<45} {str(r[1] or ''):<8} {str(r[2] or ''):<20} {str(r[3] or ''):<10} {str(r[4] or ''):<12} {str(r[5] or '')}")

print()

with SessionLocal() as db:
    country_counts = db.execute(text("""
        SELECT country, COUNT(*) as cnt
        FROM companies
        WHERE wwt_model IS NULL
        GROUP BY country
        ORDER BY cnt DESC
        LIMIT 15
    """)).fetchall()
    print("Country breakdown (NULL model):")
    for r in country_counts:
        print(f"  {str(r[0] or 'NULL'):<25} {r[1]}")
