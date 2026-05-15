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
- companies — 45 columns including all enrichment fields + ce_name/ce_email/ce_phone (migration 0011, 2026-05-14)
- company_tech_signals — weekly batch signals per company
- company_spend_estimates — model output per company (v4.0)
- company_leadership — CIO/CDO/CAIO/CTO records with signal scores
- company_assets — OT/IT/Digital/AI asset scores per company

## Spend Model v4.0 — Key Parameters
Base addressable: 27% (corrected from 28% — SAP/Oracle already excluded)
OEM-direct deduction: -3% (manual confirmation only — oem_direct_confirmed=true required)
Offshore CoE: -8%
Incumbent MSP: -10%
Channel mismatch: -8%
MS Standardized (Softchoice): +5%
High AI maturity (score >=15): +5%
Floor: 12%, Ceiling: 42%

ai_maturity_score (DB column, INTEGER, added 2026-05-14 via migration 0010):
- Stored on companies table via patch_company.py from spend_model_flags.ai_maturity_score in enrichment JSONs
- Acts as a FLOOR for the computed maturity_score (computed from signals + leadership can exceed it)
- 4 companies currently have stored scores: ExxonMobil=18, Chevron=13, Sasol=13, Weatherford=12
- Score ≥15 triggers high AI maturity +5% bonus; values 12-14 are stored but do not yet trigger bonus

Signal scoring window (updated 2026-05-14): 730 days (2yr) lookback, not 365 days.
Signal types counted toward maturity_score: partnership, ai_announcement, leadership_hire, strategic_pivot, earnings_signal
(strategic_pivot and earnings_signal added 2026-05-14; previously excluded, causing undercount for companies with data center / AI strategy pivots)

Step 2 sub-sector denominator (applied automatically, updated May 2026):
- Midstream Pipeline & Processing: EBITDA × 2.5 (fallback: Revenue × 0.12) — commodity pass-through revenue is misleading
- Downstream Refining: Gross Profit (fallback: EBITDA × 1.5, then Revenue × 0.06) — thin margins; revenue is a poor IT proxy
- Energy Utilities: EBITDA × 2.5 (fallback: Revenue × 0.35) — rate-base model; revenue set by regulators
- Integrated O&G: 50% Revenue + 50% EBITDA blend
- All others (E&P, OFS, Chemicals, Renewable): Revenue

Full 13-step model documentation: see WWT_Energy_Spend_Model_v4.docx

