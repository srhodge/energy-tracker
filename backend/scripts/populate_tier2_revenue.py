import psycopg2
import yfinance as yf
import os

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

cur.execute("""
    SELECT id, ticker FROM companies
    WHERE data_enrichment_tier = 2
    AND status = 'Active'
    AND revenue_ttm IS NULL
    AND ticker IS NOT NULL
    ORDER BY id
""")
companies = cur.fetchall()

print(f"Found {len(companies)} Tier 2 companies needing revenue data")

updated = 0
failed = []

for company_id, ticker in companies:
    try:
        info = yf.Ticker(ticker).info
        revenue = info.get('totalRevenue')
        employees = info.get('fullTimeEmployees')
        ebitda = info.get('ebitda')
        gross_profit = info.get('grossProfits')

        if revenue and revenue > 0:
            cur.execute("""
                UPDATE companies
                SET revenue_ttm = %s,
                    employee_count = COALESCE(employee_count, %s),
                    ebitda_ttm = COALESCE(ebitda_ttm, %s),
                    gross_profit_ttm = COALESCE(gross_profit_ttm, %s)
                WHERE id = %s
            """, (revenue, employees, ebitda, gross_profit, company_id))
            updated += 1
            print(f"  Updated {ticker} (id={company_id}): rev=${revenue/1e9:.2f}B")
        else:
            failed.append(f"{ticker} (id={company_id})")
    except Exception as e:
        failed.append(f"{ticker} (id={company_id}): {e}")

conn.commit()
cur.close()
conn.close()

print(f"\nUpdated: {updated}")
print(f"Failed/No data: {len(failed)}")
if failed:
    print("Failed tickers:", failed)
