"""
Technology spend estimation engine — v4.0 model.

13-step model producing low/mid/high IT, OT, Digital, and AI spend
estimates plus a 1-year forward estimate (step 11).
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Company, CompanyStatus, Financial,
    CompanyLeadership, CompanyTechSignal, CompanySpendEstimate, CompanyAsset,
)

# ── STEP 1: Baseline percentages by sub_sector ────────────────────────────────
# Each entry: (IT, OT, Digital, AI) — each a (low%, mid%, high%) tuple
_BASELINE: dict[str, tuple[tuple, tuple, tuple, tuple]] = {
    "Integrated O&G":                      ((0.8,1.3,1.8),   (0.4,0.8,1.2),  (0.3,0.6,0.9),  (0.2,0.45,0.7)),
    "Upstream E&P":                        ((0.9,1.55,2.2),  (0.8,1.4,2.0),  (0.4,0.8,1.2),  (0.3,0.65,1.0)),
    "Midstream Pipeline & Processing":     ((1.2,2.0,2.8),   (1.2,2.0,2.8),  (0.5,0.95,1.4), (0.3,0.65,1.0)),
    "Downstream Refining":                 ((1.2,1.8,2.4),   (1.2,2.0,2.8),  (0.4,0.8,1.2),  (0.3,0.6,0.9)),
    "Petrochemical & Specialty Chemicals": ((1.3,2.05,2.8),  (1.3,2.05,2.8), (0.6,1.1,1.6),  (0.4,0.8,1.2)),
    "Oilfield & Energy Services":          ((1.8,2.8,3.8),   (0.6,1.2,1.8),  (0.8,1.5,2.2),  (0.6,1.4,2.2)),
    "Energy Utilities":                    ((1.8,2.5,3.2),   (1.3,2.25,3.2), (0.8,1.4,2.0),  (0.6,1.2,1.8)),
    "Renewable & New Energy":              ((1.4,2.1,2.8),   (0.4,1.1,1.8),  (1.2,2.2,3.2),  (0.8,1.8,2.8)),
    "Energy Infrastructure & Power":       ((1.5,2.25,3.0),  (1.5,2.5,3.5),  (1.5,2.5,3.5),  (1.0,2.0,3.0)),
    "Carbon Management":                   ((1.2,1.85,2.5),  (0.8,1.4,2.0),  (1.5,2.5,3.5),  (1.2,2.1,3.0)),
    "LNG & Gas Trading":                   ((1.4,2.1,2.8),   (1.0,1.6,2.2),  (0.8,1.4,2.0),  (0.5,1.0,1.5)),
}
_DEFAULT_BASELINE = ((1.0,1.75,2.5), (0.8,1.4,2.0), (0.5,1.0,1.5), (0.3,0.65,1.0))

# ── STEP 3: Regional multipliers ─────────────────────────────────────────────
_REGIONAL: dict[str, float] = {
    "Norway": 1.25, "Netherlands": 1.20, "Germany": 1.18,
    "United Kingdom": 1.18, "UK": 1.18, "France": 1.15,
    "Sweden": 1.15, "Denmark": 1.15,
    "Saudi Arabia": 1.30, "UAE": 1.30, "United Arab Emirates": 1.30,
    "Qatar": 1.25, "Kuwait": 1.20, "Oman": 1.15,
    "Australia": 1.05, "Japan": 1.10, "South Korea": 1.10,
    "Canada": 0.92, "USA": 1.0, "United States": 1.0,
    "Brazil": 0.80, "India": 0.75, "China": 0.78,
}

# ── STEP 4: Per-employee total spend benchmarks (USD/head across all categories)
_EMPLOYEE_BENCHMARK: dict[str, int] = {
    "Integrated O&G":                      25000,
    "Upstream E&P":                        35000,
    "Midstream Pipeline & Processing":     45000,
    "Downstream Refining":                 42000,
    "Petrochemical & Specialty Chemicals": 52000,
    "Oilfield & Energy Services":          28000,
    "Energy Utilities":                    55000,
    "Renewable & New Energy":              48000,
    "Energy Infrastructure & Power":       65000,
}
_DEFAULT_EMPLOYEE_BENCHMARK = 30000

# ── STEP 5: Asset score → category uplift functions ───────────────────────────
def _asset_mult_it(score: int) -> float:
    if score <= 10: return 1.0
    if score <= 16: return 1.1
    return 1.2

def _asset_mult_ot(score: int) -> float:
    if score <= 15: return 1.0
    if score <= 30: return 1.2
    if score <= 40: return 1.4
    return 1.6

def _asset_mult_dig(score: int) -> float:
    if score <= 10: return 1.0
    if score <= 18: return 1.2
    if score <= 25: return 1.4
    return 1.6

def _asset_mult_ai(score: int) -> float:
    if score <= 10: return 1.0
    if score <= 18: return 1.2
    if score <= 25: return 1.5
    return 1.8

# ── STEP 6: Maturity score → category multipliers ────────────────────────────
def _maturity_mults(score: int) -> tuple[float, float, float, float]:
    if score <= 3:  return (0.8, 1.0, 0.6, 0.6)
    if score <= 6:  return (1.0, 1.0, 1.0, 1.0)
    if score <= 10: return (1.2, 1.1, 1.5, 1.5)
    if score <= 14: return (1.3, 1.2, 1.8, 1.8)
    return (1.5, 1.3, 2.5, 2.5)

# ── STEP 7: ESG digital multiplier delta by country ──────────────────────────
_ESG_DIGITAL_DELTA: dict[str, float] = {
    "Norway": 0.15, "Netherlands": 0.15, "Germany": 0.15,
    "United Kingdom": 0.15, "UK": 0.15, "France": 0.15,
    "United States": -0.05, "USA": -0.05,
    "Saudi Arabia": 0.20, "UAE": 0.20, "United Arab Emirates": 0.20, "Qatar": 0.20,
}


def _f(v) -> Optional[float]:
    if v is None:
        return None
    return float(v)


def estimate(company_id: int, db: Session) -> dict:
    """Run the v4.0 spend model. Writes current_year + forward_1yr rows. Returns current_year dict."""
    c = db.get(Company, company_id)
    if not c:
        raise ValueError(f"Company {company_id} not found")
    if c.status != CompanyStatus.active:
        raise ValueError(f"Company {company_id} ({c.name}) is not active (status={c.status.value})")

    # ── STEP 1: baseline pcts ─────────────────────────────────────────────────
    it_pcts, ot_pcts, dig_pcts, ai_pcts = _BASELINE.get(c.sub_sector or "", _DEFAULT_BASELINE)
    step1_value_chain = c.sub_sector or "default"

    # ── STEP 2: Revenue Denominator Selection ────────────────────────────────
    # Sub-sector-specific denominators are applied to improve accuracy.
    # Midstream: EBITDA × 2.5 (commodity pass-through revenue is misleading)
    # Downstream Refining: Gross Profit (thin margins make revenue a poor IT proxy;
    #     refiners create real value but capture little of commodity cost)
    # Regulated Utilities: EBITDA × 2.5 (rate-base model; revenue set by regulators not market)
    # Integrated O&G: 50/50 revenue + EBITDA blend
    # All others: Revenue (appropriate for services, E&P, chemicals)
    rev    = _f(c.revenue_ttm)
    ebitda = _f(c.ebitda_ttm)
    gp     = _f(c.gross_profit_ttm)

    ebitda_scales: Optional[tuple[float, float, float]] = None
    denom_used = "none"
    denominator_basis = "none"
    denominator_low = denominator_mid = denominator_high = None

    sub = c.sub_sector or ""

    if sub == "Midstream Pipeline & Processing":
        if ebitda is not None and ebitda > 0:
            d = ebitda * 2.5
            denominator_low = denominator_mid = denominator_high = d
            denom_used = "ebitda_x2.5"
            denominator_basis = "EBITDA × 2.5"
        elif rev is not None:
            d = rev * 0.12
            denominator_low = denominator_mid = denominator_high = d
            denom_used = "revenue_x0.12"
            denominator_basis = "Revenue × 0.12"

    elif sub == "Downstream Refining":
        if gp is not None and gp > 0:
            denominator_low = denominator_mid = denominator_high = gp
            denom_used = "gross_profit"
            denominator_basis = "Gross Profit"
        elif ebitda is not None and ebitda > 0:
            d = ebitda * 1.5
            denominator_low = denominator_mid = denominator_high = d
            denom_used = "ebitda_x1.5"
            denominator_basis = "EBITDA × 1.5"
        elif rev is not None:
            d = rev * 0.06
            denominator_low = denominator_mid = denominator_high = d
            denom_used = "revenue_x0.06"
            denominator_basis = "Revenue × 0.06"

    elif sub == "Energy Utilities":
        if ebitda is not None and ebitda > 0:
            d = ebitda * 2.5
            denominator_low = denominator_mid = denominator_high = d
            denom_used = "ebitda_x2.5"
            denominator_basis = "EBITDA × 2.5"
        elif rev is not None:
            d = rev * 0.35
            denominator_low = denominator_mid = denominator_high = d
            denom_used = "revenue_x0.35"
            denominator_basis = "Revenue × 0.35"

    elif sub == "Integrated O&G":
        if rev is not None and ebitda is not None:
            d = rev * 0.5 + ebitda * 0.5
            denominator_low = denominator_mid = denominator_high = d
            denom_used = "blended_50_50"
            denominator_basis = "50% Revenue + 50% EBITDA"
        elif rev is not None:
            denominator_low = denominator_mid = denominator_high = rev
            denom_used = "revenue"
            denominator_basis = "Revenue"

    else:
        # Upstream E&P, OFS, Petrochemicals, Renewable & New Energy, etc.
        if rev is not None:
            denominator_low = denominator_mid = denominator_high = rev
            denom_used = "revenue"
            denominator_basis = "Revenue"

    private_mult = 0.75 if c.is_pe_backed else (0.85 if c.is_private else 1.0)

    # ── STEP 3: regional multiplier ───────────────────────────────────────────
    regional_mult = _REGIONAL.get(c.country or "", 1.0)

    # ── STEP 6: digital maturity (score from leadership + recent signals) ─────
    leadership_rows = db.scalars(
        select(CompanyLeadership).where(
            CompanyLeadership.company_id == company_id,
            CompanyLeadership.is_current == True,
        )
    ).all()
    leadership_score = sum(r.signal_score or 0 for r in leadership_rows)

    cutoff_1yr = date.today() - timedelta(days=365)
    positive_signal_rows = db.scalars(
        select(CompanyTechSignal).where(
            CompanyTechSignal.company_id == company_id,
            CompanyTechSignal.signal_type.in_(["partnership", "ai_announcement", "leadership_hire"]),
            CompanyTechSignal.signal_date >= cutoff_1yr,
        )
    ).all()
    signal_score = sum(max(0, r.score_points or 0) for r in positive_signal_rows)
    maturity_score = leadership_score + signal_score
    it_mat, ot_mat, dig_mat, ai_mat = _maturity_mults(maturity_score)

    # ── STEP 9: financial health ──────────────────────────────────────────────
    latest_fin = db.scalars(
        select(Financial)
        .where(Financial.company_id == company_id, Financial.ps_ratio.isnot(None))
        .order_by(Financial.snapshot_date.desc())
        .limit(1)
    ).first()

    fin_adj = 0.0
    if latest_fin and latest_fin.ps_ratio and latest_fin.ps_ratio_5yr_avg and latest_fin.ps_ratio_5yr_avg != 0:
        ratio = latest_fin.ps_ratio / latest_fin.ps_ratio_5yr_avg
        if ratio > 1.5:     fin_adj = 0.15
        elif ratio >= 1.0:  fin_adj = 0.05
        elif ratio >= 0.75: fin_adj = 0.0
        elif ratio >= 0.5:  fin_adj = -0.10
        else:               fin_adj = -0.20

    # ── Apply baseline to get initial dollar amounts (steps 1-3, 6, 9) ───────
    def _apply(pcts, cat_mat, d_lo, d_mi, d_hi):
        if d_lo is None:
            return (None, None, None)
        pl, pm, ph = pcts
        es = ebitda_scales
        el = es[0] if es else 1.0
        em = es[1] if es else 1.0
        eh = es[2] if es else 1.0
        shared = private_mult * regional_mult * cat_mat * (1.0 + fin_adj)
        return (
            d_lo * (pl / 100) * el * shared,
            d_mi * (pm / 100) * em * shared,
            d_hi * (ph / 100) * eh * shared,
        )

    it_low,  it_mid,  it_high  = _apply(it_pcts,  it_mat,  denominator_low, denominator_mid, denominator_high)
    ot_low,  ot_mid,  ot_high  = _apply(ot_pcts,  ot_mat,  denominator_low, denominator_mid, denominator_high)
    dig_low, dig_mid, dig_high = _apply(dig_pcts, dig_mat, denominator_low, denominator_mid, denominator_high)
    ai_low,  ai_mid,  ai_high  = _apply(ai_pcts,  ai_mat,  denominator_low, denominator_mid, denominator_high)

    flags: dict = {
        "no_revenue":    rev is None,
        "no_sub_sector": c.sub_sector is None,
        "no_country":    c.country is None,
        "is_private":    bool(c.is_private),
        "is_pe_backed":  bool(c.is_pe_backed),
        "ebitda_mode":   denom_used not in ("revenue", "none"),
    }

    # ── STEP 4: employee count cross-check ────────────────────────────────────
    step4_employee_derived: Optional[float] = None
    step4_scale_factor = 1.0
    if c.employee_count and it_mid is not None:
        benchmark = _EMPLOYEE_BENCHMARK.get(c.sub_sector or "", _DEFAULT_EMPLOYEE_BENCHMARK)
        emp_total = float(c.employee_count) * benchmark
        rev_total = it_mid + ot_mid + dig_mid + ai_mid
        step4_employee_derived = emp_total
        if rev_total > 0:
            divergence = abs(emp_total - rev_total) / rev_total
            if divergence > 0.40:
                blended_total = rev_total * 0.6 + emp_total * 0.4
                step4_scale_factor = blended_total / rev_total
                sf = step4_scale_factor
                it_low,  it_mid,  it_high  = it_low*sf,  it_mid*sf,  it_high*sf
                ot_low,  ot_mid,  ot_high  = ot_low*sf,  ot_mid*sf,  ot_high*sf
                dig_low, dig_mid, dig_high = dig_low*sf, dig_mid*sf, dig_high*sf
                ai_low,  ai_mid,  ai_high  = ai_low*sf,  ai_mid*sf,  ai_high*sf
                flags["employee_revenue_divergence"] = True

    # ── STEP 5: asset footprint scoring ──────────────────────────────────────
    step5_applied = False
    asset_rows = db.scalars(
        select(CompanyAsset).where(CompanyAsset.company_id == company_id)
    ).all()
    if asset_rows and it_mid is not None:
        cat = lambda a, name: (a.asset_category or "").upper() == name
        it_sc  = sum(a.asset_score or 0 for a in asset_rows if cat(a, "IT"))
        ot_sc  = sum(a.asset_score or 0 for a in asset_rows if cat(a, "OT"))
        dig_sc = sum(a.asset_score or 0 for a in asset_rows if cat(a, "DIGITAL") or cat(a, "DIG"))
        ai_sc  = sum(a.asset_score or 0 for a in asset_rows if cat(a, "AI"))
        itm  = _asset_mult_it(it_sc)
        otm  = _asset_mult_ot(ot_sc)
        digm = _asset_mult_dig(dig_sc)
        aim  = _asset_mult_ai(ai_sc)
        it_low,  it_mid,  it_high  = it_low*itm,  it_mid*itm,  it_high*itm
        ot_low,  ot_mid,  ot_high  = ot_low*otm,  ot_mid*otm,  ot_high*otm
        dig_low, dig_mid, dig_high = dig_low*digm, dig_mid*digm, dig_high*digm
        ai_low,  ai_mid,  ai_high  = ai_low*aim,  ai_mid*aim,  ai_high*aim
        step5_applied = True

    # ── STEP 7: regulatory and cyber pressure ────────────────────────────────
    cutoff_3yr = date.today() - timedelta(days=3 * 365)
    cyber_rows = db.scalars(
        select(CompanyTechSignal).where(
            CompanyTechSignal.company_id == company_id,
            CompanyTechSignal.signal_type == "cyber_incident",
            CompanyTechSignal.signal_date >= cutoff_3yr,
        )
    ).all()
    step7_cyber_flag = len(cyber_rows) > 0
    if step7_cyber_flag and it_mid is not None:
        it_low, it_mid, it_high = it_low + 50_000_000, it_mid + 50_000_000, it_high + 50_000_000
        flags["recent_cyber_incident"] = True

    esg_delta = _ESG_DIGITAL_DELTA.get(c.country or "", 0.0)
    step7_esg_multiplier = 1.0 + esg_delta
    if esg_delta != 0.0 and dig_mid is not None:
        m = step7_esg_multiplier
        dig_low, dig_mid, dig_high = dig_low * m, dig_mid * m, dig_high * m

    # ── STEP 8: M&A activity and strategic pivots ────────────────────────────
    cutoff_2yr = date.today() - timedelta(days=2 * 365)
    pivot_rows = db.scalars(
        select(CompanyTechSignal).where(
            CompanyTechSignal.company_id == company_id,
            CompanyTechSignal.signal_type.in_(["m_and_a", "strategic_pivot"]),
            CompanyTechSignal.signal_date >= cutoff_2yr,
        )
    ).all()

    up_mult   = 1.0
    down_mult = 1.0
    step8_pivot_count = 0
    for sig in pivot_rows:
        if sig.spend_impact_direction == "increase":
            up_mult = min(up_mult * 1.08, 1.35)
            step8_pivot_count += 1
        elif sig.spend_impact_direction == "decrease":
            down_mult = max(down_mult * 0.95, 0.80)

    step8_ma_uplift = up_mult * down_mult
    if step8_ma_uplift != 1.0 and it_mid is not None:
        m = step8_ma_uplift
        it_low,  it_mid,  it_high  = it_low*m,  it_mid*m,  it_high*m
        ot_low,  ot_mid,  ot_high  = ot_low*m,  ot_mid*m,  ot_high*m
        dig_low, dig_mid, dig_high = dig_low*m, dig_mid*m, dig_high*m
        ai_low,  ai_mid,  ai_high  = ai_low*m,  ai_mid*m,  ai_high*m
    if step8_pivot_count > 0:
        flags["strategic_pivot_active"] = True

    # ── Round ─────────────────────────────────────────────────────────────────
    def _rnd(v): return round(v, 2) if v is not None else None

    it_low,  it_mid,  it_high  = _rnd(it_low),  _rnd(it_mid),  _rnd(it_high)
    ot_low,  ot_mid,  ot_high  = _rnd(ot_low),  _rnd(ot_mid),  _rnd(ot_high)
    dig_low, dig_mid, dig_high = _rnd(dig_low), _rnd(dig_mid), _rnd(dig_high)
    ai_low,  ai_mid,  ai_high  = _rnd(ai_low),  _rnd(ai_mid),  _rnd(ai_high)

    total_low = total_mid = total_high = None
    wwt_low = wwt_high = None

    if it_low is not None:
        total_low  = round(it_low  + ot_low  + dig_low  + ai_low,  2)
        total_mid  = round(it_mid  + ot_mid  + dig_mid  + ai_mid,  2)
        total_high = round(it_high + ot_high + dig_high + ai_high, 2)

    # ── STEP 10: WWT Addressable Share ────────────────────────────────────────
    # Base 27% reflects partner-channel addressable categories only:
    # hardware (partner portion), networking, IT security, OT security,
    # cloud infrastructure, AI infrastructure, Microsoft (via Softchoice).
    #
    # Already EXCLUDED from the 27% base (non-addressable, never counted):
    #   - Internal IT labor (28-38% of total budget)
    #   - SAP/Oracle direct licensing (go-to-market bypasses WWT)
    #   - Seismic software (SLB Petrel, HAL Landmark — direct vendor)
    #   - Specialized process control (AspenTech, Honeywell UniSim — direct)
    #
    # Additional deductions applied below:
    #   - OEM-direct hardware: -3% (large enterprise >$10B, Gartner research)
    #   - Offshore CoE: -8% (confirmed India delivery center)
    #   - Incumbent MSP: -10% (confirmed managed services contract)
    #   - Channel mismatch: -8% (tech decisions not in account owner territory)
    #   + Microsoft standardized (Softchoice): +5%
    #   + High AI maturity (score >=15): +5%
    #   Floor: 12%, Ceiling: 42%
    addressable_pct = 27.0
    # OEM-direct deduction requires manual confirmation — not auto-applied by revenue threshold.
    if c.oem_direct_confirmed:
        addressable_pct -= 3.0
        flags["oem_direct_hardware"] = True
    if c.ms_standardized:       addressable_pct += 5.0
    if c.offshore_coe_confirmed: addressable_pct -= 8.0
    if c.incumbent_msp:          addressable_pct -= 10.0
    if c.channel_mismatch_flag:  addressable_pct -= 8.0
    if maturity_score >= 15:     addressable_pct += 5.0
    addressable_pct = max(12.0, min(42.0, addressable_pct))

    if total_low is not None:
        wwt_low  = round(total_low  * addressable_pct / 100, 2)
        wwt_high = round(total_high * addressable_pct / 100, 2)

    # ── STEP 11: forward estimate multiplier ──────────────────────────────────
    fwd_mult = 1.08
    if step8_pivot_count > 0:
        fwd_mult *= min(1.05 ** step8_pivot_count, 1.20)
    if maturity_score >= 15:
        fwd_mult *= 1.12
    step11_forward_estimate = round(total_mid * fwd_mult, 2) if total_mid is not None else None

    # ── STEP 12: enhanced confidence scoring ─────────────────────────────────
    ldr_count = len(leadership_rows)
    if rev is not None and c.employee_count and c.sub_sector and c.country and ldr_count >= 2:
        confidence = "HIGH"
    elif rev is not None and c.sub_sector and (c.employee_count or ldr_count >= 1):
        confidence = "MEDIUM_HIGH"
    elif rev is not None and (c.sub_sector or c.country):
        confidence = "MEDIUM"
    elif rev is not None:
        confidence = "LOW_MEDIUM"
    else:
        confidence = "LOW"

    # ── STEP 13: key drivers and flags ───────────────────────────────────────
    if c.offshore_coe_confirmed:
        flags["offshore_coe_risk"] = True
    if c.incumbent_msp:
        flags["incumbent_msp"] = c.incumbent_msp
    if c.channel_mismatch_flag:
        flags["channel_mismatch"] = True

    key_drivers = {
        "maturity_score":   maturity_score,
        "leadership_score": leadership_score,
        "signal_score":     signal_score,
        "private_mult":     private_mult,
        "regional_mult":    regional_mult,
        "fin_adj":          fin_adj,
        "addressable_pct":  addressable_pct,
        "step4_scale":      step4_scale_factor,
        "step7_esg":        step7_esg_multiplier,
        "step8_uplift":     step8_ma_uplift,
        "fwd_mult":         fwd_mult,
    }

    # ── Persist current_year estimate ────────────────────────────────────────
    est = CompanySpendEstimate(
        company_id          = company_id,
        estimate_date       = date.today(),
        estimate_type       = "current_year",
        fiscal_year         = date.today().year,
        it_spend_low=it_low,    it_spend_mid=it_mid,    it_spend_high=it_high,
        ot_spend_low=ot_low,    ot_spend_mid=ot_mid,    ot_spend_high=ot_high,
        digital_spend_low=dig_low, digital_spend_mid=dig_mid, digital_spend_high=dig_high,
        ai_spend_low=ai_low,    ai_spend_mid=ai_mid,    ai_spend_high=ai_high,
        total_spend_low=total_low, total_spend_mid=total_mid, total_spend_high=total_high,
        wwt_addressable_low=wwt_low,  wwt_addressable_high=wwt_high,
        wwt_addressable_pct_low=addressable_pct,
        wwt_addressable_pct_high=addressable_pct,
        confidence_level         = confidence,
        model_version            = "v4.0",
        step1_value_chain        = step1_value_chain,
        step2_denominator_used   = denom_used,
        step3_regional_multiplier = regional_mult,
        step4_employee_derived   = step4_employee_derived,
        step4_scale_factor       = step4_scale_factor if step4_scale_factor != 1.0 else None,
        step5_applied            = step5_applied,
        step6_it_maturity_score      = maturity_score,
        step6_ot_maturity_score      = maturity_score,
        step6_digital_maturity_score = maturity_score,
        step6_ai_maturity_score      = maturity_score,
        step7_cyber_flag         = step7_cyber_flag,
        step7_esg_multiplier     = step7_esg_multiplier,
        step8_ma_uplift          = step8_ma_uplift,
        step8_pivot_count        = step8_pivot_count,
        step9_commodity_adjustment = fin_adj,
        step10_addressable_pct   = addressable_pct,
        step11_forward_estimate  = step11_forward_estimate,
        key_drivers = key_drivers,
        flags = {k: v for k, v in flags.items() if v},
    )
    db.add(est)
    db.commit()
    db.refresh(est)

    # ── STEP 11: persist forward_1yr record ───────────────────────────────────
    if step11_forward_estimate is not None and total_mid and total_mid > 0:
        fwd_scale = step11_forward_estimate / total_mid
        fwd_est = CompanySpendEstimate(
            company_id      = company_id,
            estimate_date   = date.today(),
            estimate_type   = "forward_1yr",
            fiscal_year     = date.today().year + 1,
            it_spend_low    = _rnd(it_low  * fwd_scale) if it_low  is not None else None,
            it_spend_mid    = _rnd(it_mid  * fwd_scale) if it_mid  is not None else None,
            it_spend_high   = _rnd(it_high * fwd_scale) if it_high is not None else None,
            ot_spend_low    = _rnd(ot_low  * fwd_scale) if ot_low  is not None else None,
            ot_spend_mid    = _rnd(ot_mid  * fwd_scale) if ot_mid  is not None else None,
            ot_spend_high   = _rnd(ot_high * fwd_scale) if ot_high is not None else None,
            digital_spend_low  = _rnd(dig_low  * fwd_scale) if dig_low  is not None else None,
            digital_spend_mid  = _rnd(dig_mid  * fwd_scale) if dig_mid  is not None else None,
            digital_spend_high = _rnd(dig_high * fwd_scale) if dig_high is not None else None,
            ai_spend_low    = _rnd(ai_low  * fwd_scale) if ai_low  is not None else None,
            ai_spend_mid    = _rnd(ai_mid  * fwd_scale) if ai_mid  is not None else None,
            ai_spend_high   = _rnd(ai_high * fwd_scale) if ai_high is not None else None,
            total_spend_low    = _rnd(total_low  * fwd_scale) if total_low  is not None else None,
            total_spend_mid    = step11_forward_estimate,
            total_spend_high   = _rnd(total_high * fwd_scale) if total_high is not None else None,
            wwt_addressable_low  = _rnd(wwt_low  * fwd_scale) if wwt_low  is not None else None,
            wwt_addressable_high = _rnd(wwt_high * fwd_scale) if wwt_high is not None else None,
            wwt_addressable_pct_low  = addressable_pct,
            wwt_addressable_pct_high = addressable_pct,
            confidence_level    = confidence,
            model_version       = "v4.0",
            step1_value_chain   = step1_value_chain,
            step2_denominator_used = denom_used,
            step3_regional_multiplier = regional_mult,
            step10_addressable_pct = addressable_pct,
            step11_forward_estimate = step11_forward_estimate,
            key_drivers = {"forward_mult": fwd_mult, "maturity_score": maturity_score},
            flags = flags,
        )
        db.add(fwd_est)
        db.commit()

    def _r(v) -> Optional[float]:
        if v is None:
            return None
        return float(v) if isinstance(v, Decimal) else v

    return {
        "id":               est.id,
        "company_id":       company_id,
        "company_name":     c.name,
        "estimate_date":    est.estimate_date.isoformat(),
        "estimate_type":    est.estimate_type,
        "fiscal_year":      est.fiscal_year,
        "confidence_level": confidence,
        "model_version":    "v4.0",
        "sub_sector":       c.sub_sector,
        "country":          c.country,
        "denominator_used": denom_used,
        "denominator_basis": denominator_basis,
        "denominator_value": denominator_mid,
        "private_mult":     private_mult,
        "regional_mult":    regional_mult,
        "maturity_score":   maturity_score,
        "fin_adj":          fin_adj,
        "addressable_pct":  addressable_pct,
        "step4_employee_derived": step4_employee_derived,
        "step4_scale_factor":     step4_scale_factor,
        "step7_cyber_flag":       step7_cyber_flag,
        "step7_esg_multiplier":   step7_esg_multiplier,
        "step8_ma_uplift":        step8_ma_uplift,
        "step8_pivot_count":      step8_pivot_count,
        "step11_forward_estimate": step11_forward_estimate,
        "it_spend":      {"low": _r(it_low),   "mid": _r(it_mid),   "high": _r(it_high)},
        "ot_spend":      {"low": _r(ot_low),   "mid": _r(ot_mid),   "high": _r(ot_high)},
        "digital_spend": {"low": _r(dig_low),  "mid": _r(dig_mid),  "high": _r(dig_high)},
        "ai_spend":      {"low": _r(ai_low),   "mid": _r(ai_mid),   "high": _r(ai_high)},
        "total_spend":   {"low": _r(total_low), "mid": _r(total_mid), "high": _r(total_high)},
        "wwt_addressable": {"low": _r(wwt_low), "high": _r(wwt_high), "pct": addressable_pct},
        "key_drivers":   est.key_drivers,
        "flags":         est.flags,
    }
