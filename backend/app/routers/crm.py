from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func, case
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models import CrmAccount, CrmOpportunity

router = APIRouter(prefix="/api/crm", tags=["crm"])

# Stages considered "open" (active pipeline)
_OPEN_STAGES = {"Prospecting", "Qualification", "Needs Analysis", "Value Proposition",
                "Id. Decision Makers", "Perception Analysis", "Proposal/Price Quote",
                "Negotiation/Review"}

def _is_open(stage: str | None) -> bool:
    if not stage:
        return False
    s = stage.lower()
    return not s.startswith("closed")


def _opp_dict(o: CrmOpportunity) -> dict:
    return {
        "id":                o.id,
        "account_id":        o.account_id,
        "account_name":      o.account_name,
        "opportunity_name":  o.opportunity_name,
        "opportunity_owner": o.opportunity_owner,
        "owner_role":        o.owner_role,
        "stage":             o.stage,
        "fiscal_period":     o.fiscal_period,
        "amount":            o.amount,
        "probability":       o.probability,
        "age":               o.age,
        "close_date":        o.close_date.isoformat() if o.close_date else None,
        "created_date":      o.created_date.isoformat() if o.created_date else None,
        "next_step":         o.next_step,
        "lead_source":       o.lead_source,
        "opp_type":          o.opp_type,
    }


# ── GET /api/crm/summary ──────────────────────────────────────────────────────

@router.get("/summary")
def crm_summary(db: Session = Depends(get_db)):
    opps = db.scalars(select(CrmOpportunity)).all()

    total_accounts = db.scalar(select(func.count(CrmAccount.id)))

    by_stage: dict[str, dict] = {}
    open_pipeline = 0.0
    closed_won = 0.0
    closed_lost = 0.0
    closed_won_count = 0
    closed_lost_count = 0

    for o in opps:
        stage = o.stage or "Unknown"
        amt = o.amount or 0.0
        if stage not in by_stage:
            by_stage[stage] = {"count": 0, "total_amount": 0.0}
        by_stage[stage]["count"] += 1
        by_stage[stage]["total_amount"] += amt

        stage_l = stage.lower()
        if stage_l == "closed won":
            closed_won += amt
            closed_won_count += 1
        elif stage_l in ("closed lost", "closed: no bid"):
            closed_lost += amt
            closed_lost_count += 1
        elif _is_open(stage):
            open_pipeline += amt

    decided = closed_won_count + closed_lost_count
    win_rate = closed_won_count / decided if decided else 0.0
    avg_deal_size = closed_won / closed_won_count if closed_won_count else 0.0

    by_stage_list = sorted(
        [{"stage": k, **v} for k, v in by_stage.items()],
        key=lambda x: x["total_amount"],
        reverse=True,
    )

    return {
        "total_opportunities": len(opps),
        "total_accounts": total_accounts,
        "open_pipeline": open_pipeline,
        "closed_won": closed_won,
        "closed_lost": closed_lost,
        "win_rate": round(win_rate, 4),
        "avg_deal_size": round(avg_deal_size, 2),
        "by_stage": by_stage_list,
    }


# ── GET /api/crm/companies ────────────────────────────────────────────────────

@router.get("/companies")
def crm_companies(db: Session = Depends(get_db)):
    accounts = db.scalars(select(CrmAccount).order_by(CrmAccount.name)).all()
    result = []
    for acct in accounts:
        opps = acct.opportunities
        total_deals = len(opps)
        open_pipeline = sum(o.amount or 0 for o in opps if _is_open(o.stage))
        closed_won    = sum(o.amount or 0 for o in opps if (o.stage or "").lower() == "closed won")
        closed_lost   = sum(o.amount or 0 for o in opps if (o.stage or "").lower() in ("closed lost", "closed: no bid"))
        won_count     = sum(1 for o in opps if (o.stage or "").lower() == "closed won")
        lost_count    = sum(1 for o in opps if (o.stage or "").lower() in ("closed lost", "closed: no bid"))
        decided       = won_count + lost_count
        win_rate      = won_count / decided if decided else 0.0
        close_dates   = [o.close_date for o in opps if o.close_date]
        latest_close  = max(close_dates).isoformat() if close_dates else None
        result.append({
            "id":             acct.id,
            "name":           acct.name,
            "total_deals":    total_deals,
            "open_pipeline":  open_pipeline,
            "closed_won":     closed_won,
            "closed_lost":    closed_lost,
            "win_rate":       round(win_rate, 4),
            "latest_close_date": latest_close,
        })
    return result


# ── GET /api/crm/companies/{company_id} ───────────────────────────────────────

