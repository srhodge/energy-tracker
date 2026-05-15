# WWT Energy Tracker — Opportunity Scorecard Rubric
## Version 1.0 — May 2026

The Opportunity Scorecard rates each company 1-5 across five factors for a total score out of 25. Scores are designed to reflect WWT-specific commercial context, not generic CRM scoring. The right-side annotations in the UI pull live data from the database to explain each score.

---

## Factor 1: Tech Maturity (1-5)
Measures how advanced the company's internal IT/AI organization is — determines whether WWT's AI, infrastructure, and digital offerings will resonate.

| Score | Meaning | Typical signals |
|-------|---------|-----------------|
| 1 | No CIO/CDO identified, no public AI programs, no cloud platform confirmed, <500 IT staff implied. Technology is purely operational/maintenance. | No leadership in DB, ai_maturity_score <5 |
| 2 | CIO exists but low profile. Some technology modernization underway but no AI programs, no cloud strategy confirmed. Reactionary IT culture. | CIO confirmed, signal_score low, no cloud platform |
| 3 | Confirmed CIO/CDO, cloud platform in use (Azure/AWS), ERP modernization (SAP). Technology is enabling but not differentiating. No AICOE or AI at scale. | ai_maturity_score 6-8, cloud confirmed |
| 4 | Active AI program with confirmed deployments, strong CIO externally visible (ORBIE, Gartner), cloud-first strategy, data analytics platform in production. | ai_maturity_score 12-14, recognition signals |
| 5 | AICOE or equivalent, AI generating measurable business outcomes, CAIO or equivalent role, NVIDIA/hyperscaler strategic partnership. Board-level AI oversight. | ai_maturity_score ≥15, NVIDIA partnership, CAIO confirmed |

UI annotation examples:
- Score 5: "AI maturity score 19 — Delfi platform 6,500+ users, NVIDIA partnership, $2.44B digital revenue"
- Score 4: "AI maturity score 18 — AICOE confirmed, Discovery 6 supercomputer (HPE+NVIDIA), CAIO Irtefa Binte-Farid"
- Score 1: "AI maturity score 3 — no CIO identified, no public AI programs"

---

## Factor 2: Financial Capacity (1-5)
Measures the company's ability to fund significant IT/infrastructure investment — financial health and investment posture, not just revenue size.

| Score | Meaning | Typical signals |
|-------|---------|-----------------|
| 1 | Revenue <$1B or financial distress, bankruptcy emergence, or highly leveraged. Minimal discretionary IT budget. | revenue_ttm <1B, high debt load |
| 2 | Revenue $1-5B, lean workforce, conservative culture, founder-controlled or cost-focused. IT spend is maintenance-oriented. | employee_count <1000, no capex program |
| 3 | Revenue $5-15B, stable financials, normal IT investment cycle. No major capex program or transformation announced. | revenue_ttm $5-15B, no active signals |
| 4 | Revenue $15-50B, healthy EBITDA margins, active capex cycle or transformation program. IT investment explicitly part of strategy. | revenue_ttm $15-50B, capex signal active |
| 5 | Revenue >$50B (or large EBITDA base), record capex plans, M&A-driven growth requiring IT integration, AI budget explicitly named in investor communications. | revenue_ttm >50B, M&A signal, earnings_signal |

UI annotation examples:
- Score 5: "$323.9B revenue — record capex, Pioneer integration active"
- Score 2: "$3.2B revenue, 700 employees — lean E&P, conservative culture"

---

## Factor 3: Strategic Urgency (1-5)
Measures how many near-term forcing functions exist that create IT buying pressure — M&A integration, CEO change, cost programs, competitive threats, regulatory change.

| Score | Meaning | Qualifying signals |
|-------|---------|-------------------|
| 1 | No signals. Stable company with no announced changes. IT status quo likely to continue. | 0 active signals in company_tech_signals |
| 2 | One minor signal — small acquisition, minor leadership change, or incremental efficiency program. | 1 low-score signal |
| 3 | One significant signal — major acquisition integration, new CEO within 18 months, or large cost savings program. | 1 strategic_pivot or career_move signal |
| 4 | Two significant signals — e.g. M&A + CEO change, or cost program + strategic pivot. Multiple forcing functions. | 2+ strategic_pivot or M&A signals |
| 5 | Three or more active signals — transformational acquisition + CEO change + strategic pivot + earnings pressure. Maximum buying urgency. | 3+ high-score signals within 730 days |

UI annotation examples:
- Score 4: "ChampionX acquisition July 2025 + Azure MOU Feb 2025 — active IT integration and vendor engagement"
- Score 1: "0 qualifying signals — stable execution phase, no near-term IT forcing function identified"

---

