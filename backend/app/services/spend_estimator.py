"""
Technology spend estimation engine — v3.0 model.

Runs a 13-step model (steps 1, 2, 3, 6, 9, 10 are data-driven;
remaining steps are pass-through/reserved) to produce low/mid/high
IT, OT, Digital, and AI spend estimates for a single company.
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Company, CompanyStatus, Financial,
    CompanyLeadership, CompanyTechSignal, CompanySpendEstimate,
)

# ── STEP 1: Baseline percentages by sub_sector ────────────────────────────────
# Each entry: (IT, OT, Digital, AI) — each a (low%, mid%, high%) tuple
_BASELINE: dict[str, tuple[tuple, tuple, tuple, tuple]] = {
    "Integrated O&G":                   ((0.8,1.3,1.8),  (0.4,0.8,1.2),  (0.3,0.6,0.9),  (0.2,0.45,0.7)),
    "Upstream E&P":                     ((0.9,1.55,2.2), (0.8,1.4,2.0),  (0.4,0.8,1.2),  (0.3,0.65,1.0)),
    "Midstream Pipeline & Processing":  ((1.2,2.0,2.8),  (1.2,2.0,2.8),  (0.5,0.95,1.4), (0.3,0.65,1.0)),
    "Downstream Refining":              ((1.2,1.8,2.4),  (1.2,2.0,2.8),  (0.4,0.8,1.2),  (0.3,0.6,0.9)),
    "Petrochemical & Specialty Chemicals": ((1.3,2.05,2.8),(1.3,2.05,2.8),(0.6,1.1,1.6),  (0.4,0.8,1.2)),
    "Oilfield & Energy Services":       ((1.8,2.8,3.8),  (0.6,1.2,1.8),  (0.8,1.5,2.2),  (0.6,1.4,2.2)),
    "Energy Utilities":                 ((1.8,2.5,3.2),  (1.3,2.25,3.2), (0.8,1.4,2.0),  (0.6,1.2,1.8)),
    "Renewable & New Energy":           ((1.4,2.1,2.8),  (0.4,1.1,1.8),  (1.2,2.2,3.2),  (0.8,1.8,2.8)),
    "Energy Infrastructure & Power":    ((1.5,2.25,3.0), (1.5,2.5,3.5),  (1.5,2.5,3.5),  (1.0,2.0,3.0)),
    "Carbon Management":                ((1.2,1.85,2.5), (0.8,1.4,2.0),  (1.5,2.5,3.5),  (1.2,2.1,3.0)),
    "LNG & Gas Trading":                ((1.4,2.1,2.8),  (1.0,1.6,2.2),  (0.8,1.4,2.0),  (0.5,1.0,1.5)),
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

# ── STEP 6: Maturity score → category multipliers ────────────────────────────
def _maturity_mults(score: int) -> tuple[float, float, float, float]:
    """Returns (IT_mult, OT_mult, Digital_mult, AI_mult)."""
    if score <= 3:
        return (0.8, 1.0, 0.6, 0.6)
    if score <= 6:
        return (1.0, 1.0, 1.0, 1.0)
    if score <= 10:
        return (1.2, 1.1, 1.5, 1.5)
    if score <= 14:
        return (1.3, 1.2, 1.8, 1.8)
    return (1.5, 1.3, 2.5, 2.5)


def _f(v) -> Optional[float]:
    """Decimal → float, pass-through for float/None."""
    if v is None:
        return None
    return float(v)


def estimate(company_id: int, db: Session) -> dict:
    """Run the v3.0 spend model for one company. Writes a row to company_spend_estimates and returns it as a dict."""
    c = db.get(Company, company_id)
    if not c:
        raise ValueError(f"Company {company_id} not found")
    if c.status != CompanyStatus.active:
        raise ValueError(f"Company {company_id} ({c.name}) is not active (status={c.status.value})")

    # ── STEP 1: baseline ─────────────────────────────────────────────────────
    it_pcts, ot_pcts, dig_pcts, ai_pcts = _BASELINE.get(
        c.sub_sector or "", _DEFAULT_BASELINE
    )
    step1_value_chain = c.sub_sector or "default"

    # ── STEP 2: denominator ──────────────────────────────────────────────────
    rev    = _f(c.revenue_ttm)
    ebitda = _f(c.ebitda_ttm)
    gp     = _f(c.gross_profit_ttm)

    ebitda_scales: Optional[tuple[float, float, float]] = None  # (low, mid, high)

    denom_used = "none"
    denominator_low = denominator_mid = denominator_high = None

    if c.revenue_denominator == "ebitda" and ebitda is not None:
        # Step1 % calibrated for revenue; scale down by assumed EBITDA margin
        # low estimate uses high margin (÷0.20), high estimate uses low margin (÷0.15)
        denominator_low  = ebitda
        denominator_mid  = ebitda
        denominator_high = ebitda
        ebitda_scales    = (0.15, 0.175, 0.20)
        denom_used = "ebitda"
    elif c.revenue_denominator == "gross_profit" and gp is not None:
        denominator_low = denominator_mid = denominator_high = gp
        denom_used = "gross_profit"
    elif c.revenue_denominator == "blended" and rev is not None and ebitda is not None:
        blended = rev * 0.6 + ebitda * 0.4
        denominator_low = denominator_mid = denominator_high = blended
        denom_used = "blended"
    elif rev is not None:
        denominator_low = denominator_mid = denominator_high = rev
        denom_used = "revenue"

    # Private / PE multiplier
    if c.is_pe_backed:
        private_mult = 0.75
    elif c.is_private:
        private_mult = 0.85
    else:
        private_mult = 1.0

    # ── STEP 3: regional multiplier ──────────────────────────────────────────
    regional_mult = _REGIONAL.get(c.country or "", 1.0)

    # ── STEP 6: digital maturity ─────────────────────────────────────────────
    leadership_rows = db.scalars(
        select(CompanyLeadership).where(
            CompanyLeadership.company_id == company_id,
            CompanyLeadership.is_current == True,
        )
    ).all()
    leadership_score = sum(r.signal_score or 0 for r in leadership_rows)

    cutoff = date.today() - timedelta(days=365)
    signal_rows = db.scalars(
        select(CompanyTechSignal).where(
            CompanyTechSignal.company_id == company_id,
            CompanyTechSignal.signal_type.in_(
                ["partnership", "ai_announcement", "leadership_hire"]
            ),
            CompanyTechSignal.signal_date >= cutoff,
        )
    ).all()
    signal_score = sum(r.score_points or 0 for r in signal_rows)
    maturity_score = leadership_score + signal_score

    it_mat, ot_mat, dig_mat, ai_mat = _maturity_mults(maturity_score)

    # ── STEP 9: financial health ──────────────────────────────────────────────
    latest_fin = db.scalars(
        select(Financial)
        .where(
            Financial.company_id == company_id,
            Financial.ps_ratio.isnot(None),
        )
        .order_by(Financial.snapshot_date.desc())
        .limit(1)
    ).first()

    fin_adj = 0.0
    if (
        latest_fin
        and latest_fin.ps_ratio is not None
        and latest_fin.ps_ratio_5yr_avg
        and latest_fin.ps_ratio_5yr_avg != 0
    ):
        ratio = latest_fin.ps_ratio / latest_fin.ps_ratio_5yr_avg
        if ratio > 1.5:
            fin_adj = 0.15
        elif ratio >= 1.0:
            fin_adj = 0.05
        elif ratio >= 0.75:
            fin_adj = 0.0
        elif ratio >= 0.5:
            fin_adj = -0.10
        else:
            fin_adj = -0.20

    # ── STEP 10: WWT addressable ─────────────────────────────────────────────
    addressable_pct = 28.0
    if c.ms_standardized:
        addressable_pct += 5.0
    if c.offshore_coe_confirmed:
        addressable_pct -= 8.0
    if c.incumbent_msp:
        addressable_pct -= 10.0
    if c.channel_mismatch_flag:
        addressable_pct -= 8.0
    if maturity_score >= 15:
        addressable_pct += 5.0
    addressable_pct = max(12.0, min(42.0, addressable_pct))

    # ── Calculate dollar amounts ──────────────────────────────────────────────
    def _apply(
        pcts: tuple[float, float, float],
        cat_mat: float,
        denom_lo: Optional[float],
        denom_mi: Optional[float],
        denom_hi: Optional[float],
    ) -> tuple[Optional[float], Optional[float], Optional[float]]:
        if denom_lo is None:
            return (None, None, None)
        pl, pm, ph = pcts
        es = ebitda_scales  # None unless EBITDA mode
        el = es[0] if es else 1.0
        em = es[1] if es else 1.0
        eh = es[2] if es else 1.0
        shared = private_mult * regional_mult * cat_mat * (1.0 + fin_adj)
        low  = round(denom_lo * (pl / 100) * el * shared, 2)
        mid  = round(denom_mi * (pm / 100) * em * shared, 2)
        high = round(denom_hi * (ph / 100) * eh * shared, 2)
        return (low, mid, high)

    it_low,  it_mid,  it_high  = _apply(it_pcts,  it_mat,  denominator_low, denominator_mid, denominator_high)
    ot_low,  ot_mid,  ot_high  = _apply(ot_pcts,  ot_mat,  denominator_low, denominator_mid, denominator_high)
    dig_low, dig_mid, dig_high = _apply(dig_pcts, dig_mat, denominator_low, denominator_mid, denominator_high)
    ai_low,  ai_mid,  ai_high  = _apply(ai_pcts,  ai_mat,  denominator_low, denominator_mid, denominator_high)

    total_low = total_mid = total_high = None
    wwt_low = wwt_high = None

    if it_low is not None:
        total_low  = round(it_low  + ot_low  + dig_low  + ai_low,  2)
        total_mid  = round(it_mid  + ot_mid  + dig_mid  + ai_mid,  2)
        total_high = round(it_high + ot_high + dig_high + ai_high, 2)
        wwt_low    = round(total_low  * addressable_pct / 100, 2)
        wwt_high   = round(total_high * addressable_pct / 100, 2)

    # ── Confidence level ─────────────────────────────────────────────────────
    if rev is not None and c.employee_count and c.sub_sector and c.country:
        confidence = "HIGH"
    elif rev is not None and (c.sub_sector or c.country):
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    # ── Persist ──────────────────────────────────────────────────────────────
    est = CompanySpendEstimate(
        company_id          = company_id,
        estimate_date       = date.today(),
        estimate_type       = "current_year",
        fiscal_year         = date.today().year,
        it_spend_low        = it_low,  it_spend_mid  = it_mid,  it_spend_high  = it_high,
        ot_spend_low        = ot_low,  ot_spend_mid  = ot_mid,  ot_spend_high  = ot_high,
        digital_spend_low   = dig_low, digital_spend_mid = dig_mid, digital_spend_high = dig_high,
        ai_spend_low        = ai_low,  ai_spend_mid  = ai_mid,  ai_spend_high  = ai_high,
        total_spend_low     = total_low,  total_spend_mid  = total_mid,  total_spend_high  = total_high,
        wwt_addressable_low = wwt_low,  wwt_addressable_high = wwt_high,
        wwt_addressable_pct_low  = addressable_pct,
        wwt_addressable_pct_high = addressable_pct,
        confidence_level         = confidence,
        model_version            = "v3.0",
        step1_value_chain        = step1_value_chain,
        step2_denominator_used   = denom_used,
        step3_regional_multiplier = regional_mult,
        step6_it_maturity_score      = maturity_score,
        step6_ot_maturity_score      = maturity_score,
        step6_digital_maturity_score = maturity_score,
        step6_ai_maturity_score      = maturity_score,
        step9_commodity_adjustment   = fin_adj,
        step10_addressable_pct       = addressable_pct,
        key_drivers = {
            "maturity_score":     maturity_score,
            "leadership_score":   leadership_score,
            "signal_score":       signal_score,
            "private_mult":       private_mult,
            "regional_mult":      regional_mult,
            "fin_adj":            fin_adj,
            "addressable_pct":    addressable_pct,
        },
        flags = {
            "no_revenue":   rev is None,
            "no_sub_sector": c.sub_sector is None,
            "no_country":   c.country is None,
            "is_private":   c.is_private,
            "is_pe_backed": c.is_pe_backed,
            "ebitda_mode":  denom_used == "ebitda",
        },
    )
    db.add(est)
    db.commit()
    db.refresh(est)

    def _r(v) -> Optional[float]:
        if v is None:
            return None
        return float(v) if isinstance(v, Decimal) else v

    return {
        "id":                       est.id,
        "company_id":               company_id,
        "company_name":             c.name,
        "estimate_date":            est.estimate_date.isoformat(),
        "estimate_type":            est.estimate_type,
        "fiscal_year":              est.fiscal_year,
        "confidence_level":         confidence,
        "model_version":            "v3.0",
        # Inputs
        "sub_sector":               c.sub_sector,
        "country":                  c.country,
        "denominator_used":         denom_used,
        "denominator_value":        denominator_mid,
        "private_mult":             private_mult,
        "regional_mult":            regional_mult,
        "maturity_score":           maturity_score,
        "fin_adj":                  fin_adj,
        "addressable_pct":          addressable_pct,
        # Spend outputs (USD)
        "it_spend":      {"low": _r(it_low),  "mid": _r(it_mid),  "high": _r(it_high)},
        "ot_spend":      {"low": _r(ot_low),  "mid": _r(ot_mid),  "high": _r(ot_high)},
        "digital_spend": {"low": _r(dig_low), "mid": _r(dig_mid), "high": _r(dig_high)},
        "ai_spend":      {"low": _r(ai_low),  "mid": _r(ai_mid),  "high": _r(ai_high)},
        "total_spend":   {"low": _r(total_low), "mid": _r(total_mid), "high": _r(total_high)},
        "wwt_addressable": {"low": _r(wwt_low), "high": _r(wwt_high), "pct": addressable_pct},
        "key_drivers":   est.key_drivers,
        "flags":         est.flags,
    }