## Enrichment Status (as of May 2026)
Tier 1 (21 companies) — 21 enriched (COMPLETE):
- ExxonMobil (id=2): XOM, Integrated O&G, $323.9B rev, 58,000 employees, $1.20B WWT addressable high (12% — floor; 27%−3%OEM−8%CoE−10%MSP+5%AI=11%→floor; CoE=Bangalore Global Business & Tech Center [DC exit evaluation active — WWT opportunity], MSP=Accenture/Deloitte/McKinsey confirmed, ms_standardized=false, ai_maturity_score=18; CRM linked: crm_accounts id=14 "ExxonMobil Global Services Company" → energy_company_id=2, manual_confirmed, score=100; CRM 3yr: $7.14M open pipeline, $5.73M closed won, 76 open opps; Relationship Warmth=5/5) [HIGH]
- Chevron (id=3): CVX, Integrated O&G, $193.4B rev, 40,000 employees, $458.4M mid / $668.5M high WWT addressable (12% — floor; 27%−3%OEM−8%CoE−10%MSP+5%MS+0%AI=11%→floor; CoE=Bengaluru ENGINE Center, MSP=HCL Technologies+LTIMindtree confirmed, ms_standardized=true, ai_maturity_score=13 below ≥15 threshold — AI bonus does not apply) [HIGH]
- ConocoPhillips (id=8): COP, Upstream E&P, $56.1B rev, 11,800 employees, $1.74B WWT addressable (37%; 27%+5%MS+5%AI=37%; ms_standardized=true, high AI maturity confirmed, oem_direct_confirmed=false) [HIGH]
- Halliburton (id=67): HAL, Oilfield & Energy Services, $22.9B rev, 48,000 employees, $1.11B WWT addressable (19%; 27%−3%OEM−10%MSP+5%MS+5%AI=24%→19% floor from MSP — AI bonus now applies; MSP=Accenture confirmed, ms_standardized=true, ai_maturity≥15 confirmed) [MEDIUM_HIGH]
- Phillips 66 (id=34): PSX, Downstream Refining, $143.1B rev, 13,000 employees, $474M WWT addressable (37%; 27%+5%MS+5%AI=37%; ms_standardized=true, no MSP, oem_direct_confirmed=false, ai_maturity≥15 confirmed — high AI bonus now applies; denominator=Revenue×0.06=$8.59B) [MEDIUM_HIGH]
- Enbridge (id=12): ENB, Midstream Pipeline & Processing, $38.75B rev, 12,000 employees, $236M WWT addressable (29%; 27%−8%mismatch+5%MS+5%AI=29%; ms_standardized=true, channel_mismatch=Calgary HQ outside STOLA territory, oem_direct_confirmed=false, ai_maturity≥15 confirmed — high AI bonus now applies; denominator=Revenue×0.12=$4.65B) [MEDIUM_HIGH]
- EOG Resources (id=21): EOG, Upstream E&P, $23.7B rev, 3,000 employees, $325.4M WWT addressable (27%; 27%=27%; ms_standardized=false, no MSP, no CoE, oem_direct_confirmed=false) [MEDIUM_HIGH]
- Targa Resources (id=53): TRGP, Midstream Pipeline & Processing, $17.0B rev, 3,570 employees, $49.4M WWT addressable (27%; 27%=27%; ms_standardized=false, no MSP, no CoE, oem_direct_confirmed=false; denominator=Revenue×0.12=$2.04B) [MEDIUM_HIGH]
- LyondellBasell (id=63): LYB, Petrochemical & Specialty Chemicals, $37.7B rev, 26,000 employees, $804.9M WWT addressable (32%; 27%+5%MS=32%; ms_standardized=true, no MSP, no CoE, oem_direct_confirmed=false) [MEDIUM_HIGH]
- Sempra Energy (id=31): SRE, Energy Utilities, $13.185B rev, 16,773 employees, $294.1M WWT addressable (24%; 27%−8%mismatch+5%MS=24%; ms_standardized=true, channel_mismatch=San Diego HQ outside STOLA, no MSP, no CoE, oem_direct_confirmed=false; denominator=Revenue×0.35=$4.61B) [MEDIUM_HIGH]
- Antero Resources (id=144): AR, Upstream E&P, $4.11B rev, 632 employees, $18.0M mid / $26.0M high WWT addressable (19%; 27%−8%mismatch=19%; ms_standardized=false, no MSP, no CoE, channel_mismatch=Denver HQ outside STOLA) [MEDIUM_HIGH]
- Chord Energy (id=150): CHRD, Upstream E&P, $5.25B rev, 762 employees, $32.5M mid / $47.0M high WWT addressable (27%; 27%=27%; ms_standardized=false, no MSP, no CoE, Houston HQ in STOLA) [MEDIUM_HIGH]
- CVR Energy (id=345): CVI, Downstream Refining, $7.61B rev, 1,595 employees, $59.7M mid / $83.3M high WWT addressable (27%; 27%=27%; ms_standardized=false, no MSP, no CoE, Sugar Land TX in STOLA) [MEDIUM_HIGH]
- Helmerich & Payne (id=258): HP, Oilfield & Energy Services, $2.76B rev, 6,200 employees, $26.9M mid / $38.9M high WWT addressable (19%; 27%−8%mismatch=19%; ms_standardized=false, no MSP, no CoE, channel_mismatch=Tulsa OK outside STOLA) [MEDIUM_HIGH]
- HF Sinclair (id=152): DINO, Downstream Refining, $28.57B rev, 4,800 employees, $46.7M WWT addressable (27%; 27%=27%; ms_standardized=false, no MSP, Dallas TX in STOLA, oem_direct_confirmed=false; denominator=Revenue×0.06=$1.71B) [MEDIUM_HIGH]
- NCS Multistage (id=567): NCSM, Oilfield & Energy Services, $162.6M rev, 250 employees, $2.2M mid / $3.3M high WWT addressable (27%; 27%=27%; ms_standardized=false, Houston TX in STOLA — micro-cap, limited opportunity) [MEDIUM_HIGH]
- Par Pacific (id=402): PARR, Downstream Refining, $8.2B rev, 1,100 employees, $61.5M mid / $85.9M high WWT addressable (27%; 27%=27%; ms_standardized=false, Houston TX in STOLA) [MEDIUM_HIGH]
- PBF Energy (id=259): PBF, Downstream Refining, $33.12B rev, 3,800 employees, $30.3M WWT addressable (19%; 27%−8%mismatch=19%; ms_standardized=false, channel_mismatch=Parsippany NJ outside STOLA, oem_direct_confirmed=false; denominator=Revenue×0.06=$1.99B) [MEDIUM_HIGH]
- Sasol (id=244): SSL, Petrochemical & Specialty Chemicals, $13.9B rev, 27,411 employees, $401.7M WWT addressable (24%; 27%−8%mismatch+5%MS=24%; ms_standardized=true, CIO confirmed, channel_mismatch=Johannesburg HQ, oem_direct_confirmed=false) [MEDIUM_HIGH]
- Technip Energies (id=214): TE, Oilfield & Energy Services, $7.61B rev, 17,000 employees, $88.4M mid / $127.7M high WWT addressable (19%; 27%−8%mismatch=19%; ms_standardized=false, channel_mismatch=France HQ) [MEDIUM_HIGH]
- TechnipFMC (id=110): FTI, Oilfield & Energy Services, $9.08B rev, 21,000 employees, $116.9M mid / $168.9M high WWT addressable (19%; 27%−8%mismatch=19%; ms_standardized=false, channel_mismatch=UK HQ, Datagration AI acquisition) [MEDIUM_HIGH]
- Weatherford (id=179): WFRD, Oilfield & Energy Services, $5.4B rev, 17,000 employees, $140.4M mid / $204.3M high WWT addressable (27%; 27%=27%; ms_standardized=false, Houston HQ in STOLA, Datagration AI acquisition, CEO digitalization mandate) [MEDIUM_HIGH]
- Worley (id=201): WOR, Oilfield & Energy Services, $8.24B rev, 45,505 employees, $147.9M mid / $213.6M high WWT addressable (19%; 27%−8%mismatch=19%; ms_standardized=false, channel_mismatch=Sydney Australia HQ) [MEDIUM_HIGH]

Tier 1 remaining: NONE — all 21 companies enriched.