## Factor 4: WWT Accessibility (1-5)
Measures how easy it is for WWT to engage this account — territory alignment, absence of incumbents, and relationship barriers. Territory is assessed against the company's wwt_territory field and tech_decision_city, NOT fixed to STOLA.

| Score | Meaning | Conditions |
|-------|---------|------------|
| 1 | Tech decisions outside any WWT territory AND confirmed incumbent MSP displacing WWT. Very high barriers. | channel_mismatch=true AND incumbent_msp=true |
| 2 | Either channel mismatch OR incumbent MSP — one major barrier. Engagement requires displacement or territory exception. | channel_mismatch=true OR incumbent_msp=true |
| 3 | In WWT territory but has incumbent MSP, OR outside territory but no MSP. One barrier only. | Single barrier present |
| 4 | In WWT territory, no incumbent MSP, but OEM-direct purchasing confirmed or limited WWT relationship history. | oem_direct_confirmed=true, no MSP |
| 5 | In WWT territory, no incumbent MSP, no OEM-direct, no channel mismatch, CE assigned or known strategic alignment. | All flags clear, ce_name populated or strategic alignment noted |

Territory note: Channel mismatch is evaluated against the company's assigned wwt_territory and tech_decision_city — not fixed to STOLA. Example: Diamondback Energy (Midland TX) = NTOLA territory, not a mismatch if account is NTOLA-assigned.

UI annotation examples:
- Score 1: "MSP: Accenture, Deloitte, McKinsey — channel mismatch: Calgary HQ outside WWT territory"
- Score 5: "Houston STOLA — no MSP, no OEM-direct, CE assigned: [Name]"
- Score 3: "MSP: Accenture confirmed — Houston STOLA territory clear"

---

## Factor 5: Relationship Warmth (1-5)
Measures the current state of WWT's relationship — CRM pipeline, open opportunities, recent wins, CE assignment, and executive contacts.

| Score | Meaning | Data source |
|-------|---------|-------------|
| 1 | No CRM data, no CE assigned, no known WWT relationship. Cold account. | No CRM link, ce_name NULL |
| 2 | CRM account exists but $0 pipeline, placeholder only. No active seller engagement confirmed. | crm_accounts linked, $0 pipeline |
| 3 | Default — CRM account with historical activity or open opportunities but no recent wins or executive relationship. | crm_opportunities exist, no recent closed-won |
| 4 | Active CRM pipeline with open opportunities, CE assigned, recent activity within 12 months. | ce_name populated + active opportunities |
| 5 | Significant open pipeline, recent closed-won, executive relationship confirmed, or internal WWT strategic alignment noted. | Large pipeline + closed-won + strategic alignment flag |

UI annotation examples:
- Score 4: "CE: Sam Hodge — 3 open opportunities, last activity March 2026"
- Score 3: "No data — default score pending CRM link"
- Score 5: "Halliburton strategic alignment confirmed — expressed desire for WWT partnership (internal)"

---

## Total Score Interpretation
The total score narrative synthesizes the pattern across all five factors — the same total score can mean very different things depending on which factors are high vs. low.

| Total | Tier | Narrative approach |
|-------|------|-------------------|
| 20-25 | Immediate Priority | Multiple strong signals across categories. Identify the #1 recommended engagement action based on highest-scoring factors. |
| 15-19 | Near-term Opportunity | Solid foundation with 1-2 specific constraints. Identify exactly what would unlock the account. |
| 10-14 | Medium-term Watch | Meaningful potential but real barriers. Identify the trigger event that would move this to priority. |
| 5-9 | Low Near-term Priority | Significant constraints across multiple dimensions. Honest about why patience or a different entry point is required. |

The narrative should always:
1. Name the single biggest strength driving the score
2. Name the single biggest constraint limiting the score
3. Recommend one specific WWT engagement action

Example narratives:
- XOM 16/25: "Strong AI and financial foundation but zero strategic urgency and MSP incumbency. WWT posture: relationship-building now via NVIDIA/AI Proving Ground angle, positioned for next M&A or CEO transition event."
- SLB 22/25: "Maximum tech maturity and clean Houston accessibility — ChampionX integration creates immediate IT demand. Recommended action: executive engagement Q2 2026 focused on Delfi AI Foundry expansion and connected asset infrastructure."

---

## Scoring Implementation Notes
- Tech Maturity: derived from maturity_score in company_spend_estimates.key_drivers
- Financial Capacity: derived from revenue_ttm on companies table
- Strategic Urgency: count of active signals (strategic_pivot, career_move, partnership, earnings_signal) within 730 days in company_tech_signals
- WWT Accessibility: derived from channel_mismatch_flag, incumbent_msp, oem_direct_confirmed, wwt_territory vs tech_decision_city
- Relationship Warmth: derived from CRM link status, ce_name, open opportunities in crm_opportunities
