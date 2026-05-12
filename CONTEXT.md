# WWT Energy Tracker — Project Context for New Chat Sessions

## App Infrastructure
- Frontend: https://energy-tracker-swart.vercel.app (React/TypeScript, Vercel)
- Backend: https://energy-tracker-production-39a1.up.railway.app (FastAPI, Railway)
- Database: PostgreSQL on Railway
- GitHub: srhodge/energy-tracker
- Local: C:\Users\sfsal\Documents\Energy-Tracker

## Key Files
- backend/app/services/spend_estimator.py — 13-step spend model engine (v4.0)
- backend/app/services/run_estimates.py — CLI runner for estimates
- backend/app/services/patch_company.py — pushes enrichment JSON to production API
- backend/app/routers/intelligence.py — all intelligence API endpoints
- backend/enrichment_data/ — enrichment JSON files per company
- frontend/src/pages/CompanyDetail.tsx — company detail + Intelligence tab
- G:\WWT\Energy Tracker\WWT_Energy_Spend_Model_v4.docx — full methodology document
- G:\WWT\Energy Tracker\wwt_energy_spend_model_v4.html — HTML version of methodology

## Database Tables (key new ones added this session)
- companies — 42 columns including all enrichment fields
- company_tech_signals — weekly batch signals per company
- company_spend_estimates — model output per company (v4.0)
- company_leadership — CIO/CDO/CAIO/CTO records with signal scores
- company_assets — OT/IT/Digital/AI asset scores per company

## Spend Model v4.0 — Key Parameters
Base addressable: 27% (corrected from 28% — SAP/Oracle already excluded)
OEM-direct deduction: -3% for companies with revenue >$10B
Offshore CoE: -8%
Incumbent MSP: -10%
Channel mismatch: -8%
MS Standardized (Softchoice): +5%
High AI maturity (score >=15): +5%
Floor: 12%, Ceiling: 42%

Full 13-step model documentation: see WWT_Energy_Spend_Model_v4.docx

## Enrichment Status (as of May 2026)
Tier 1 (21 companies) — 3 enriched with HIGH confidence:
- ExxonMobil (id=2): XOM, Integrated O&G, $323.9B rev, 58,000 employees
- Chevron (id=3): CVX, Integrated O&G, $189.0B rev, 43,039 employees
- ConocoPhillips (id=8): COP, Upstream E&P, $56.1B rev, 11,800 employees, $1.60B WWT addressable (34%)

Tier 1 remaining (18 companies): Halliburton (id=67),
Phillips 66 (id=34), Enbridge (id=12), EOG Resources (id=21), Targa Resources (id=53),
LyondellBasell (id=63), Sempra Energy (id=31), Antero Resources (id=144),
Chord Energy (id=150), CVR Energy (id=345), Helmerich & Payne (id=258),
HF Sinclair (id=152), NCS Multistage (id=567), Par Pacific (id=402),
PBF Energy (id=259), Sasol (id=244), Technip Energies (id=214),
TechnipFMC (id=110), Weatherford (id=179), Worley (id=201)

## Enrichment Workflow
1. I (Claude in new chat) research company via web search
2. Generate enrichment JSON
3. User pastes JSON instruction into Claude Code
4. Claude Code writes file + runs patch_company.py against production API
5. Claude Code runs run_estimates.py --company-id N

## Pending Work
1. Continue Tier 1 enrichment (19 remaining companies)
2. Filter bar standardization across all pages (Analytics pattern)
3. Intelligence tab Phase 2 enhancements (forward estimate display, opportunity scorecard)
4. Weekly batch signal collection service
5. Expand to Tier 2 US companies after Tier 1 complete

## Key Architectural Decisions
- CRM accounts and companies table NOT linked yet (deliberate — pending manual review UI)
- Enrichment research done by Claude (web search) -> JSON -> Claude Code pushes via API
- All batch processes filter WHERE status = 'active' (567 active, 18 non-active)
- No Anthropic API key available locally or in Railway for automated enrichment

## CRM Data Details
- 83 Salesforce accounts loaded (48 with real opportunity data, 35 named placeholders with $0)
- 7,878 total opportunities (deduplicated across all export files)
- $60.35M open pipeline, $179.56M closed won, 64.4% win rate
- Key sellers: Sam Hodge (hodges) - 25 open opps, Matthew Nalbone (nalbonem) - 30 opps, Shay Gillespie (sgill)
- CRM data is in crm_accounts and crm_opportunities tables — NOT linked to companies table yet (deliberate)
- Fuzzy matching script exists (match_crm_accounts.py) but was NOT run — manual review UI planned first
- The 83 CRM accounts were used only to set data_enrichment_tier=1 via exact name match (21 matched)