Tier 2 (US companies by revenue) — enrichment begun May 2026:
- Marathon Petroleum (id=38): MPC, Downstream Refining, $135.95B rev, 16,738 employees, $176.6M WWT addressable (24%; 27%−8%mismatch+5%MS=24%; CDO Ehren Powell confirmed since 2020, new CEO Maryann Mannen Aug 2024 from TechnipFMC, ms_standardized=true, channel_mismatch=Findlay OH outside STOLA, Imubit AI deployed, MPLX AI data center pivot 2025, ai_maturity=13; denominator=Revenue×0.06=$8.16B) [HIGH]
- Valero Energy (id=50): VLO, Downstream Refining, $117.84B rev, 9,811 employees, $138.2M WWT addressable (27%; 27%=27%; no CIO/CDO — VP Technology only, no cloud/MSP/AI programs confirmed, San Antonio TX in STOLA, ai_maturity=6; denominator=Revenue×0.06=$7.07B) [MEDIUM_HIGH]
- SLB (id=28): SLB, Oilfield & Energy Services, $35.94B rev, 113,000 employees, $3.42B WWT addressable (37%; 27%+5%MS+5%AI=37%; CEO Olivier Le Peuch drives digital-first, $2.44B digital revenue FY2024, NVIDIA partnership, ChampionX acquisition July 2025, ms_standardized=true, Houston HQ in STOLA, ai_maturity≥15 confirmed — high AI bonus applies) [HIGH]
- Occidental Petroleum (id=42): OXY, Upstream E&P, $26.72B rev, 12,000 employees, $529.9M WWT addressable (32%; 27%+5%MS=32%; CEO Vicki Hollub, ruthless automation 40% Permian production automated, CrownRock acquisition Aug 2024 IT integration demand, ms_standardized=true, Houston HQ in STOLA, ai_maturity=13) [MEDIUM_HIGH]
- Baker Hughes (id=52): BKR, Oilfield & Energy Services, $27.83B rev, 58,000 employees, $1.82B WWT addressable (37%; 27%+5%MS+5%AI=37%; CEO Lorenzo Simonelli, Azure MOU Feb 2025 + AI Foundry integration, Cordant bp enterprise contract, C3 AI partnership, ms_standardized=true, Houston HQ in STOLA, ai_maturity≥15 confirmed — high AI bonus applies) [HIGH]
- Williams Companies (id=23): WMB, Midstream Pipeline & Processing, $10.5B rev, 5,829 employees, $39.6M WWT addressable (19%; 27%−8%mismatch=19%; new CEO Chad Zamarin July 2025, $3.1B AI data center power commitment Socrates project, ms_standardized=false, channel_mismatch=Tulsa OK outside STOLA, ai_maturity=9; denominator=Revenue×0.12=$1.26B) [MEDIUM_HIGH]
- ONEOK (id=29): OKE, Midstream Pipeline & Processing, $35.2B rev, 6,326 employees, $68.7M WWT addressable (19%; 27%−8%mismatch=19%; CEO Pierce Norton, satellite emissions detection deployed, 4 simultaneous M&A integrations (Magellan/EnLink/Medallion/Gulf Coast NGL) = highest IT integration demand in midstream, channel_mismatch=Tulsa OK, ms_standardized=false, ai_maturity=7; denominator=Revenue×0.12=$4.22B) [MEDIUM_HIGH]
- Energy Transfer (id=27): ET, Midstream Pipeline & Processing, $92.29B rev, 12,000 employees, $192.5M WWT addressable (27%; 27%=27%; Co-CEO Tom Long, AI data center power positioning, Lake Charles LNG 20-yr Chevron SPA, Dallas TX in STOLA, ms_standardized=false, ai_maturity=5; denominator=Revenue×0.12=$11.07B) [MEDIUM_HIGH]
- Devon Energy (id=66): DVN, Upstream E&P, $16.0B rev, 4,500 employees, $207.3M WWT addressable (24%; 27%−8%mismatch+5%MS=24%; CTO Trey Lowe confirmed, AI/automation/RPA named as core competencies, Databricks+Azure+SAP HANA confirmed, new CEO Clay Gaspar 2025 + $1B business optimization, channel_mismatch=OKC outside STOLA, ms_standardized=true, ai_maturity=11) [MEDIUM_HIGH]
- Enterprise Products Partners (id=24): EPD, Midstream Pipeline & Processing, $51.56B rev, 7,500 employees, $107.5M WWT addressable (27%; 27%=27%; no CIO/technology leadership identified, AI data center power positioning is energy revenue play not internal IT, Houston HQ in STOLA, ms_standardized=false, ai_maturity=6; denominator=Revenue×0.12=$6.19B) [MEDIUM_HIGH]
- Cheniere Energy (id=70): LNG, Midstream Pipeline & Processing, $15.1B rev, 1,717 employees, $31.5M WWT addressable (27%; 27%=27%; 1,717 employees extremely lean for Fortune 500, Corpus Christi Stage 3 expansion = near-term IT/OT demand, Houston HQ in STOLA, ms_standardized=false, ai_maturity=6; denominator=Revenue×0.12=$1.81B — corrected from pre-refactor $169.3M) [MEDIUM_HIGH]
- Diamondback Energy (id=32): FANG, Upstream E&P, $14.46B rev, 1,983 employees, $98.0M WWT addressable (19%; 27%−8%mismatch=19%; electric simul-frac VoltaGrid+Halliburton 200MW, real-time methane monitoring 87% production, $26B Endeavor merger IT integration, channel_mismatch=Midland TX West Texas, ms_standardized=false, ai_maturity=8) [MEDIUM_HIGH]
- Dow (id=55): DOW, Petrochemical & Specialty Chemicals, $39.33B rev, 36,000 employees, $1.30B WWT addressable (29%; 27%−8%mismatch+5%MS+5%AI=29%; CIDO Debra Bauler on Leadership Team, CDAO Chris Bruman, two CIO 100 Awards 2024-2025 (Integrated Data Hub + Market Intelligence Hub OpenAI), channel_mismatch=Midland MI outside STOLA, ms_standardized=true, ai_maturity=27+ [leadership alone ≥15]) [HIGH]
- Kinder Morgan (id=30): KMI, Midstream Pipeline & Processing, $15.1B rev, 10,933 employees, $123.9M WWT addressable (32%; 27%+5%MS=32%; CIO/CAO Michael Pitta, CFO drives GenAI strategy, $5B pipeline backlog for AI data center demand, Houston HQ in STOLA, ms_standardized=true, ai_maturity=10; denominator=Revenue×0.12=$1.81B) [MEDIUM_HIGH]
- Expand Energy (id=76): EXE, Upstream E&P, $12.96B rev, 2,400 employees, $157.9M WWT addressable (27%; 27%=27%; interim CEO Wichterich, Chesapeake+Southwestern merger IT integration, HQ relocating Oklahoma City→Houston Feb 2026, ms_standardized=false, ai_maturity=6) [MEDIUM_HIGH]
- MPLX LP (id=43): MPLX, Midstream Pipeline & Processing, $11.82B rev, 6,000 employees, $49.7M WWT addressable (19%; 27%−8%mismatch+5%MS=24% but estimate reflects ~19% effective; CEO Maryann Mannen (also MPC CEO), MARA Holdings AI data center natural gas supply partnership, Marathon subsidiary, channel_mismatch=Findlay OH outside STOLA, ms_standardized=true, ai_maturity=7; denominator=Revenue×0.12=$1.42B) [MEDIUM_HIGH]
- Westlake Chemical (id=79): WLK, Petrochemical & Specialty Chemicals, $10.98B rev, 16,000 employees, $242.8M WWT addressable (27%; no adjustments; no CIO/CDO identified, no AI programs, family-controlled (Chao family ~70%), Houston HQ in STOLA, ms_standardized=false, ai_maturity=0; sub_sector corrected from Downstream Refining) [MEDIUM_HIGH]
- Sunoco LP (id=158): SUN, Downstream Refining (fuel distribution), $22.69B rev, 6,000 employees, $50.9M WWT addressable (27%; no adjustments; CEO Joseph Kim, $7.3B NuStar acquisition May 2024 = multi-year IT integration, Energy Transfer subsidiary, Dallas HQ in STOLA, ms_standardized=false, ai_maturity=4; denominator=Revenue×0.06=$1.36B pass-through adjustment) [MEDIUM_HIGH]
- EQT Corporation (id=73): EQT, Upstream E&P, $9.36B rev, 1,461 employees, $79.1M WWT addressable (19%; 27%−8%mismatch=19%; CIO confirmed VP-level per proxy (name unknown), Equitrans Midstream merger IT integration, AI data center natural gas positioning via EVP Rob Wingo, channel_mismatch=Pittsburgh PA outside STOLA, ms_standardized=false, ai_maturity=8) [MEDIUM_HIGH]
- NOV Inc. (id=174): NOV, Oilfield & Energy Services, $8.69B rev, 31,605 employees, $276.2M WWT addressable (27%; no adjustments; CEO Clay Williams drives digital/automation as core strategy, Automation Performance Center AI-assisted drilling service, Ideal eFrac 40,000 HP OT automation, Houston HQ in STOLA, ms_standardized=false, ai_maturity=11) [MEDIUM_HIGH]
- Eastman Chemical (id=106): EMN, Petrochemical & Specialty Chemicals, $9.4B rev, 14,000 employees, $399.1M WWT addressable (29%; 27%−8%mismatch+5%MS+5%AI=29%; CIO Aldo Noseda 2024 Tennessee Global ORBIE Award winner, AI/data analytics framework in production, digital products generating independent revenue, Azure+SAP+M365 confirmed, channel_mismatch=Kingsport TN outside STOLA, ms_standardized=true, ai_maturity=16; sub_sector corrected from Downstream Refining) [HIGH]
- APA Corporation (id=133): APA, Upstream E&P, $8.37B rev, 4,700 employees, $93.9M WWT addressable (27%; no adjustments; no CIO identified, $4.5B Callon Petroleum acquisition April 2024 = active IT integration, $350M cost savings program, Houston HQ in STOLA, ms_standardized=false, ai_maturity=7) [MEDIUM_HIGH]
- Coterra Energy (id=81): CTRA, Upstream E&P, $7.35B rev, 957 employees, $70.5M WWT addressable (27%; no adjustments; no CIO identified, two Delaware Basin acquisitions late 2024 = IT integration demand, Houston HQ in STOLA, ms_standardized=false, ai_maturity=5) [MEDIUM_HIGH]
- DuPont de Nemours (id=54): DD, Petrochemical & Specialty Chemicals, $6.92B rev, 25,300 employees, $258.0M WWT addressable (24%; 27%−8%mismatch+5%MS=24%; CEO Lori Koch new June 2024, Digital Center 25-person/40+ projects, 3-way company split = major IT separation demand, Azure+SAP+M365 confirmed, channel_mismatch=Wilmington DE outside STOLA, ms_standardized=true, ai_maturity=10; sub_sector corrected from Downstream Refining) [MEDIUM_HIGH]
- Matador Resources (id=167): MTDR, Upstream E&P, $3.59B rev, 700 employees, $33.1M WWT addressable (27%; no adjustments; no CIO identified, founder-CEO conservative culture, Dallas HQ in STOLA, ms_standardized=false, ai_maturity=4) [MEDIUM_HIGH]
- Range Resources (id=154): RRC, Upstream E&P, $3.21B rev, 700 employees, $30.0M WWT addressable (27%; no adjustments; no CIO identified, Fort Worth TX in STOLA, Appalachian-focused operationally conservative, ms_standardized=false, ai_maturity=4) [MEDIUM_HIGH]
- Antero Midstream (id=159): AM, Midstream Pipeline & Processing, $1.29B rev, 300 employees, $2.6M WWT addressable (19%; 27%−8%mismatch=19%; single-customer MLP for Antero Resources parent, effectively IT satellite of parent, channel_mismatch=Denver CO outside STOLA, ms_standardized=false, ai_maturity=3; denominator=Revenue×0.12=$154.8M) [MEDIUM_HIGH]

