from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models import Event, Company, EventType
from app.schemas import EventWithCompany

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=list[EventWithCompany])
def list_events(
    event_type: Optional[EventType] = Query(None),
    company_id: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    q = (
        select(Event, Company.name.label("company_name"), Company.ticker.label("company_ticker"))
        .join(Company, Event.company_id == Company.id)
        .order_by(desc(Event.event_date), desc(Event.created_at))
        .limit(limit)
    )
    if event_type:
        q = q.where(Event.event_type == event_type)
    if company_id:
        q = q.where(Event.company_id == company_id)

    rows = db.execute(q).all()
    results = []
    for row in rows:
        event = row[0]
        out = EventWithCompany.model_validate(event)
        out.company_name = row[1]
        out.company_ticker = row[2]
        results.append(out)
    return results
