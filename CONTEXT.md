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
Tier 1 (21 companies) — 2 enriched with HIGH confidence:
- ExxonMobil (id=2): XOM, Integrated O&G, $323.9B rev, 58,000 employees
- Chevron (id=3): CVX, Integrated O&G, $189.0B rev, 43,039 employees

Tier 1 remaining (19 companies): ConocoPhillips (id=8), Halliburton (id=67),
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