## Enrichment Workflow
1. I (Claude in new chat) research company via web search
2. Generate enrichment JSON
3. User pastes JSON instruction into Claude Code
4. Claude Code writes file + runs patch_company.py against production API
5. Claude Code runs run_estimates.py --company-id N

After every enrichment: auto-update CONTEXT.md + commit + push without being asked.

Historical signal backfill complete (2026-05-13): Structured leadership and technology signals backfilled via direct SQL INSERT for 10 companies — COP (x2 ORBIE), PSX (Gartner Summit), ENB (GenAI workforce), MPC (Metis Strategy), EMN (ORBIE), DOW (x2 CIO 100 Awards), BKR (Azure MOU), SLB (NVIDIA Delfi), WFRD. Signals stored in company_tech_signals table as typed records (signal_type: recognition, thought_leadership, partnership) rather than enrichment_notes prose.

## Leadership Signal Types (for enrichment)
When researching company leadership, capture any of the following as signals on the leadership record using signal_type and notes fields. These surface in the Intelligence tab and inform the signal_score:

Awards & Recognition (signal_type: "recognition"):
- CIO/CDO/CAIO ORBIE Award wins (Global, Regional, or sector-specific)
- Gartner Top 25 CIO recognition
- Forbes/Fortune technology leadership lists
- Industry association awards (HoustonCIO, ChicagoCIO, etc.)
- Company-internal awards cited publicly (e.g. WWT Partner of Year)

