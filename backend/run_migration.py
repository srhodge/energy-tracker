import sys
sys.path.insert(0, ".")
from sqlalchemy import create_engine, text
from app.config import settings

engine = create_engine(settings.database_url)

# Use raw psycopg2 to execute the full migration in one shot
raw_conn = engine.raw_connection()
try:
    cur = raw_conn.cursor()

    print("Step 1: Adding columns to companies...")
    cur.execute("""
        ALTER TABLE companies ADD COLUMN IF NOT EXISTS sub_sector VARCHAR(100);
        ALTER TABLE companies ADD COLUMN IF NOT EXISTS employee_count INTEGER;
        ALTER TABLE companies ADD COLUMN IF NOT EXISTS employee_count_source VARCHAR(50);
        ALTER TABLE companies ADD COLUMN IF NOT EXISTS employee_count_updated DATE;
        ALTER TABLE companies ADD COLUMN IF NOT EXISTS hq_city VARCHAR(100);
        ALTER TABLE companies ADD COLUMN IF NOT EXISTS hq_country VARCHAR(100);
        ALTER TABLE companies ADD COLUMN IF NOT EXISTS tech_decision_city VARCHAR(100);
        ALTER TABLE companies ADD COLUMN IF NOT EXISTS tech_decision_country VARCHAR(100);
        ALTER TABLE companies ADD COLUMN IF NOT EXISTS revenue_ttm NUMERIC(18,2);
        ALTER TABLE companies ADD COLUMN IF NOT EXISTS ebitda_ttm NUMERIC(18,2);
        ALTER TABLE companies ADD COLUMN IF NOT EXISTS gross_profit_ttm NUMERIC(18,2);
        ALTER TABLE companies ADD COLUMN IF NOT EXISTS enterprise_value NUMERIC(18,2);
        ALTER TABLE companies ADD COLUMN IF NOT EXISTS revenue_denominator VARCHAR(20) DEFAULT 'revenue';
        ALTER TABLE companies ADD COLUMN IF NOT EXISTS is_private BOOLEAN DEFAULT FALSE;
        ALTER TABLE companies ADD COLUMN IF NOT EXISTS is_pe_backed BOOLEAN DEFAULT FALSE;
        ALTER TABLE companies ADD COLUMN IF NOT EXISTS commodity_exposure_pct INTEGER;
        ALTER TABLE companies ADD COLUMN IF NOT EXISTS ms_standardized BOOLEAN DEFAULT FALSE;
        ALTER TABLE companies ADD COLUMN IF NOT EXISTS offshore_coe_confirmed BOOLEAN DEFAULT FALSE;
        ALTER TABLE companies ADD COLUMN IF NOT EXISTS incumbent_msp VARCHAR(200);
        ALTER TABLE companies ADD COLUMN IF NOT EXISTS channel_mismatch_flag BOOLEAN DEFAULT FALSE;
        ALTER TABLE companies ADD COLUMN IF NOT EXISTS channel_mismatch_note TEXT;
        ALTER TABLE companies ADD COLUMN IF NOT EXISTS data_enrichment_tier INTEGER;
    """)
    print("  done")

    print("Step 2: Adding columns to crm_accounts...")
    cur.execute("""
        ALTER TABLE crm_accounts ADD COLUMN IF NOT EXISTS energy_company_id INTEGER REFERENCES companies(id) ON DELETE SET NULL;
        ALTER TABLE crm_accounts ADD COLUMN IF NOT EXISTS match_score FLOAT;
        ALTER TABLE crm_accounts ADD COLUMN IF NOT EXISTS match_method VARCHAR(50);
        ALTER TABLE crm_accounts ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();
        ALTER TABLE crm_accounts ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();
    """)
    print("  done")

    print("Step 3: Adding columns to financials...")
    cur.execute("""
        ALTER TABLE financials ADD COLUMN IF NOT EXISTS ebitda_annual_usd DOUBLE PRECISION;
        ALTER TABLE financials ADD COLUMN IF NOT EXISTS gross_profit_annual_usd DOUBLE PRECISION;
        ALTER TABLE financials ADD COLUMN IF NOT EXISTS enterprise_value_usd DOUBLE PRECISION;
        ALTER TABLE financials ADD COLUMN IF NOT EXISTS ps_ratio DOUBLE PRECISION;
        ALTER TABLE financials ADD COLUMN IF NOT EXISTS ps_ratio_5yr_avg DOUBLE PRECISION;
    """)
    print("  done")

    print("Step 4: Creating company_tech_signals...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS company_tech_signals (
            id SERIAL PRIMARY KEY,
            company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE,
            signal_type VARCHAR(50) NOT NULL,
            signal_category VARCHAR(20),
            signal_date DATE,
            signal_title TEXT,
            signal_description TEXT,
            signal_url TEXT,
            sentiment VARCHAR(10),
            spend_impact_direction VARCHAR(10),
            score_points INTEGER DEFAULT 0,
            source VARCHAR(50),
            week_batch_date DATE,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_signals_company ON company_tech_signals(company_id);
        CREATE INDEX IF NOT EXISTS idx_signals_type ON company_tech_signals(signal_type);
        CREATE INDEX IF NOT EXISTS idx_signals_date ON company_tech_signals(signal_date DESC);
        CREATE INDEX IF NOT EXISTS idx_signals_batch ON company_tech_signals(week_batch_date);
    """)
    print("  done")

    print("Step 5: Creating company_spend_estimates...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS company_spend_estimates (
            id SERIAL PRIMARY KEY,
            company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE,
            estimate_date DATE NOT NULL,
            estimate_type VARCHAR(20) NOT NULL,
            fiscal_year INTEGER,
            it_spend_low NUMERIC(15,2),
            it_spend_mid NUMERIC(15,2),
            it_spend_high NUMERIC(15,2),
            ot_spend_low NUMERIC(15,2),
            ot_spend_mid NUMERIC(15,2),
            ot_spend_high NUMERIC(15,2),
            digital_spend_low NUMERIC(15,2),
            digital_spend_mid NUMERIC(15,2),
            digital_spend_high NUMERIC(15,2),
            ai_spend_low NUMERIC(15,2),
            ai_spend_mid NUMERIC(15,2),
            ai_spend_high NUMERIC(15,2),
            total_spend_low NUMERIC(15,2),
            total_spend_mid NUMERIC(15,2),
            total_spend_high NUMERIC(15,2),
            wwt_addressable_low NUMERIC(15,2),
            wwt_addressable_high NUMERIC(15,2),
            wwt_addressable_pct_low NUMERIC(5,2),
            wwt_addressable_pct_high NUMERIC(5,2),
            confidence_level VARCHAR(10),
            model_version VARCHAR(10) DEFAULT 'v3.0',
            step1_value_chain VARCHAR(100),
            step2_denominator_used VARCHAR(20),
            step3_regional_multiplier NUMERIC(5,3),
            step6_it_maturity_score INTEGER,
            step6_ot_maturity_score INTEGER,
            step6_digital_maturity_score INTEGER,
            step6_ai_maturity_score INTEGER,
            step9_commodity_adjustment NUMERIC(5,3),
            step10_addressable_pct NUMERIC(5,2),
            key_drivers JSONB,
            flags JSONB,
            notes TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_estimates_company ON company_spend_estimates(company_id);
        CREATE INDEX IF NOT EXISTS idx_estimates_type ON company_spend_estimates(estimate_type);
        CREATE INDEX IF NOT EXISTS idx_estimates_date ON company_spend_estimates(estimate_date DESC);
    """)
    print("  done")

    print("Step 6: Creating company_leadership...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS company_leadership (
            id SERIAL PRIMARY KEY,
            company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE,
            role VARCHAR(100) NOT NULL,
            person_name VARCHAR(200),
            location_city VARCHAR(100),
            location_country VARCHAR(100),
            hire_date DATE,
            linkedin_url TEXT,
            is_current BOOLEAN DEFAULT TRUE,
            departure_date DATE,
            spend_category VARCHAR(20),
            signal_score INTEGER DEFAULT 0,
            source VARCHAR(50),
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_leadership_company ON company_leadership(company_id);
        CREATE INDEX IF NOT EXISTS idx_leadership_role ON company_leadership(role);
        CREATE INDEX IF NOT EXISTS idx_leadership_current ON company_leadership(is_current);
    """)
    print("  done")

    print("Step 7: Creating company_assets...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS company_assets (
            id SERIAL PRIMARY KEY,
            company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE,
            asset_type VARCHAR(100) NOT NULL,
            asset_category VARCHAR(20),
            asset_value NUMERIC(15,2),
            asset_unit VARCHAR(50),
            asset_score INTEGER,
            data_source VARCHAR(100),
            as_of_date DATE,
            notes TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_assets_company ON company_assets(company_id);
        CREATE INDEX IF NOT EXISTS idx_assets_type ON company_assets(asset_type);
        CREATE INDEX IF NOT EXISTS idx_assets_category ON company_assets(asset_category);
    """)
    print("  done")

    print("Step 8: Populating sub_sector...")
    cur.execute("""
        UPDATE companies SET sub_sector = CASE
            WHEN value_chain_position::text = 'Upstream' THEN 'Upstream E&P'
            WHEN value_chain_position::text = 'Midstream' THEN 'Midstream Pipeline & Processing'
            WHEN value_chain_position::text = 'Downstream' THEN 'Downstream Refining'
            WHEN value_chain_position::text = 'Integrated' THEN 'Integrated O&G'
            WHEN value_chain_position::text = 'Services' THEN 'Oilfield & Energy Services'
            WHEN energy_segment::text LIKE '%Utility%' OR energy_segment::text LIKE '%Utilities%' THEN 'Energy Utilities'
            WHEN energy_segment::text LIKE '%Chemical%' OR energy_segment::text LIKE '%Petrochem%' THEN 'Petrochemical & Specialty Chemicals'
            WHEN energy_segment::text LIKE '%Renewable%' THEN 'Renewable & New Energy'
            ELSE NULL
        END
        WHERE sub_sector IS NULL
    """)
    print(f"  {cur.rowcount} rows updated")

    print("Step 9: Setting data_enrichment_tier...")
    cur.execute("""
        UPDATE companies SET data_enrichment_tier = 1
        WHERE id IN (
            SELECT DISTINCT energy_company_id FROM crm_accounts WHERE energy_company_id IS NOT NULL
        )
    """)
    print(f"  tier 1: {cur.rowcount}")
    cur.execute("""
        UPDATE companies SET data_enrichment_tier = 2
        WHERE data_enrichment_tier IS NULL
        AND country IN ('United States', 'USA', 'US')
    """)
    print(f"  tier 2: {cur.rowcount}")
    cur.execute("""
        UPDATE companies SET data_enrichment_tier = 3
        WHERE data_enrichment_tier IS NULL AND country IN ('Canada')
    """)
    print(f"  tier 3: {cur.rowcount}")
    cur.execute("""
        UPDATE companies SET data_enrichment_tier = 4
        WHERE data_enrichment_tier IS NULL
        AND country IN ('United Kingdom','Netherlands','Norway','France','Germany','Italy','Spain',
                        'Denmark','Belgium','Sweden','Finland','Austria','Switzerland','Portugal',
                        'Ireland','Luxembourg')
    """)
    print(f"  tier 4: {cur.rowcount}")
    cur.execute("""
        UPDATE companies SET data_enrichment_tier = 5
        WHERE data_enrichment_tier IS NULL
        AND country IN ('Saudi Arabia','UAE','United Arab Emirates','Qatar','Kuwait','Oman',
                        'Bahrain','Iraq','Iran')
    """)
    print(f"  tier 5: {cur.rowcount}")
    cur.execute("""
        UPDATE companies SET data_enrichment_tier = 6
        WHERE data_enrichment_tier IS NULL
    """)
    print(f"  tier 6: {cur.rowcount}")

    raw_conn.commit()
    print("\nMigration committed successfully.\n")

    print("Summary:")
    cur.execute("""
        SELECT 'companies columns' as item, COUNT(*)::text as count
          FROM information_schema.columns
         WHERE table_name='companies' AND table_schema='public'
        UNION ALL SELECT 'company_tech_signals rows',   COUNT(*)::text FROM company_tech_signals
        UNION ALL SELECT 'company_spend_estimates rows', COUNT(*)::text FROM company_spend_estimates
        UNION ALL SELECT 'company_leadership rows',      COUNT(*)::text FROM company_leadership
        UNION ALL SELECT 'company_assets rows',          COUNT(*)::text FROM company_assets
        UNION ALL SELECT 'sub_sector populated',         COUNT(*)::text FROM companies WHERE sub_sector IS NOT NULL
        UNION ALL SELECT 'tier 1 companies',  COUNT(*)::text FROM companies WHERE data_enrichment_tier = 1
        UNION ALL SELECT 'tier 2 companies',  COUNT(*)::text FROM companies WHERE data_enrichment_tier = 2
        UNION ALL SELECT 'tier 3 companies',  COUNT(*)::text FROM companies WHERE data_enrichment_tier = 3
        UNION ALL SELECT 'tier 4 companies',  COUNT(*)::text FROM companies WHERE data_enrichment_tier = 4
        UNION ALL SELECT 'tier 5 companies',  COUNT(*)::text FROM companies WHERE data_enrichment_tier = 5
        UNION ALL SELECT 'tier 6 companies',  COUNT(*)::text FROM companies WHERE data_enrichment_tier = 6
    """)
    for item, count in cur.fetchall():
        print(f"  {item:<35} {count}")

except Exception as e:
    raw_conn.rollback()
    print(f"\nERROR — rolled back: {e}")
    raise
finally:
    raw_conn.close()