@router.get("/companies/{company_id}")
def crm_company_detail(company_id: int, db: Session = Depends(get_db)):
    acct = db.get(CrmAccount, company_id)
    if not acct:
        raise HTTPException(status_code=404, detail="Account not found")

    opps = sorted(acct.opportunities, key=lambda o: o.close_date or __import__("datetime").date.min, reverse=True)
    open_pipeline = sum(o.amount or 0 for o in opps if _is_open(o.stage))
    closed_won    = sum(o.amount or 0 for o in opps if (o.stage or "").lower() == "closed won")
    closed_lost   = sum(o.amount or 0 for o in opps if (o.stage or "").lower() in ("closed lost", "closed: no bid"))
    won_count     = sum(1 for o in opps if (o.stage or "").lower() == "closed won")
    lost_count    = sum(1 for o in opps if (o.stage or "").lower() in ("closed lost", "closed: no bid"))
    decided       = won_count + lost_count

    return {
        "id":             acct.id,
        "name":           acct.name,
        "total_deals":    len(opps),
        "open_pipeline":  open_pipeline,
        "closed_won":     closed_won,
        "closed_lost":    closed_lost,
        "win_rate":       round(won_count / decided, 4) if decided else 0.0,
        "opportunities":  [_opp_dict(o) for o in opps],
    }


# ── GET /api/crm/opportunities ────────────────────────────────────────────────

# ── GET /api/crm/filter-options ───────────────────────────────────────────────

@router.get("/filter-options")
def crm_filter_options(db: Session = Depends(get_db)):
    stages = [r[0] for r in db.execute(
        select(CrmOpportunity.stage).distinct()
        .where(CrmOpportunity.stage.isnot(None))
        .order_by(CrmOpportunity.stage)
    ).all()]
    owners = [r[0] for r in db.execute(
        select(CrmOpportunity.opportunity_owner).distinct()
        .where(CrmOpportunity.opportunity_owner.isnot(None))
        .order_by(CrmOpportunity.opportunity_owner)
    ).all()]
    periods = [r[0] for r in db.execute(
        select(CrmOpportunity.fiscal_period).distinct()
        .where(CrmOpportunity.fiscal_period.isnot(None))
        .order_by(CrmOpportunity.fiscal_period)
    ).all()]
    return {"stages": stages, "owners": owners, "fiscal_periods": periods}


@router.get("/opportunities")
def crm_opportunities(
    stage:        Optional[str]  = Query(None),
    owner:        Optional[str]  = Query(None),
    fiscal_period: Optional[str] = Query(None),
    account_id:   Optional[int]  = Query(None),
    account_name: Optional[str]  = Query(None),
    lead_source:  Optional[str]  = Query(None),
    active_only:  bool           = Query(False),
    page:         int            = Query(1, ge=1),
    page_size:    int            = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    q = select(CrmOpportunity)
    if stage:
        q = q.where(CrmOpportunity.stage == stage)
    if owner:
        q = q.where(CrmOpportunity.opportunity_owner == owner)
    if fiscal_period:
        q = q.where(CrmOpportunity.fiscal_period == fiscal_period)
    if account_id:
        q = q.where(CrmOpportunity.account_id == account_id)
    if account_name:
        q = q.where(CrmOpportunity.account_name.ilike(f"%{account_name}%"))
    if lead_source:
        q = q.where(CrmOpportunity.lead_source == lead_source)
    if active_only:
        q = q.where(~CrmOpportunity.stage.ilike("closed%"))

    total = db.scalar(select(func.count()).select_from(q.subquery()))
    opps  = db.scalars(
        q.order_by(CrmOpportunity.close_date.desc().nullslast(), CrmOpportunity.id)
         .offset((page - 1) * page_size)
         .limit(page_size)
    ).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_opp_dict(o) for o in opps],
    }


# ── GET /api/crm/owners ───────────────────────────────────────────────────────

@router.get("/owners")
def crm_owners(db: Session = Depends(get_db)):
    opps = db.scalars(select(CrmOpportunity)).all()

    owners: dict[str, dict] = {}
    for o in opps:
        name = o.opportunity_owner or "Unknown"
        amt  = o.amount or 0.0
        stage_l = (o.stage or "").lower()
        if name not in owners:
            owners[name] = {
                "opportunity_owner": name,
                "total_deals": 0,
                "open_pipeline": 0.0,
                "closed_won": 0.0,
                "closed_lost": 0.0,
                "won_count": 0,
                "lost_count": 0,
            }
        owners[name]["total_deals"] += 1
        if stage_l == "closed won":
            owners[name]["closed_won"]  += amt
            owners[name]["won_count"]   += 1
        elif stage_l in ("closed lost", "closed: no bid"):
            owners[name]["closed_lost"] += amt
            owners[name]["lost_count"]  += 1
        elif _is_open(o.stage):
            owners[name]["open_pipeline"] += amt

    leaderboard = []
    for d in owners.values():
        decided  = d["won_count"] + d["lost_count"]
        win_rate = d["won_count"] / decided if decided else 0.0
        won_c    = d["won_count"]
        avg      = d["closed_won"] / won_c if won_c else 0.0
        leaderboard.append({
            "opportunity_owner": d["opportunity_owner"],
            "total_deals":       d["total_deals"],
            "open_pipeline":     round(d["open_pipeline"], 2),
            "closed_won":        round(d["closed_won"], 2),
            "closed_lost":       round(d["closed_lost"], 2),
            "win_rate":          round(win_rate, 4),
            "avg_deal_size":     round(avg, 2),
        })

    leaderboard.sort(key=lambda x: x["closed_won"], reverse=True)
    return leaderboard