Career Moves (signal_type: "career_move"):
- New CIO/CDO/CAIO hire within last 18 months — NEW badge trigger
- Promotion to C-suite from VP level
- External hire from high-signal company (GE, Microsoft, Amazon, NVIDIA, etc.)
- Departure of incumbent technology leader — watch signal

Public Appearances & Thought Leadership (signal_type: "thought_leadership"):
- Keynote at Gartner, AWS re:Invent, Microsoft Ignite, SAP Sapphire, CERAWeek
- Published interview or byline in CIO.com, MIT Sloan, HBR on technology strategy
- Panel appearance at industry conference (HoustonCIO, Energy Thought Summit, etc.)
- Podcast guest on technology leadership topics

Strategic Commitments (signal_type: "strategic_commitment"):
- AI budget explicitly named in earnings call or investor presentation
- Board-level AI committee or technology committee formed
- CAIO role created for first time at company
- Digital transformation named as CEO strategic priority

Partnership & Technology Signals (signal_type: "partnership"):
- NVIDIA partnership or certification announced
- Hyperscaler (Azure, AWS, GCP) strategic agreement signed
- SAP RISE or S/4HANA migration announced
- AI platform vendor (C3.ai, Palantir, Cognite, etc.) contract announced

Rules:
- Always include date, source URL where available, and brief description
- signal_score impact: Recognition (+2 to +4), Career Move (+2 to +3), Thought Leadership (+1 to +2), Strategic Commitment (+3 to +5), Partnership (+2 to +4)
- ORBIE Global winner = +4 (highest CIO recognition signal)
- New C-suite hire from NVIDIA/Microsoft/Amazon/GE = +3
- Earnings call AI budget mention = +4

OEM deduction rule: oem_direct_deduction is manual-confirmation only — same standard as incumbent_msp. Never auto-applied by revenue threshold. Confirmed YES: ExxonMobil, Chevron, Halliburton. All others confirmed NO or pending assessment.

## Tier 2 Revenue Population (2026-05-13)
Script: backend/scripts/populate_tier2_revenue.py — pulls totalRevenue, fullTimeEmployees, ebitda, grossProfits from yfinance for all Tier 2 companies with NULL revenue_ttm.
- Found 140 companies needing revenue data
- Updated: 125 companies successfully populated
- Failed/no data: 15 tickers (N/A id=26, STR, NEXT, NR, DRQ, SOI, SMLP, BRY, TSE, GIFI, ZNOG, DNMR, CEIN, HUSA, VTNR)
- Many companies show sub_sector = "unknown" — not yet enriched via patch_company workflow

