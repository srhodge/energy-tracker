from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Company, CompanyTechSignal, CompanySpendEstimate, CompanyLeadership, CompanyAsset

router = APIRouter(prefix="/api/companies", tags=["intelligence"])


# ── Serialisers ───────────────────────────────────────────────────────────────

def _d(v: Any) -> Any:
    """Convert date/datetime/Decimal to JSON-safe types."""
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, Decimal):
        return float(v)
    return v


def _profile(c: Company) -> dict:
    return {
        "sub_sector":               c.sub_sector,
        "employee_count":           c.employee_count,
        "employee_count_source":    c.employee_count_source,
        "employee_count_updated":   _d(c.employee_count_updated),
        "hq_city":                  c.hq_city,
        "hq_country":               c.hq_country,
        "tech_decision_city":       c.tech_decision_city,
        "tech_decision_country":    c.tech_decision_country,
        "revenue_ttm":              _d(c.revenue_ttm),
        "ebitda_ttm":               _d(c.ebitda_ttm),
        "gross_profit_ttm":         _d(c.gross_profit_ttm),
        "enterprise_value":         _d(c.enterprise_value),
        "revenue_denominator":      c.revenue_denominator,
        "is_private":               c.is_private,
        "is_pe_backed":             c.is_pe_backed,
        "commodity_exposure_pct":   c.commodity_exposure_pct,
        "ms_standardized":          c.ms_standardized,
        "offshore_coe_confirmed":   c.offshore_coe_confirmed,
        "incumbent_msp":            c.incumbent_msp,
        "channel_mismatch_flag":    c.channel_mismatch_flag,
        "channel_mismatch_note":    c.channel_mismatch_note,
        "data_enrichment_tier":     c.data_enrichment_tier,
    }


def _signal(s: CompanyTechSignal) -> dict:
    return {
        "id":                   s.id,
        "company_id":           s.company_id,
        "signal_type":          s.signal_type,
        "signal_category":      s.signal_category,
        "signal_date":          _d(s.signal_date),
        "signal_title":         s.signal_title,
        "signal_description":   s.signal_description,
        "signal_url":           s.signal_url,
        "sentiment":            s.sentiment,
        "spend_impact_direction": s.spend_impact_direction,
        "score_points":         s.score_points,
        "source":               s.source,
        "week_batch_date":      _d(s.week_batch_date),
        "created_at":           _d(s.created_at),
    }


def _leadership(l: CompanyLeadership) -> dict:
    return {
        "id":               l.id,
        "company_id":       l.company_id,
        "role":             l.role,
        "person_name":      l.person_name,
        "location_city":    l.location_city,
        "location_country": l.location_country,
        "hire_date":        _d(l.hire_date),
        "linkedin_url":     l.linkedin_url,
        "is_current":       l.is_current,
        "departure_date":   _d(l.departure_date),
        "spend_category":   l.spend_category,
        "signal_score":     l.signal_score,
        "source":           l.source,
        "created_at":       _d(l.created_at),
        "updated_at":       _d(l.updated_at),
    }


def _asset(a: CompanyAsset) -> dict:
    return {
        "id":           a.id,
        "company_id":   a.company_id,
        "asset_type":   a.asset_type,
        "asset_category": a.asset_category,
        "asset_value":  _d(a.asset_value),
        "asset_unit":   a.asset_unit,
        "asset_score":  a.asset_score,
        "data_source":  a.data_source,
        "as_of_date":   _d(a.as_of_date),
        "notes":        a.notes,
        "created_at":   _d(a.created_at),
    }


