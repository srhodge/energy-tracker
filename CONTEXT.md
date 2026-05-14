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
OEM-direct deduction: -3% (manual confirmation only — oem_direct_confirmed=true required)
Offshore CoE: -8%
Incumbent MSP: -10%
Channel mismatch: -8%
MS Standardized (Softchoice): +5%
High AI maturity (score >=15): +5%
Floor: 12%, Ceiling: 42%

Full 13-step model documentation: see WWT_Energy_Spend_Model_v4.docx

## Enrichment Status (as of May 2026)
Tier 1 (21 companies) — 21 enriched (COMPLETE):
- ExxonMobil (id=2): XOM, Integrated O&G, $323.9B rev, 58,000 employees, $1.81B WWT addressable high (12% — floor; 27%−3%OEM−8%CoE−10%MSP+5%AI=11%→floor; CoE=Bangalore Global Business & Tech Center, MSP=Accenture/Deloitte/McKinsey confirmed, ms_standardized=false, ai_maturity_score=18) [HIGH]
- Chevron (id=3): CVX, Integrated O&G, $193.4B rev, 40,000 employees, $458.4M mid / $668.5M high WWT addressable (12% — floor; 27%−3%OEM−8%CoE−10%MSP+5%MS+0%AI=11%→floor; CoE=Bengaluru ENGINE Center, MSP=HCL Technologies+LTIMindtree confirmed, ms_standardized=true, ai_maturity_score=13 below ≥15 threshold — AI bonus does not apply) [HIGH]
- ConocoPhillips (id=8): COP, Upstream E&P, $56.1B rev, 11,800 employees, $1.74B WWT addressable (37%; 27%+5%MS+5%AI=37%; ms_standardized=true, high AI maturity confirmed, oem_direct_confirmed=false) [HIGH]
- Halliburton (id=67): HAL, Oilfield & Energy Services, $22.9B rev, 48,000 employees, $610.8M WWT addressable (19%; 27%−3%OEM−10%MSP+5%MS=19%; MSP=Accenture confirmed, ms_standardized=true) [MEDIUM_HIGH]
- Phillips 66 (id=34): PSX, Downstream Refining, $143.1B rev, 13,000 employees, $2.89B WWT addressable (32%; 27%+5%MS=32%; ms_standardized=true, no MSP, oem_direct_confirmed=false) [MEDIUM_HIGH]
- Enbridge (id=12): ENB, Midstream Pipeline & Processing, $38.75B rev, 12,000 employees, $708.0M WWT addressable (24%; 27%−8%mismatch+5%MS=24%; ms_standardized=true, channel_mismatch=Calgary HQ outside STOLA territory, oem_direct_confirmed=false) [MEDIUM_HIGH]
- EOG Resources (id=21): EOG, Upstream E&P, $23.7B rev, 3,000 employees, $325.4M WWT addressable (27%; 27%=27%; ms_standardized=false, no MSP, no CoE, oem_direct_confirmed=false) [MEDIUM_HIGH]
- Targa Resources (id=53): TRGP, Midstream Pipeline & Processing, $17.0B rev, 3,570 employees, $217.9M WWT addressable (27%; 27%=27%; ms_standardized=false, no MSP, no CoE, oem_direct_confirmed=false) [MEDIUM_HIGH]
- LyondellBasell (id=63): LYB, Petrochemical & Specialty Chemicals, $37.7B rev, 26,000 employees, $804.9M WWT addressable (32%; 27%+5%MS=32%; ms_standardized=true, no MSP, no CoE, oem_direct_confirmed=false) [MEDIUM_HIGH]
- Sempra Energy (id=31): SRE, Energy Utilities, $13.185B rev, 16,773 employees, $565.7M WWT addressable (24%; 27%−8%mismatch+5%MS=24%; ms_standardized=true, channel_mismatch=San Diego HQ outside STOLA, no MSP, no CoE, oem_direct_confirmed=false) [MEDIUM_HIGH]
- Antero Resources (id=144): AR, Upstream E&P, $4.11B rev, 632 employees, $18.0M mid / $26.0M high WWT addressable (19%; 27%−8%mismatch=19%; ms_standardized=false, no MSP, no CoE, channel_mismatch=Denver HQ outside STOLA) [MEDIUM_HIGH]
- Chord Energy (id=150): CHRD, Upstream E&P, $5.25B rev, 762 employees, $32.5M mid / $47.0M high WWT addressable (27%; 27%=27%; ms_standardized=false, no MSP, no CoE, Houston HQ in STOLA) [MEDIUM_HIGH]
- CVR Energy (id=345): CVI, Downstream Refining, $7.61B rev, 1,595 employees, $59.7M mid / $83.3M high WWT addressable (27%; 27%=27%; ms_standardized=false, no MSP, no CoE, Sugar Land TX in STOLA) [MEDIUM_HIGH]
- Helmerich & Payne (id=258): HP, Oilfield & Energy Services, $2.76B rev, 6,200 employees, $26.9M mid / $38.9M high WWT addressable (19%; 27%−8%mismatch=19%; ms_standardized=false, no MSP, no CoE, channel_mismatch=Tulsa OK outside STOLA) [MEDIUM_HIGH]
- HF Sinclair (id=152): DINO, Downstream Refining, $28.57B rev, 4,800 employees, $305.3M WWT addressable (27%; 27%=27%; ms_standardized=false, no MSP, Dallas TX in STOLA, oem_direct_confirmed=false) [MEDIUM_HIGH]
- NCS Multistage (id=567): NCSM, Oilfield & Energy Services, $162.6M rev, 250 employees, $2.2M mid / $3.3M high WWT addressable (27%; 27%=27%; ms_standardized=false, Houston TX in STOLA — micro-cap, limited opportunity) [MEDIUM_HIGH]
- Par Pacific (id=402): PARR, Downstream Refining, $8.2B rev, 1,100 employees, $61.5M mid / $85.9M high WWT addressable (27%; 27%=27%; ms_standardized=false, Houston TX in STOLA) [MEDIUM_HIGH]
- PBF Energy (id=259): PBF, Downstream Refining, $33.12B rev, 3,800 employees, $241.3M WWT addressable (19%; 27%−8%mismatch=19%; ms_standardized=false, channel_mismatch=Parsippany NJ outside STOLA, oem_direct_confirmed=false) [MEDIUM_HIGH]
- Sasol (id=244): SSL, Petrochemical & Specialty Chemicals, $13.9B rev, 27,411 employees, $401.7M WWT addressable (24%; 27%−8%mismatch+5%MS=24%; ms_standardized=true, CIO confirmed, channel_mismatch=Johannesburg HQ, oem_direct_confirmed=false) [MEDIUM_HIGH]
- Technip Energies (id=214): TE, Oilfield & Energy Services, $7.61B rev, 17,000 employees, $88.4M mid / $127.7M high WWT addressable (19%; 27%−8%mismatch=19%; ms_standardized=false, channel_mismatch=France HQ) [MEDIUM_HIGH]
- TechnipFMC (id=110): FTI, Oilfield & Energy Services, $9.08B rev, 21,000 employees, $116.9M mid / $168.9M high WWT addressable (19%; 27%−8%mismatch=19%; ms_standardized=false, channel_mismatch=UK HQ, Datagration AI acquisition) [MEDIUM_HIGH]
- Weatherford (id=179): WFRD, Oilfield & Energy Services, $5.4B rev, 17,000 employees, $140.4M mid / $204.3M high WWT addressable (27%; 27%=27%; ms_standardized=false, Houston HQ in STOLA, Datagration AI acquisition, CEO digitalization mandate) [MEDIUM_HIGH]
- Worley (id=201): WOR, Oilfield & Energy Services, $8.24B rev, 45,505 employees, $147.9M mid / $213.6M high WWT addressable (19%; 27%−8%mismatch=19%; ms_standardized=false, channel_mismatch=Sydney Australia HQ) [MEDIUM_HIGH]