## WWT Territory Structure (for channel mismatch logic)
Territories in the database: STOLA (Houston/TX), EURO, MENA, APAC, CALA, FEDERAL, and others
Channel mismatch flag = tech decisions made in a city not covered by the WWT account owner's territory
Key examples: Shell (EURO account, Houston tech decisions), BP (EURO account, Houston ops),
Dow Chemical (FEDERAL/STOLA mismatch), Bechtel (similar)

## UI Pages and Their Status
- Companies page — filter bar complete, working
- Territory Dashboard — filter bar complete, working
- Analytics page — REFERENCE for filter bar pattern (sticky horizontal, pill-style dropdowns, Reset button)
- Activity Feed — has filters, needs standardization
- CRM Dashboard — 4 tabs (Companies, Opportunities, Owners, Summary)
  - Has been partially improved but filter bar NOT yet standardized to Analytics pattern
  - Pending: full filter bar standardization matching Analytics exactly
- Company Detail page — Overview + Intelligence tabs both working

## Filter Bar Standardization (PENDING TASK — HIGH PRIORITY)
The Analytics page has the reference filter bar pattern:
- Sticky/fixed at top of content area (below sidebar/nav)
- Pill-style dropdown buttons
- Reset button appears only when any filter differs from default, disappears when reset
This pattern needs to be applied to:
1. CrmDashboard.tsx — all 4 tabs (Companies, Opportunities, Owners, Summary)
2. Companies page — already has filters, needs to match Analytics style exactly
3. Territory Dashboard — same
4. Activity Feed page

## Intelligence Tab Enhancements (PENDING)
Phase 2 enhancements planned but not yet built:
- Forward estimate FY2027E column (data exists in company_spend_estimates, just not displayed)
- Opportunity Scorecard (5-factor: tech maturity, financial capacity, strategic urgency, WWT accessibility, relationship warmth)
- Confidence indicator per category (not just overall)
- Trend arrow vs. prior estimate
- Signal age warning banner (>90 days since last signal)
- NEW badge for recent leadership hires (<18 months)
- Missing role flags (grayed-out row if no CAIO identified)
- Completeness score / data freshness indicator on profile card
- WWT relationship context pulled from CRM (last opportunity date, pipeline, account owner)

## Weekly Batch Signal Collection (PLANNED, NOT YET BUILT)
Planned architecture:
- Backend scheduled job collects signals weekly from news/LinkedIn/SEC
- Signals stored in company_tech_signals with week_batch_date
- Displayed in company detail Intelligence tab as "Recent Signals" feed
- Scoring refreshed quarterly at earnings dates
- Requires Anthropic API key in Railway env vars (NOT YET SET)

## Sub-Sector Values Currently in Database
Mapped from value_chain_position:
- Upstream E&P, Midstream Pipeline & Processing, Downstream Refining
- Integrated O&G, Oilfield & Energy Services, Energy Utilities
- Petrochemical & Specialty Chemicals, Renewable & New Energy
New segments to add (not yet in DB):
- Energy Infrastructure & Power, Carbon Management, LNG & Gas Trading

## Enrichment JSON Files Location
backend/enrichment_data/
- exxonmobil.json (company_id=2) — COMPLETE
- chevron.json (company_id=3) — COMPLETE

## Key WWT Commercial Context (for model/enrichment work)
- WWT acquired Softchoice in 2024 — adds Microsoft licensing addressability (+5% Step 10)
- WWT AI Proving Ground — ~12 years AI history, 7x consecutive NVIDIA Americas Enterprise Partner of Year
- Halliburton has expressed desire for WWT strategic alignment (internal knowledge)
- Chevron MSP confirmed: HCL Technologies + LTIMindtree (internal knowledge)
- Shell Houston relationship exists at WWT but account owned by EURO territory (channel conflict)

## Salesforce Account to Company ID Mapping Notes
The 83 CRM accounts use slightly different names than the 585 companies database.
Known aliases needing manual mapping when ready:
- "Oxy" = Occidental Petroleum
- "ExxonMobil Global Services Company" = ExxonMobil (id=2)
- "Engie North America" = ENGIE
- "ONEOK" = ONEOK (may not exist in companies DB)
- "Baker Hughes Inc" vs "Baker Hughes"
- "Schlumberger Ltd." vs "Schlumberger/SLB"
