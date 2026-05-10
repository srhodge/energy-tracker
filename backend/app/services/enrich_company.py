"""
Company enrichment service — uses Claude with web search to research and
populate intelligence data for a given company_id.

Steps:
  1. Backfill revenue_ttm from latest financials row (no search needed)
  2. Search: current employee count
  3. Search: HQ city and country
  4. Search: current C-suite (CEO, CIO, CTO, CDO, CAIO, VP AI)
  5. Search: recent AI / tech partnership announcements (12 months)
  6. Run spend estimator

Each search is independent — failures are logged and skipped.
"""

import json
import os
import re
import traceback
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

import anthropic
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Company, CompanyStatus, Financial,
    CompanyLeadership, CompanyTechSignal,
)

# ── Config ────────────────────────────────────────────────────────────────────

MODEL = "claude-sonnet-4-5-20250514"

ROLE_SCORES: dict[str, int] = {
    "CEO": 1, "Chief Executive Officer": 1,
    "CIO": 1, "Chief Information Officer": 1,
    "CTO": 2, "Chief Technology Officer": 2,
    "CDO": 2, "Chief Digital Officer": 2,
    "CAIO": 3, "Chief AI Officer": 3, "Chief Artificial Intelligence Officer": 3,
    "VP AI": 2, "VP of AI": 2, "VP Artificial Intelligence": 2,
    "VP_AI": 2,
}

_CANONICAL_ROLES = {
    "Chief Executive Officer": "CEO",
    "Chief Information Officer": "CIO",
    "Chief Technology Officer": "CTO",
    "Chief Digital Officer": "CDO",
    "Chief AI Officer": "CAIO",
    "Chief Artificial Intelligence Officer": "CAIO",
    "VP AI": "VP_AI",
    "VP of AI": "VP_AI",
}


# ── Anthropic client ──────────────────────────────────────────────────────────

def _get_client() -> anthropic.Anthropic:
    from app.config import settings
    key = settings.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return anthropic.Anthropic(api_key=key)
    return anthropic.Anthropic()  # will raise on first call if no key in env


# ── Search helper ─────────────────────────────────────────────────────────────