Tier 2 estimates run (2026-05-15, --tier 2): 168 companies estimated, 0 errors
- Grand total mid (Tier 2): $30.24B across 168 companies
- Grand total WWT high (Tier 2): $12.86B across 168 companies
- 15 companies remain with N/A estimates (revenue NULL after yfinance pull — mostly very small or delisted)
- Top 10 by WWT addressable high: SLB $2,695M, Baker Hughes $1,507M, Dow $1,305M, OXY $530M, Plains All American $418M, Eastman Chemical $399M, PPG Industries $339M, NOV $304M, DuPont $258M, Westlake Chemical $243M

## Pending Work
1. Tier 2 revenue population — COMPLETE
2. Filter bar standardization — COMPLETE
3. Intelligence tab Phase 2 (FY2027E column, Opportunity Scorecard, Signal Age Warning, confidence pills) — COMPLETE
4. ai_maturity_score DB column (migration 0010, floor override) — COMPLETE
5. Denominator audit — COMPLETE
6. Client Executive fields (ce_name, ce_email, ce_phone) — COMPLETE (migration 0011, 2026-05-14)
7. Tier 2 spend estimates — COMPLETE (2026-05-15): 168 companies estimated, 0 errors; $30.24B total mid, $12.86B WWT high
8. CRM account linking — COMPLETE (2026-05-15): 27/27 accounts linked; 6 stub companies added (ids 587–592, Tier 3) to cover previously unlinked pipeline accounts
9. Weekly batch signal collection service — PENDING (requires Anthropic API key in Railway)
10. Structured enrichment for high-value unenriched Tier 2 accounts — PENDING
11. Intelligence tab Phase 3 (trend arrows, NEW badge for recent hires, CRM context panel) — PENDING

## Key Architectural Decisions
- CRM accounts linked to companies table via manual review (energy_company_id FK) — see CRM Data Details below
- Enrichment research done by Claude (web search) -> JSON -> Claude Code pushes via API
- All batch processes filter WHERE status = 'active' (567 active, 18 non-active)
- No Anthropic API key available locally or in Railway for automated enrichment
- ai_maturity_score is now a real DB column (migration 0010) acting as a floor override. Computed dynamically from signals (strategic_pivot + earnings_signal types, 730-day window) then max() applied against stored floor. Companies with stored scores: XOM=18, CVX=13, COP=18, HAL=16, SLB=19, BKR=16, DOW=16, EMN=16, Sasol=13, Weatherford=12, MPC=13, OXY=13.

## CRM Data Details
- 83 Salesforce accounts loaded (48 with real opportunity data, 35 named placeholders with $0)
- 7,878 total opportunities (deduplicated across all export files)
- $60.35M open pipeline, $179.56M closed won, 64.4% win rate
- Key sellers: Sam Hodge (hodges) - 25 open opps, Matthew Nalbone (nalbonem) - 30 opps, Shay Gillespie (sgill)
- CRM linking status (2026-05-15): 27 accounts linked to companies table (energy_company_id, match_method='manual_confirmed', match_score=100)

Linked accounts (crm_id → company_id):
  id=14 → id=2   ExxonMobil Global Services Company → ExxonMobil
  id=9  → id=8   ConocoPhillips → ConocoPhillips
  id=36 → id=34  Phillips 66 → Phillips 66
  id=41 → id=31  Sempra Energy → Sempra Energy
  id=19 → id=67  Halliburton → Halliburton
  id=48 → id=201 Worley → Worley
  id=47 → id=179 Weatherford International → Weatherford International
  id=11 → id=40  ENI Petroleum → ENI
  id=39 → id=28  Schlumberger Ltd. → SLB
  id=43 → id=214 Technip Energies → Technip Energies
  id=44 → id=110 TechnipFMC → TechnipFMC
  id=40 → id=291 Seadrill Limited → Seadrill
  id=21 → id=63  LyondellBasell → LyondellBasell
  id=8  → id=150 Chord Energy → Chord Energy
  id=24 → id=567 NCS Multistage → NCS Multistage
  id=34 → id=402 Par Pacific Holdings → Par Pacific Holdings
  id=7  → id=3   Chevron Corporation → Chevron
  id=31 → id=42  Oxy → Occidental Petroleum
  id=25 → id=168 Noble Corporation → Noble Corporation
  id=51 → id=52  Baker Hughes Inc → Baker Hughes
  id=29 → id=29  ONEOK → Oneok
  id=28 → id=587 OGE Energy → OGE Energy (stub, Tier 3)
  id=15 → id=588 Fidelis New Energy → Fidelis New Energy (stub, Tier 3)
  id=16 → id=589 Fluor Corporation → Fluor Corporation (stub, Tier 3)
  id=45 → id=590 Terraflow Energy → Terraflow Energy (stub, Tier 3)
  id=20 → id=591 Independence Power Holdings → Independence Power Holdings (stub, Tier 3)
  id=10 → id=592 Continental Resources → Continental Resources (stub, Tier 3)

Note: 6 stub company records added 2026-05-15 (ids 587–592). Created to surface CRM pipeline in the Opportunity Scorecard.
  Fluor Corporation (id=589, FLR): PRIORITY Tier 2 enrichment — $15.18B rev, Irving TX (STOLA), sub_sector=Oilfield & Energy Services, WWT addressable high $225.5M, $1.08M active pipeline. Major EPC/engineering firm (~60,000 employees globally). Promoted to data_enrichment_tier=2.
  OGE Energy (id=587, OGE): Future enrichment candidate — Oklahoma utility, $3.26B rev, 2,248 emp, WWT addressable high $39.7M, $1.29M pipeline (3.2% penetration → Warmth 3/5). HQ Oklahoma City outside STOLA.
  Continental Resources (id=592): is_private=TRUE, ticker=NULL — taken private by Harold Hamm Oct 2022. No financial enrichment possible. CRM retained for relationship tracking only ($0.07M pipeline).
  Fidelis New Energy (id=588), Terraflow Energy (id=590), Independence Power Holdings (id=591): no revenue data available; CRM pipeline only.