Tier 1 remaining: NONE — all 21 companies enriched.

Tier 2 (US companies by revenue) — enrichment begun May 2026:
- Marathon Petroleum (id=38): MPC, Downstream Refining, $135.95B rev, 16,738 employees, $1.86B WWT addressable (24%; 27%−8%mismatch+5%MS=24%; CDO Ehren Powell confirmed since 2020, new CEO Maryann Mannen Aug 2024 from TechnipFMC, ms_standardized=true, channel_mismatch=Findlay OH outside STOLA, Imubit AI deployed, MPLX AI data center pivot 2025, ai_maturity=13) [HIGH]
- Valero Energy (id=50): VLO, Downstream Refining, $117.84B rev, 9,811 employees, $1.44B WWT addressable (27%; 27%=27%; no CIO/CDO — VP Technology only, no cloud/MSP/AI programs confirmed, San Antonio TX in STOLA, ai_maturity=6) [MEDIUM_HIGH]
- SLB (id=28): SLB, Oilfield & Energy Services, $35.94B rev, 113,000 employees, $1.61B WWT addressable (37%; 27%+5%MS+5%AI=37%; CEO Olivier Le Peuch drives digital-first, $2.44B digital revenue FY2024, NVIDIA partnership, ChampionX acquisition July 2025, ms_standardized=true, Houston HQ in STOLA, ai_maturity=19 — highest in Tier 2 set) [HIGH]
- Occidental Petroleum (id=42): OXY, Upstream E&P, $26.72B rev, 12,000 employees, $529.9M WWT addressable (32%; 27%+5%MS=32%; CEO Vicki Hollub, ruthless automation 40% Permian production automated, CrownRock acquisition Aug 2024 IT integration demand, ms_standardized=true, Houston HQ in STOLA, ai_maturity=13) [MEDIUM_HIGH]
- Baker Hughes (id=52): BKR, Oilfield & Energy Services, $27.83B rev, 58,000 employees, $1.16B WWT addressable (37%; 27%+5%MS+5%AI=37%; CEO Lorenzo Simonelli, Azure MOU Feb 2025 + AI Foundry integration, Cordant bp enterprise contract, C3 AI partnership, ms_standardized=true, Houston HQ in STOLA, ai_maturity=16) [HIGH]
- Williams Companies (id=23): WMB, Midstream Pipeline & Processing, $10.5B rev, 5,829 employees, $123.2M WWT addressable (19%; 27%−8%mismatch=19%; new CEO Chad Zamarin July 2025, $3.1B AI data center power commitment Socrates project, ms_standardized=false, channel_mismatch=Tulsa OK outside STOLA, ai_maturity=9) [MEDIUM_HIGH]
- ONEOK (id=29): OKE, Midstream Pipeline & Processing, $35.2B rev, 6,326 employees, $376.8M WWT addressable (19%; 27%−8%mismatch=19%; CEO Pierce Norton, satellite emissions detection deployed, 4 simultaneous M&A integrations (Magellan/EnLink/Medallion/Gulf Coast NGL) = highest IT integration demand in midstream, channel_mismatch=Tulsa OK, ms_standardized=false, ai_maturity=7) [MEDIUM_HIGH]
- Energy Transfer (id=27): ET, Midstream Pipeline & Processing, $92.29B rev, 12,000 employees, $1.04B WWT addressable (27%; 27%=27%; Co-CEO Tom Long, AI data center power positioning, Lake Charles LNG 20-yr Chevron SPA, Dallas TX in STOLA, ms_standardized=false, ai_maturity=5) [MEDIUM_HIGH]
- Devon Energy (id=66): DVN, Upstream E&P, $16.0B rev, 4,500 employees, $207.3M WWT addressable (24%; 27%−8%mismatch+5%MS=24%; CTO Trey Lowe confirmed, AI/automation/RPA named as core competencies, Databricks+Azure+SAP HANA confirmed, new CEO Clay Gaspar 2025 + $1B business optimization, channel_mismatch=OKC outside STOLA, ms_standardized=true, ai_maturity=11) [MEDIUM_HIGH]
- Enterprise Products Partners (id=24): EPD, Midstream Pipeline & Processing, $51.56B rev, 7,500 employees, $589.2M WWT addressable (27%; 27%=27%; no CIO/technology leadership identified, AI data center power positioning is energy revenue play not internal IT, Houston HQ in STOLA, ms_standardized=false, ai_maturity=6) [MEDIUM_HIGH]
- Cheniere Energy (id=70): LNG, Midstream Pipeline & Processing, $15.1B rev, 1,717 employees, $169.3M WWT addressable (27%; 27%=27%; 1,717 employees extremely lean for Fortune 500, Corpus Christi Stage 3 expansion = near-term IT/OT demand, Houston HQ in STOLA, ms_standardized=false, ai_maturity=6) [MEDIUM_HIGH]
- Diamondback Energy (id=32): FANG, Upstream E&P, $14.46B rev, 1,983 employees, $98.0M WWT addressable (19%; 27%−8%mismatch=19%; electric simul-frac VoltaGrid+Halliburton 200MW, real-time methane monitoring 87% production, $26B Endeavor merger IT integration, channel_mismatch=Midland TX West Texas, ms_standardized=false, ai_maturity=8) [MEDIUM_HIGH]

## Enrichment Workflow
1. I (Claude in new chat) research company via web search
2. Generate enrichment JSON
3. User pastes JSON instruction into Claude Code
4. Claude Code writes file + runs patch_company.py against production API
5. Claude Code runs run_estimates.py --company-id N

After every enrichment: auto-update CONTEXT.md + commit + push without being asked.

OEM deduction rule: oem_direct_deduction is manual-confirmation only — same standard as incumbent_msp. Never auto-applied by revenue threshold. Confirmed YES: ExxonMobil, Chevron, Halliburton. All others confirmed NO or pending assessment.

## Pending Work
1. Tier 1 enrichment COMPLETE — begin Tier 2 US companies
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
The 83 CRM accounts use slightly different names than the 585 companies database.
Known aliases needing manual mapping when ready:
- "Oxy" = Occidental Petroleum
- "ExxonMobil Global Services Company" = ExxonMobil (id=2)
- "Engie North America" = ENGIE
- "ONEOK" = ONEOK (may not exist in companies DB)
- "Baker Hughes Inc" vs "Baker Hughes"
- "Schlumberger Ltd." vs "Schlumberger/SLB"