def _search(client: anthropic.Anthropic, prompt: str) -> str:
    """Call Claude with web_search and return the full text response."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": prompt}],
    )
    parts: list[str] = []
    for block in response.content:
        if block.type == "text":
            parts.append(block.text)
    return "\n".join(parts).strip()


def _extract_json(text: str):
    """Extract the first JSON object or array from a Claude response."""
    # 1. JSON inside a code fence
    m = re.search(r"```(?:json)?\s*([\[{][\s\S]*?[\]}])\s*```", text)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    # 2. Bare array or object — greedy match
    for pattern in (r"(\[[\s\S]+\])", r"(\{[\s\S]+\})"):
        m = re.search(pattern, text)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                continue
    return None


# ── Step functions ────────────────────────────────────────────────────────────

def _step_revenue(company: Company, db: Session) -> dict:
    """Copy revenue_annual_usd from latest financials row → revenue_ttm."""
    if company.revenue_ttm is not None:
        return {"status": "already_set", "value": float(company.revenue_ttm)}

    latest = db.scalars(
        select(Financial)
        .where(
            Financial.company_id == company.id,
            Financial.revenue_annual_usd.isnot(None),
        )
        .order_by(Financial.snapshot_date.desc())
        .limit(1)
    ).first()

    if latest and latest.revenue_annual_usd:
        company.revenue_ttm = Decimal(str(latest.revenue_annual_usd))
        db.commit()
        return {
            "status": "backfilled",
            "value": latest.revenue_annual_usd,
            "from_date": str(latest.snapshot_date),
        }
    return {"status": "no_financial_data"}


def _step_employees(company: Company, client: anthropic.Anthropic, db: Session) -> dict:
    """Search for current employee count."""
    prompt = (
        f"Search for the current number of employees at {company.name} "
        f"({company.ticker or 'no ticker'}, {company.country or 'unknown country'}). "
        "Return ONLY a JSON object in a code block, no other text:\n"
        "```json\n"
        '{"employee_count": <integer or null>, "source": "<linkedin|company_website|annual_report|news>"}\n'
        "```"
    )
    raw = _search(client, prompt)
    data = _extract_json(raw)
    if not data or not isinstance(data, dict):
        return {"status": "parse_error", "raw": raw[:200]}

    count = data.get("employee_count")
    source = data.get("source", "web_search")

    if count and isinstance(count, (int, float)) and count > 0:
        company.employee_count = int(count)
        company.employee_count_source = str(source)[:50]
        company.employee_count_updated = date.today()
        db.commit()
        return {"status": "updated", "employee_count": int(count), "source": source}

    return {"status": "not_found", "raw": raw[:200]}


def _step_hq(company: Company, client: anthropic.Anthropic, db: Session) -> dict:
    """Search for HQ city and country."""
    prompt = (
        f"Search for the headquarters location of {company.name} "
        f"({company.ticker or 'no ticker'}). "
        "Return ONLY a JSON object in a code block:\n"
        "```json\n"
        '{"hq_city": "<city name>", "hq_country": "<country name>"}\n'
        "```"
    )
    raw = _search(client, prompt)
    data = _extract_json(raw)
    if not data or not isinstance(data, dict):
        return {"status": "parse_error", "raw": raw[:200]}

    city    = data.get("hq_city")
    country = data.get("hq_country")

    if city or country:
        if city:    company.hq_city    = str(city)[:100]
        if country: company.hq_country = str(country)[:100]
        db.commit()
        return {"status": "updated", "hq_city": city, "hq_country": country}

    return {"status": "not_found", "raw": raw[:200]}


def _step_leadership(company: Company, client: anthropic.Anthropic, db: Session) -> dict:
    """Search for current C-suite and create company_leadership records."""
    prompt = (
        f"Search for the current CEO, CIO, CTO, CDO, CAIO (Chief AI Officer), "
        f"and VP of AI at {company.name} ({company.ticker or 'no ticker'}, {company.country or ''}). "
        "Return ONLY a JSON array in a code block. "
        "Only include roles you find confirmed in a search result:\n"
        "```json\n"
        "[\n"
        '  {"role": "CEO", "person_name": "<full name>", "location_city": "<city or null>", "location_country": "<country or null>"},\n'
        '  {"role": "CIO", "person_name": "<full name>", "location_city": null, "location_country": null}\n'
        "]\n"
        "```\n"
        "Use these exact role codes: CEO, CIO, CTO, CDO, CAIO, VP_AI"
    )
    raw = _search(client, prompt)
    data = _extract_json(raw)
    if not data or not isinstance(data, list):
        return {"status": "parse_error", "raw": raw[:200]}

    created: list[dict] = []
    skipped: list[str] = []

    # Get existing roles for this company to avoid duplicates
    existing_roles = {
        r[0] for r in db.execute(
            select(CompanyLeadership.role)
            .where(
                CompanyLeadership.company_id == company.id,
                CompanyLeadership.is_current == True,
            )
        ).all()
    }

    for entry in data:
        if not isinstance(entry, dict):
            continue
        role        = str(entry.get("role", "")).strip().upper()
        person_name = entry.get("person_name")
        if not role or not person_name:
            continue

        # Canonicalise role code
        role = _CANONICAL_ROLES.get(role, role)
        score = ROLE_SCORES.get(role, 1)

        if role in existing_roles:
            skipped.append(f"{role} (already exists)")
            continue

        rec = CompanyLeadership(
            company_id      = company.id,
            role            = role,
            person_name     = str(person_name)[:200],
            location_city   = str(entry.get("location_city") or "")[:100] or None,
            location_country= str(entry.get("location_country") or "")[:100] or None,
            is_current      = True,
            signal_score    = score,
            source          = "web_search",
        )
        db.add(rec)
        existing_roles.add(role)
        created.append({"role": role, "person_name": str(person_name)})

    if created:
        db.commit()

    return {"status": "ok", "created": created, "skipped": skipped}


def _step_signals(company: Company, client: anthropic.Anthropic, db: Session) -> dict:
    """Search for recent AI/tech announcements and create signal records."""
    cutoff = (date.today() - timedelta(days=365)).strftime("%B %Y")
    prompt = (
        f"Search for recent AI strategy, technology partnership, digital transformation, "
        f"and technology investment announcements by {company.name} "
        f"({company.ticker or 'no ticker'}) since {cutoff}. "
        "Include press releases, news articles, and earnings commentary. "
        "Return ONLY a JSON array in a code block with up to 8 items:\n"
        "```json\n"
        "[\n"
        "  {\n"
        '    "signal_type": "ai_announcement",\n'
        '    "signal_category": "AI",\n'
        '    "signal_title": "<concise title>",\n'
        '    "signal_date": "YYYY-MM-DD",\n'
        '    "signal_url": "<url or null>",\n'
        '    "spend_impact_direction": "up",\n'
        '    "score_points": 3\n'
        "  }\n"
        "]\n"
        "```\n"
        "signal_type must be one of: ai_announcement, partnership, contract_win, earnings_signal, regulatory\n"
        "signal_category must be one of: AI, Cloud, OT, Digital, Cybersecurity, Infrastructure\n"
        "spend_impact_direction: up (spend increasing), down (spend decreasing), neutral\n"
        "score_points: 1 (minor) to 5 (major strategic)"
    )
    raw = _search(client, prompt)
    data = _extract_json(raw)
    if not data or not isinstance(data, list):
        return {"status": "parse_error", "raw": raw[:200]}

    # Existing signal titles to avoid duplicates
    existing_titles = {
        r[0] for r in db.execute(
            select(CompanyTechSignal.signal_title)
            .where(CompanyTechSignal.company_id == company.id)
        ).all()
        if r[0]
    }

    created: list[str] = []
    for entry in data:
        if not isinstance(entry, dict):
            continue
        title = entry.get("signal_title", "")
        if not title or title in existing_titles:
            continue

        sig_type = str(entry.get("signal_type", "partnership"))[:50]
        sig_cat  = str(entry.get("signal_category", ""))[:20] or None
        sig_url  = entry.get("signal_url") or None

        raw_date = entry.get("signal_date")
        sig_date: Optional[date] = None
        if raw_date:
            try:
                sig_date = date.fromisoformat(str(raw_date)[:10])
            except ValueError:
                pass

        direction = str(entry.get("spend_impact_direction", "neutral"))[:10]
        score     = int(entry.get("score_points", 1))
        score     = max(1, min(5, score))

        rec = CompanyTechSignal(
            company_id            = company.id,
            signal_type           = sig_type,
            signal_category       = sig_cat,
            signal_date           = sig_date,
            signal_title          = str(title)[:500],
            signal_description    = None,
            signal_url            = str(sig_url)[:500] if sig_url else None,
            spend_impact_direction= direction,
            score_points          = score,
            source                = "web_search",
            week_batch_date       = date.today(),
        )
        db.add(rec)
        existing_titles.add(title)
        created.append(title[:80])

    if created:
        db.commit()

    return {"status": "ok", "created": created}


def _step_estimate(company_id: int, db: Session) -> dict:
    """Run the spend estimator and store the result."""
    try:
        from app.services.spend_estimator import estimate
        result = estimate(company_id, db)
        return {
            "status": "ok",
            "confidence": result["confidence_level"],
            "total_mid": result["total_spend"]["mid"],
            "wwt_high":  result["wwt_addressable"]["high"],
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ── Public API ────────────────────────────────────────────────────────────────

def enrich_company(company_id: int, db: Session) -> dict:
    """
    Enrich a single active company. Returns a result dict with per-step
    status. Raises ValueError if company not found or not active.
    """
    company = db.get(Company, company_id)
    if not company:
        raise ValueError(f"Company {company_id} not found")
    if company.status != CompanyStatus.active:
        raise ValueError(
            f"Company {company_id} ({company.name}) is not active (status={company.status.value})"
        )

    result: dict = {
        "company_id":   company_id,
        "company_name": company.name,
        "ticker":       company.ticker,
        "steps":        {},
        "errors":       [],
    }

    client = _get_client()

    def _run_step(name: str, fn, *args):
        print(f"  [{name}] ...", flush=True)
        try:
            outcome = fn(*args)
            result["steps"][name] = outcome
            status = outcome.get("status", "?")
            detail = ""
            if name == "employees" and outcome.get("employee_count"):
                detail = f" → {outcome['employee_count']:,}"
            elif name == "hq" and outcome.get("hq_city"):
                detail = f" → {outcome['hq_city']}, {outcome['hq_country']}"
            elif name == "leadership" and outcome.get("created"):
                detail = f" → {len(outcome['created'])} roles"
            elif name == "signals" and outcome.get("created"):
                detail = f" → {len(outcome['created'])} signals"
            elif name == "estimate" and outcome.get("total_mid") is not None:
                from app.services.run_estimates import _fmt
                detail = f" → {_fmt(outcome['total_mid'])} total mid"
            print(f"  [{name}] {status}{detail}", flush=True)
        except Exception as exc:
            msg = str(exc)
            result["steps"][name] = {"status": "error", "error": msg}
            result["errors"].append(f"{name}: {msg}")
            print(f"  [{name}] ERROR: {msg}", flush=True)
            if os.environ.get("ENRICH_DEBUG"):
                traceback.print_exc()

    _run_step("revenue_ttm",  _step_revenue,    company,        db)
    _run_step("employees",    _step_employees,  company, client, db)
    _run_step("hq",           _step_hq,         company, client, db)
    _run_step("leadership",   _step_leadership, company, client, db)
    _run_step("signals",      _step_signals,    company, client, db)
    _run_step("estimate",     _step_estimate,   company_id,     db)

    return result