Pipeline for newly linked accounts (3yr rolling):
  OGE Energy: $1.29M (3.2% of $39.7M → Warmth 3/5) | Fluor Corporation: $1.08M (0.5% of $225.5M → Warmth 2/5) | Fidelis New Energy: $1.06M (fallback → Warmth 2/5)
  Terraflow Energy: $0.27M (fallback → Warmth 1/5) | Independence Power Holdings: $0.14M (fallback → Warmth 1/5) | Continental Resources: $0.07M (fallback → Warmth 1/5)

All CRM accounts are now linked (27/27). No unlinked accounts with pipeline remain.

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

## Filter Bar Standardization — COMPLETE
All pages (Companies, Territory Dashboard, CrmDashboard, Activity Feed, Analytics) audited 2026-05-14 — all already match the Analytics reference pattern (sticky horizontal, pill-style dropdowns, Reset button). No changes needed.

## Intelligence Tab Enhancements — Phase 2 COMPLETE (2026-05-14)
Built and deployed:
- FY2027E column in spend table (WWT High × 1.08, amber, tooltip)
- Opportunity Scorecard card (5 factors: Tech Maturity, Financial Capacity, Strategic Urgency, WWT Accessibility, Relationship Warmth; 1-5 bars; total /25)
  - Relationship Warmth: wired to CRM data (3yr filter). Scored by penetration ratio (pipe3yr / wwt_addressable_mid): >10%=5, 3-10%=4, 1-3%=3, 0.1-1%=2, <0.1% with pipeline=1, $0/no link=3.
  - Per-factor explanation paragraphs below each bar (12px gray, data-derived)
  - Total score narrative (italic, 12px): tier label + strongest/weakest factor + recommended action
- Signal Age Warning banner (amber, if most recent signal >90 days old)
- Per-category confidence pills (HIGH/MED/LOW inline with IT/OT/Digital/AI rows)

## Client Executive Fields — COMPLETE (2026-05-14)
ce_name VARCHAR(200), ce_email VARCHAR(200), ce_phone VARCHAR(50) added to companies table (migration 0011).
- Exposed in intelligence profile API (GET/PATCH /api/companies/{id}/profile) and companies API (GET/PUT /api/companies/{id})
- Overview tab: CE contact rows shown in Company Info card when ce_name is populated (email as mailto link)
- Edit modal: CLIENT EXECUTIVE section with name/email/phone inputs (no admin gating — no auth in frontend)
- Set values via Edit modal (PUT /api/companies/{id}) or via PATCH /api/companies/{id}/profile

Still pending (Phase 3):
- Trend arrow vs. prior estimate
- NEW badge for recent leadership hires (<18 months)
- Missing role flags (grayed-out row if no CAIO identified)
- WWT relationship context pulled from CRM (last opportunity date, pipeline, account owner)

## Opportunity Scorecard
Full rubric: backend/docs/opportunity_scorecard_rubric.md
Five factors scored 1-5, total out of 25:
- Tech Maturity: derived from maturity_score in spend estimates key_drivers (ai_maturity_score floor override via migration 0010)
- Financial Capacity: derived from revenue_ttm; denominator basis from est.step2_denominator_used
- Strategic Urgency: count of qualifying signals (leadership_hire, earnings_signal, strategic_pivot, partnership, ai_announcement) from fetched signals
- WWT Accessibility: channel_mismatch_flag + incumbent_msp + oem_direct_confirmed + territory vs tech_decision_city comparison
- Relationship Warmth: wired to CRM data via crm_accounts.energy_company_id; 3-year filter (rolling, cutoff = today − 3yr)
  - Scored by penetration ratio = 3yr open pipeline / wwt_addressable_mid: >10%=5, 3-10%=4, 1-3%=3, 0.1-1%=2, <0.1% with pipeline=1, $0 linked=2, no CRM link=3
  - wwt_addressable_mid is NOT a DB column — computed on-the-fly in _estimate() serializer as total_spend_mid × wwt_addressable_pct_low / 100
  - Frontend fallback chain: mid → wwt_addressable_high → absolute thresholds ($10M/5M/1M/0) for unenriched companies

CRM integration (2026-05-14):
- All CRM data filtered to 3-year rolling window (open pipeline + closed won >= cutoff)
- crm_summary field added to GET /api/companies/{id}/intelligence: linked, pipeline_3yr, closed_won_3yr, open_opp_count, sellers, primary_seller, top_opportunities (top 2 open opps by amount)
- CRM accounts linked via crm_accounts.energy_company_id (FK to companies.id)
- ExxonMobil CRM link: crm_accounts id=14 → energy_company_id=2, match_method=manual_confirmed, match_score=100
- ExxonMobil Bangalore DC Exit signal added (strategic_pivot, score=4, date=2026-01-01, source=crm_internal) — if exit confirmed, offshore CoE penalty (-8%) should be removed

