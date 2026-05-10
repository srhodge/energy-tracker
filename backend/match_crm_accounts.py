import sys
sys.path.insert(0, ".")
from app.config import settings
from rapidfuzz import fuzz, process
from sqlalchemy import create_engine

THRESHOLD = 80

engine = create_engine(settings.database_url)
raw = engine.raw_connection()

try:
    cur = raw.cursor()

    # Load companies: id, name (also grab ticker for display)
    cur.execute("SELECT id, name, ticker FROM companies ORDER BY id")
    companies = cur.fetchall()  # [(id, name, ticker), ...]
    company_names = [row[1] for row in companies]
    company_by_name = {row[1]: row for row in companies}

    # Load CRM accounts
    cur.execute("SELECT id, name FROM crm_accounts ORDER BY id")
    accounts = cur.fetchall()  # [(id, name), ...]

    print(f"Matching {len(accounts)} CRM accounts against {len(companies)} companies "
          f"(threshold={THRESHOLD})...\n")

    matched = []
    unmatched = []

    for acct_id, acct_name in accounts:
        result = process.extractOne(
            acct_name,
            company_names,
            scorer=fuzz.token_set_ratio,
            score_cutoff=THRESHOLD,
        )
        if result:
            best_name, score, _ = result
            comp = company_by_name[best_name]
            comp_id, comp_name, comp_ticker = comp
            matched.append((acct_id, acct_name, comp_id, comp_name, comp_ticker, score))
        else:
            unmatched.append((acct_id, acct_name))

    # Apply updates
    print("Applying updates...")
    for acct_id, _, comp_id, _, _, score in matched:
        cur.execute("""
            UPDATE crm_accounts
               SET energy_company_id = %s,
                   match_score       = %s,
                   match_method      = 'token_set_ratio',
                   updated_at        = NOW()
             WHERE id = %s
        """, (comp_id, score, acct_id))

    # Clear stale matches on unmatched rows (idempotent re-runs)
    for acct_id, _ in unmatched:
        cur.execute("""
            UPDATE crm_accounts
               SET energy_company_id = NULL,
                   match_score       = NULL,
                   match_method      = NULL
             WHERE id = %s
        """, (acct_id,))

    # Reset tier 1, then re-apply only to newly matched companies
    cur.execute("""
        UPDATE companies SET data_enrichment_tier = NULL
         WHERE data_enrichment_tier = 1
    """)
    if matched:
        matched_company_ids = list({comp_id for _, _, comp_id, _, _, _ in matched})
        cur.execute("""
            UPDATE companies SET data_enrichment_tier = 1
             WHERE id = ANY(%s)
        """, (matched_company_ids,))

    # Re-apply tiers 2-6 for companies that lost tier 1 but aren't matched
    cur.execute("""
        UPDATE companies SET data_enrichment_tier = 2
         WHERE data_enrichment_tier IS NULL AND country IN ('United States','USA','US')
    """)
    cur.execute("""
        UPDATE companies SET data_enrichment_tier = 3
         WHERE data_enrichment_tier IS NULL AND country IN ('Canada')
    """)
    cur.execute("""
        UPDATE companies SET data_enrichment_tier = 4
         WHERE data_enrichment_tier IS NULL
           AND country IN ('United Kingdom','Netherlands','Norway','France','Germany','Italy',
                           'Spain','Denmark','Belgium','Sweden','Finland','Austria','Switzerland',
                           'Portugal','Ireland','Luxembourg')
    """)
    cur.execute("""
        UPDATE companies SET data_enrichment_tier = 5
         WHERE data_enrichment_tier IS NULL
           AND country IN ('Saudi Arabia','UAE','United Arab Emirates','Qatar','Kuwait','Oman',
                           'Bahrain','Iraq','Iran')
    """)
    cur.execute("""
        UPDATE companies SET data_enrichment_tier = 6
         WHERE data_enrichment_tier IS NULL
    """)

    raw.commit()
    print("Committed.\n")

    # ── Summary ──────────────────────────────────────────────────────────────
    print(f"{'='*60}")
    print(f"  Matched:    {len(matched):>4}  ({len(matched)/len(accounts)*100:.1f}%)")
    print(f"  Unmatched:  {len(unmatched):>4}  ({len(unmatched)/len(accounts)*100:.1f}%)")
    print(f"  Total:      {len(accounts):>4}")

    cur.execute("SELECT COUNT(*) FROM companies WHERE data_enrichment_tier = 1")
    tier1 = cur.fetchone()[0]
    print(f"  Tier 1 companies after match: {tier1}")
    print(f"{'='*60}\n")

    # Score distribution
    if matched:
        scores = [s for *_, s in matched]
        buckets = [(80, 85), (85, 90), (90, 95), (95, 100), (100, 101)]
        print("Score distribution:")
        for lo, hi in buckets:
            n = sum(1 for s in scores if lo <= s < hi)
            label = f"{lo}-{hi-1}" if hi <= 100 else "100"
            print(f"  {label:>7}:  {n:>3}")
        print()

    # Matched pairs (sorted by score desc)
    print(f"{'CRM Account':<45} {'Company':<40} {'Tkr':<6} {'Score':>5}")
    print("-" * 100)
    for _, acct_name, _, comp_name, ticker, score in sorted(matched, key=lambda r: -r[5]):
        t = ticker or ""
        print(f"  {acct_name:<43} {comp_name:<40} {t:<6} {score:>5.1f}")

    if unmatched:
        print(f"\nUnmatched CRM accounts ({len(unmatched)}):")
        for _, name in unmatched:
            print(f"  - {name}")

except Exception as e:
    raw.rollback()
    print(f"\nERROR — rolled back: {e}")
    raise
finally:
    raw.close()