def _estimate(e: CompanySpendEstimate) -> dict:
    return {
        "id":                       e.id,
        "company_id":               e.company_id,
        "estimate_date":            _d(e.estimate_date),
        "estimate_type":            e.estimate_type,
        "fiscal_year":              e.fiscal_year,
        "it_spend_low":             _d(e.it_spend_low),
        "it_spend_mid":             _d(e.it_spend_mid),
        "it_spend_high":            _d(e.it_spend_high),
        "ot_spend_low":             _d(e.ot_spend_low),
        "ot_spend_mid":             _d(e.ot_spend_mid),
        "ot_spend_high":            _d(e.ot_spend_high),
        "digital_spend_low":        _d(e.digital_spend_low),
        "digital_spend_mid":        _d(e.digital_spend_mid),
        "digital_spend_high":       _d(e.digital_spend_high),
        "ai_spend_low":             _d(e.ai_spend_low),
        "ai_spend_mid":             _d(e.ai_spend_mid),
        "ai_spend_high":            _d(e.ai_spend_high),
        "total_spend_low":          _d(e.total_spend_low),
        "total_spend_mid":          _d(e.total_spend_mid),
        "total_spend_high":         _d(e.total_spend_high),
        "wwt_addressable_low":      _d(e.wwt_addressable_low),
        "wwt_addressable_high":     _d(e.wwt_addressable_high),
        "wwt_addressable_pct_low":  _d(e.wwt_addressable_pct_low),
        "wwt_addressable_pct_high": _d(e.wwt_addressable_pct_high),
        "confidence_level":         e.confidence_level,
        "model_version":            e.model_version,
        "step1_value_chain":        e.step1_value_chain,
        "step2_denominator_used":   e.step2_denominator_used,
        "step3_regional_multiplier": _d(e.step3_regional_multiplier),
        "step6_it_maturity_score":  e.step6_it_maturity_score,
        "step6_ot_maturity_score":  e.step6_ot_maturity_score,
        "step6_digital_maturity_score": e.step6_digital_maturity_score,
        "step6_ai_maturity_score":  e.step6_ai_maturity_score,
        "step9_commodity_adjustment": _d(e.step9_commodity_adjustment),
        "step10_addressable_pct":   _d(e.step10_addressable_pct),
        "key_drivers":              e.key_drivers,
        "flags":                    e.flags,
        "notes":                    e.notes,
        "created_at":               _d(e.created_at),
    }


def _get_company_or_404(company_id: int, db: Session) -> Company:
    c = db.get(Company, company_id)
    if not c:
        raise HTTPException(status_code=404, detail="Company not found")
    return c


# ── GET /api/companies/{id}/intelligence ─────────────────────────────────────

@router.get("/{company_id}/intelligence")
def get_intelligence(company_id: int, db: Session = Depends(get_db)):
    c = _get_company_or_404(company_id, db)

    signals = db.scalars(
        select(CompanyTechSignal)
        .where(CompanyTechSignal.company_id == company_id)
        .order_by(CompanyTechSignal.signal_date.desc().nullslast())
        .limit(20)
    ).all()

    leadership = db.scalars(
        select(CompanyLeadership)
        .where(CompanyLeadership.company_id == company_id)
        .order_by(CompanyLeadership.is_current.desc(), CompanyLeadership.role)
    ).all()

    latest_estimate = db.scalars(
        select(CompanySpendEstimate)
        .where(CompanySpendEstimate.company_id == company_id)
        .order_by(CompanySpendEstimate.estimate_date.desc(), CompanySpendEstimate.id.desc())
        .limit(1)
    ).first()

    return {
        "profile":          _profile(c),
        "signals":          [_signal(s) for s in signals],
        "leadership":       [_leadership(l) for l in leadership],
        "latest_estimate":  _estimate(latest_estimate) if latest_estimate else None,
    }


# ── Signals ───────────────────────────────────────────────────────────────────