Territory note: WWT Accessibility is evaluated against wwt_territory and tech_decision_city — NOT fixed to STOLA. Diamondback (Midland TX) = NTOLA, not a mismatch if NTOLA-assigned.

Score interpretation: 20-25 Immediate Priority, 15-19 Near-term Opportunity, 10-14 Medium-term Watch, 5-9 Low Priority.

Per-factor explanatory text: each factor renders a 12px gray explanation paragraph below the bar with data-derived context (signal count, denominator, MSP name, top opps, etc.). Total score renders a 3-sentence italic narrative: tier + strongest factor + constraint + recommended action.

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

## MSP Reference List (for enrichment validation)
When enriching any company, check for confirmed relationships with these MSPs. A confirmed relationship triggers incumbent_msp=true and -10% addressable deduction. Only flag if confirmed via WWT internal intelligence, press release, SEC filing, or credible news source. Sector inference alone is never sufficient — do not presume.

Enterprise MSPs (top priority to check — most likely at Tier 1 accounts):
Accenture, DXC Technology, HCLTech, Infosys, Capgemini, IBM, NTT Data, TCS, Wipro, CGI, Lumen Technologies

Enterprise & Mid-Market MSPs:
Abacus Group, Accucode, Advizex, Agilant Solutions, All Covered, Alphaserve Technologies, Anexinet, ANM, Applied Imaging, Arraya Solutions, ATSG, BlueAlly, Buchanan Technologies, Burwood Group, C Spire Business, Calligo, CDW Canada, CentriLogic, CGS, Clearpath Solutions Group, CompuCom, Computer Design & Integration, Computex Technology Solutions, Dataprise, designDATA, Ensono, Fidelus Technologies, Frontline Managed Services, GDT, GreenPages, Insight, InterVision Systems, iVenture Solutions, Jolera, Lemongrass, Logically, Lunavi, Magna5, Marco, Meridian IT, Microserve, Navisite, NetGain Technologies, Netrix, NexusTek, Ntiva, NWN Corporation, OneNeck, Onica, OST, Otava, Park Place Technologies, Procurri, Quest Technology Management, Reliable IT, Right! Systems, SADA, Scantron

SMB MSPs (unlikely at Tier 1 — relevant for Tier 2/3 smaller companies):
AxiaTP, Creospark, V2 Systems, Systech MSP, NuMSP, Apex Technology Corporation, Corserva

NOTE: Softchoice is a WWT company and is NEVER listed as an incumbent MSP. It represents a WWT opportunity, not a displacement challenge.

Current confirmed MSP relationships in database:
- ExxonMobil (id=2): Accenture, Deloitte, McKinsey — WWT internal confirmed
- Chevron (id=3): HCL Technologies, LTIMindtree — WWT internal confirmed
- Halliburton (id=67): Accenture — confirmed public sources (Azure migration partner + SAP S/4HANA implementation partner)

All other enriched companies: no MSP confirmed. Do not flag without confirmation.

## Consulting Firm Reference List (for enrichment validation)
When enriching any company, check for confirmed relationships with these consulting firms. A confirmed consulting relationship is noted in enrichment_notes for intelligence purposes but does NOT trigger a model deduction — consulting relationships influence vendor selection and strategy but do not displace WWT infrastructure/networking spend the way MSP relationships do. Only flag if confirmed via WWT internal intelligence, press release, SEC filing, or credible news source. Never presume.

Note: Several firms appear on both the MSP list and this list (Accenture, Capgemini, IBM, CGI, TCS, Wipro, HCLTech, Infosys, NTT Data). When a firm acts as an MSP (running IT infrastructure), apply the -10% MSP deduction. When acting as a strategy/IT consultant only, record the relationship but do not apply the deduction.

Global Strategy & Management Consulting (MBB):
McKinsey & Company, Boston Consulting Group (BCG), Bain & Company

Big Four Advisory & Strategy:
Deloitte / Monitor Deloitte, PwC / Strategy&, Ernst & Young (EY) / EY-Parthenon, KPMG Advisory

Global IT & Business Transformation Consultancies (overlap with MSP list):
Accenture, Capgemini, IBM Consulting, NTT Data, TCS, Wipro, HCLTech, Infosys Consulting, Cognizant Consulting

Elite Global Strategy & Specialty Firms:
Oliver Wyman, Kearney, Roland Berger, L.E.K. Consulting, ZS Associates, Arthur D. Little, Booz Allen Hamilton, Alvarez & Marsal, FTI Consulting, PA Consulting, Slalom Consulting, West Monroe, Protiviti, BDO Consulting, Grant Thornton Advisory

Digital, Cloud & Technology-Focused Consulting:
Publicis Sapient, EPAM Systems, Thoughtworks, Hitachi Consulting, CGI, Atos

Boutique Strategy & High-Impact Specialists:
The Cambridge Group, Innosight, Simon-Kucher & Partners, OC&C Strategy Consultants

Current confirmed consulting relationships in database:
- ExxonMobil (id=2): Deloitte (publicly cited as consulting client), McKinsey (WWT internal confirmed), Accenture (WWT internal confirmed — dual role: MSP + consulting, MSP deduction already applied)

All other enriched companies: no consulting firm relationship confirmed. Do not flag without confirmation.

## Salesforce Account to Company ID Mapping Notes
21 accounts now linked (see CRM Data Details above). Remaining known aliases still needing mapping:
- "Engie North America" (CRM) — ENGIE not found in companies table; skip or add company first
