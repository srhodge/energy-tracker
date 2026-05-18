import sys
sys.path.insert(0, ".")
from app.config import settings
from sqlalchemy import create_engine

engine = create_engine(settings.database_url)
raw = engine.raw_connection()

try:
    cur = raw.cursor()

    # Step 1: Clear all fuzzy-match columns from crm_accounts
    cur.execute("""
        UPDATE crm_accounts
           SET energy_company_id = NULL,
               match_score       = NULL,
               match_method      = NULL,
               updated_at        = NOW()
    """)
    print(f"Cleared match data from {cur.rowcount} crm_accounts rows")

    # Step 2: Null out tier 1 on any companies that had it set
    cur.execute("""
        UPDATE companies SET data_enrichment_tier = NULL
         WHERE data_enrichment_tier = 1
    """)
    print(f"Cleared tier 1 from {cur.rowcount} companies")

    # Step 3: Set tier 1 for companies whose name matches a crm_account name
    # Uses case-insensitive exact match — no FK, just name reference
    cur.execute("""
        UPDATE companies
           SET data_enrichment_tier = 1
         WHERE data_enrichment_tier IS NULL
           AND LOWER(name) IN (SELECT LOWER(name) FROM crm_accounts)
    """)
    tier1_by_name = cur.rowcount
    print(f"Set tier 1 on {tier1_by_name} companies matched by name from crm_accounts")

    # Step 4: Re-apply tiers 2–6 for remaining companies
    cur.execute("""
        UPDATE companies SET data_enrichment_tier = 2
         WHERE data_enrichment_tier IS NULL
           AND country IN ('United States', 'USA', 'US')
    """)
    print(f"  tier 2 (US):     {cur.rowcount}")

    cur.execute("""
        UPDATE companies SET data_enrichment_tier = 3
         WHERE data_enrichment_tier IS NULL
           AND country IN ('Canada')
    """)
    print(f"  tier 3 (Canada): {cur.rowcount}")

    cur.execute("""
        UPDATE companies SET data_enrichment_tier = 4
         WHERE data_enrichment_tier IS NULL
           AND country IN ('United Kingdom','Netherlands','Norway','France','Germany','Italy',
                           'Spain','Denmark','Belgium','Sweden','Finland','Austria','Switzerland',
                           'Portugal','Ireland','Luxembourg')
    """)
    print(f"  tier 4 (Europe): {cur.rowcount}")

    cur.execute("""
        UPDATE companies SET data_enrichment_tier = 5
         WHERE data_enrichment_tier IS NULL
           AND country IN ('Saudi Arabia','UAE','United Arab Emirates','Qatar','Kuwait','Oman',
                           'Bahrain','Iraq','Iran')
    """)
    print(f"  tier 5 (Gulf):   {cur.rowcount}")

    cur.execute("""
        UPDATE companies SET data_enrichment_tier = 6
         WHERE data_enrichment_tier IS NULL
    """)
    print(f"  tier 6 (rest):   {cur.rowcount}")

    raw.commit()
    print("\nCommitted.\n")

    # Summary
    cur.execute("""
        SELECT data_enrichment_tier, COUNT(*)
          FROM companies
         GROUP BY data_enrichment_tier
         ORDER BY data_enrichment_tier
    """)
    print("Tier distribution:")
    for tier, count in cur.fetchall():
        label = {1:"CRM name match", 2:"US", 3:"Canada", 4:"Europe", 5:"Gulf", 6:"Rest"}.get(tier, "?")
        print(f"  Tier {tier} ({label}): {count}")

    # Show which companies got tier 1
    cur.execute("""
        SELECT c.name, c.ticker, c.country
          FROM companies c
         WHERE c.data_enrichment_tier = 1
         ORDER BY c.name
    """)
    rows = cur.fetchall()
    print(f"\nTier 1 companies ({len(rows)}):")
    print(f"  {'Company':<50} {'Ticker':<8} Country")
    print("  " + "-"*75)
    for name, ticker, country in rows:
        print(f"  {name:<50} {ticker or '':<8} {country or ''}")

    # Show crm_accounts with no matching company
    cur.execute("""
        SELECT a.name
          FROM crm_accounts a
         WHERE NOT EXISTS (
             SELECT 1 FROM companies c WHERE LOWER(c.name) = LOWER(a.name)
         )
         ORDER BY a.name
    """)
    no_match = cur.fetchall()
    print(f"\nCRM accounts with no exact company name match ({len(no_match)}):")
    for (name,) in no_match:
        print(f"  - {name}")

except Exception as e:
    raw.rollback()
    print(f"\nERROR — rolled back: {e}")
    raise
finally:
    raw.close()
