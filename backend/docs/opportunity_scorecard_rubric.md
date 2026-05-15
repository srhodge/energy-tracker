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

Qualifying signal types: `leadership_hire`, `earnings_signal`, `strategic_pivot`, `partnership`, `ai_announcement` — any of these five types count toward the score.

| Score | Meaning | Signal count |
|-------|---------|--------------|
| 1 | No signals. Stable company with no announced changes. IT status quo likely to continue. | 0 qualifying signals |
| 2 | One signal — minor leadership change, partnership announcement, or incremental efficiency signal. | 1 qualifying signal |
| 3 | Two signals — multiple forcing functions beginning to accumulate. | 2 qualifying signals |
| 4 | Three to four signals — M&A + CEO change, or cost program + strategic pivot + leadership hire. Meaningful buying urgency. | 3–4 qualifying signals |
| 5 | Five or more signals — transformational acquisition + CEO change + strategic pivot + earnings pressure. Maximum buying urgency. | 5+ qualifying signals |

UI annotation examples:
- Score 5: "7 qualifying signals in the past 730 days. Recent signals: Bangalore DC exit; ChampionX integration."
- Score 4: "3 qualifying signals. Recent signals: ChampionX acquisition July 2025 + Azure MOU Feb 2025."
- Score 1: "0 qualifying signals — stable execution phase, no near-term IT forcing function identified."

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
Measures the current state of WWT's relationship using pipeline penetration ratio against WWT addressable mid — not absolute deal sizes. This prevents large-revenue accounts from appearing well-penetrated when deal sizes are small relative to TAM.

**Penetration ratio = 3-year rolling open pipeline / wwt_addressable_mid (computed on-the-fly as total_spend_mid × addressable_pct / 100).**

Fallback chain when estimate unavailable: mid → wwt_addressable_high → absolute thresholds ($10M/$5M/$1M/$0).
CRM data filtered to 3-year rolling window (today − 3yr). No CRM link defaults to 3 — unknown, not penalized.

| Score | Condition | Meaning |
|-------|-----------|---------|
| 5 | Penetration > 10% of WWT addressable mid | Deep strategic relationship — significant share of wallet captured |
| 4 | Penetration 3–10% | Active relationship — meaningful engagement, clear growth opportunity |
| 3 | Penetration 1–3% OR no CRM link (default) | Early relationship — transactional access, limited executive reach |
| 2 | Penetration 0.1–1% OR CRM linked with $0 pipeline | Surface relationship — present but not penetrating the account |
| 1 | Penetration <0.1% with pipeline, OR unenriched absolute fallback | Negligible — deal sizes suggest no real relationship |

UI annotation examples:
- Score 4: "$14.7M open pipeline (7.0% of $210M WWT addressable mid) — active relationship, clear growth opportunity."
- Score 2: "$7.1M open pipeline (0.9% of $814M WWT addressable mid) — surface relationship, not penetrating account relative to TAM."
- Score 3: "CRM account not yet linked — pending manual review. Pipeline data unavailable."

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
- Strategic Urgency: count of signals with type in (leadership_hire, earnings_signal, strategic_pivot, partnership, ai_announcement) in company_tech_signals; thresholds: 0=1, 1=2, 2=3, 3-4=4, 5+=5
- WWT Accessibility: derived from channel_mismatch_flag, incumbent_msp, oem_direct_confirmed, wwt_territory vs tech_decision_city
- Relationship Warmth: penetration ratio = 3yr open pipeline / wwt_addressable_mid (computed on-the-fly in _estimate() serializer; not a DB column); fallback chain: mid → wwt_addressable_high → absolute thresholds; no CRM link = 3; >10% = 5, 3–10% = 4, 1–3% = 3, 0.1–1% = 2, <0.1% with pipeline = 1, $0 pipeline = 2

---

## Real Account Examples (as of May 2026)

| Company | Pipeline | WWT Mid | Penetration | Score | Interpretation |
|---------|----------|---------|-------------|-------|----------------|
| Sempra Energy | $14.7M | $210M | 7.0% | 4/5 | Active relationship — best-penetrated large account in portfolio |
| Halliburton | $8.9M | $595M | 1.5% | 3/5 | Early relationship — transactional but growing |
| Worley | $2.3M | $148M | 1.6% | 3/5 | Early relationship — consistent small engagement |
| Weatherford | $1.9M | $160M | 1.2% | 3/5 | Early relationship — consistent small engagement |
| ExxonMobil | $7.1M | $814M | 0.9% | 2/5 | Surface relationship — $7.1M vs $814M TAM = 0.9% penetration |
| ConocoPhillips | $9.5M | $1.18B | 0.8% | 2/5 | Surface relationship — largest open pipeline, lowest % penetration |
| SLB | $2.8M | $1.84B | 0.15% | 2/5 | Surface relationship — highest TAM account, least penetrated |

**Key insight:** WWT has better penetration at mid-size accounts (Sempra, Halliburton, Worley) than at the largest TAM accounts (SLB, COP, XOM). The largest white space opportunity in the portfolio is SLB ($1.84B TAM, 0.15% penetrated) and ConocoPhillips ($1.18B TAM, 0.8% penetrated) — both Houston STOLA accounts with no MSP displacement required.