@router.get("/{company_id}/signals")
def get_signals(
    company_id: int,
    category: Optional[str] = Query(None),
    type: Optional[str]     = Query(None),
    limit: int              = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    _get_company_or_404(company_id, db)
    q = select(CompanyTechSignal).where(CompanyTechSignal.company_id == company_id)
    if category:
        q = q.where(CompanyTechSignal.signal_category == category)
    if type:
        q = q.where(CompanyTechSignal.signal_type == type)
    q = q.order_by(CompanyTechSignal.signal_date.desc().nullslast()).limit(limit)
    return [_signal(s) for s in db.scalars(q).all()]


@router.post("/{company_id}/signals", status_code=201)
def create_signal(company_id: int, body: dict, db: Session = Depends(get_db)):
    _get_company_or_404(company_id, db)
    body.pop("id", None)
    body.pop("company_id", None)
    body.pop("created_at", None)
    sig = CompanyTechSignal(company_id=company_id, **body)
    db.add(sig)
    db.commit()
    db.refresh(sig)
    return _signal(sig)


# ── Leadership ────────────────────────────────────────────────────────────────

@router.get("/{company_id}/leadership")
def get_leadership(
    company_id: int,
    current_only: bool = Query(True),
    db: Session = Depends(get_db),
):
    _get_company_or_404(company_id, db)
    q = select(CompanyLeadership).where(CompanyLeadership.company_id == company_id)
    if current_only:
        q = q.where(CompanyLeadership.is_current == True)
    q = q.order_by(CompanyLeadership.is_current.desc(), CompanyLeadership.role)
    return [_leadership(l) for l in db.scalars(q).all()]


@router.post("/{company_id}/leadership", status_code=201)
def create_leadership(company_id: int, body: dict, db: Session = Depends(get_db)):
    _get_company_or_404(company_id, db)
    body.pop("id", None)
    body.pop("company_id", None)
    body.pop("created_at", None)
    body.pop("updated_at", None)
    rec = CompanyLeadership(company_id=company_id, **body)
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return _leadership(rec)


# ── Assets ────────────────────────────────────────────────────────────────────

@router.get("/{company_id}/assets")
def get_assets(
    company_id: int,
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    _get_company_or_404(company_id, db)
    q = select(CompanyAsset).where(CompanyAsset.company_id == company_id)
    if category:
        q = q.where(CompanyAsset.asset_category == category)
    q = q.order_by(CompanyAsset.asset_type)
    return [_asset(a) for a in db.scalars(q).all()]


@router.post("/{company_id}/assets", status_code=201)
def create_asset(company_id: int, body: dict, db: Session = Depends(get_db)):
    _get_company_or_404(company_id, db)
    body.pop("id", None)
    body.pop("company_id", None)
    body.pop("created_at", None)
    rec = CompanyAsset(company_id=company_id, **body)
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return _asset(rec)


# ── Spend estimates ───────────────────────────────────────────────────────────

@router.get("/{company_id}/spend-estimates")
def get_spend_estimates(company_id: int, db: Session = Depends(get_db)):
    _get_company_or_404(company_id, db)
    estimates = db.scalars(
        select(CompanySpendEstimate)
        .where(CompanySpendEstimate.company_id == company_id)
        .order_by(CompanySpendEstimate.estimate_date.desc(), CompanySpendEstimate.id.desc())
    ).all()
    return [_estimate(e) for e in estimates]


@router.post("/{company_id}/spend-estimates", status_code=201)
def create_spend_estimate(company_id: int, body: dict, db: Session = Depends(get_db)):
    _get_company_or_404(company_id, db)
    body.pop("id", None)
    body.pop("company_id", None)
    body.pop("created_at", None)
    rec = CompanySpendEstimate(company_id=company_id, **body)
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return _estimate(rec)


# ── Calculate estimate ───────────────────────────────────────────────────────

@router.post("/{company_id}/calculate-estimate", status_code=201)
def calculate_estimate(company_id: int, db: Session = Depends(get_db)):
    _get_company_or_404(company_id, db)
    from app.services.spend_estimator import estimate
    return estimate(company_id, db)


# ── Profile patch ─────────────────────────────────────────────────────────────

_PROFILE_FIELDS = {
    "sub_sector", "employee_count", "employee_count_source", "employee_count_updated",
    "hq_city", "hq_country", "tech_decision_city", "tech_decision_country",
    "revenue_ttm", "ebitda_ttm", "gross_profit_ttm", "enterprise_value",
    "revenue_denominator", "is_private", "is_pe_backed", "commodity_exposure_pct",
    "ms_standardized", "offshore_coe_confirmed", "incumbent_msp",
    "channel_mismatch_flag", "channel_mismatch_note", "data_enrichment_tier",
}


@router.patch("/{company_id}/profile")
def patch_profile(company_id: int, body: dict, db: Session = Depends(get_db)):
    c = _get_company_or_404(company_id, db)
    unknown = set(body) - _PROFILE_FIELDS
    if unknown:
        raise HTTPException(status_code=422, detail=f"Unknown profile fields: {sorted(unknown)}")
    for field, value in body.items():
        setattr(c, field, value)
    db.commit()
    db.refresh(c)
    return _profile(c)
