"""Dashboard API - one denormalized read endpoint plus two synchronous agent actions.

The dashboard page (static/index.html) uses these so it can show company names,
and so it can show an agent's result immediately instead of polling.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import Company, Contact, Customer, Deal, Email

router = APIRouter()

OPEN_STAGES = ["prospecting", "qualification", "proposal", "negotiation"]

_orchestrator = None


def get_orchestrator():
    """Create the agent orchestrator on first use."""
    global _orchestrator
    if _orchestrator is None:
        from workflows.orchestrator import AgentOrchestrator

        _orchestrator = AgentOrchestrator()
    return _orchestrator


def _iso(value) -> Optional[str]:
    return value.isoformat() if value else None


def _full_name(first, last, fallback=""):
    name = " ".join(p for p in [first, last] if p)
    return name or fallback


@router.get("/summary")
async def summary(db: Session = Depends(get_db)):
    """Everything the dashboard needs in one call."""
    orch = get_orchestrator()
    llm = orch.llm

    companies = {c.id: c.name for c in db.query(Company).all()}

    contacts = db.query(Contact).order_by(Contact.created_at.desc()).limit(200).all()
    contact_names = {c.id: _full_name(c.first_name, c.last_name, c.email) for c in contacts}

    deals = db.query(Deal).order_by(Deal.value.desc()).all()
    customers = db.query(Customer).order_by(Customer.mrr.desc()).all()
    emails = db.query(Email).order_by(Email.created_at.desc()).limit(50).all()

    open_deals = [d for d in deals if d.stage in OPEN_STAGES]
    won_deals = [d for d in deals if d.stage == "closed_won"]
    total_mrr = sum(c.mrr or 0 for c in customers)

    kpis = {
        "leads_total": len(contacts),
        "leads_qualified": sum(1 for c in contacts if (c.lead_score or 0) >= 60),
        "pipeline_value": sum(d.value or 0 for d in open_deals),
        "forecast_value": sum((d.value or 0) * (d.probability or 0) / 100 for d in open_deals),
        "open_deals": len(open_deals),
        "stalled_deals": sum(1 for d in open_deals if d.is_stalled),
        "won_value": sum(d.value or 0 for d in won_deals),
        "customers": len(customers),
        "mrr": total_mrr,
        "arr": total_mrr * 12,
        "at_risk_customers": sum(1 for c in customers if c.churn_risk in ("medium", "high")),
        "avg_customer_health": round(sum(c.health_score or 0 for c in customers) / len(customers))
        if customers
        else 0,
        "negative_emails": sum(1 for e in emails if e.sentiment == "negative"),
    }

    return {
        "llm": {"provider": llm.name, "model": llm.model},
        "agents": orch.get_agent_status(),
        "kpis": kpis,
        "leads": [
            {
                "id": str(c.id),
                "name": _full_name(c.first_name, c.last_name, c.email),
                "email": c.email,
                "job_title": c.job_title,
                "company": companies.get(c.company_id),
                "score": c.lead_score or 0,
                "status": c.lead_status,
                "source": c.lead_source,
                "created_at": _iso(c.created_at),
            }
            for c in contacts
        ],
        "deals": [
            {
                "id": str(d.id),
                "name": d.name,
                "company": companies.get(d.company_id),
                "contact": contact_names.get(d.contact_id),
                "stage": d.stage,
                "value": d.value or 0,
                "probability": d.probability or 0,
                "health_score": d.health_score or 0,
                "is_stalled": bool(d.is_stalled),
                "expected_close_date": _iso(d.expected_close_date),
                "notes": d.notes,
            }
            for d in deals
        ],
        "customers": [
            {
                "id": str(c.id),
                "company": companies.get(c.company_id),
                "plan": c.plan,
                "mrr": c.mrr or 0,
                "health_score": c.health_score or 0,
                "churn_risk": c.churn_risk,
                "churn_probability": c.churn_probability or 0,
                "license_usage_percent": c.license_usage_percent or 0,
                "support_tickets_30d": c.support_tickets_30d or 0,
                "nps_score": c.nps_score or 0,
            }
            for c in customers
        ],
        "emails": [
            {
                "id": str(e.id),
                "from": e.from_email,
                "subject": e.subject,
                "body": e.body,
                "sentiment": e.sentiment,
                "sentiment_score": e.sentiment_score,
                "category": e.category,
                "priority": e.priority,
                "draft_response": e.draft_response,
                "created_at": _iso(e.created_at),
            }
            for e in emails
        ],
    }


class LeadIn(BaseModel):
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    job_title: Optional[str] = None
    company_name: Optional[str] = None
    message: Optional[str] = None  # what the lead actually said; the agent finds signals in it
    lead_source: Optional[str] = "dashboard"


@router.post("/leads")
async def add_lead(lead: LeadIn, db: Session = Depends(get_db)):
    """Run the Lead Qualification Agent now, save the lead, and return the result."""
    if db.query(Contact).filter(Contact.email == lead.email).first():
        raise HTTPException(status_code=409, detail="A lead with that email already exists")

    orch = get_orchestrator()
    try:
        result = await orch.lead_agent.execute({"lead_data": lead.model_dump()})
    except Exception as exc:  # LLM/network problems should reach the UI, not crash it
        raise HTTPException(status_code=502, detail=f"Lead agent failed: {exc}")

    company_id = None
    if lead.company_name:
        company = db.query(Company).filter(Company.name == lead.company_name).first()
        if not company:
            company = Company(name=lead.company_name)
            db.add(company)
            db.flush()
        company_id = company.id

    routing = result.get("routing", {})
    contact = Contact(
        email=lead.email,
        first_name=lead.first_name,
        last_name=lead.last_name,
        job_title=lead.job_title,
        company_id=company_id,
        lead_source=lead.lead_source,
        lead_score=result.get("score", 0),
        lead_status=routing.get("team", "Marketing Nurture"),
        enrichment_data=result.get("enriched_data"),
    )
    db.add(contact)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A lead with that email already exists")

    return {
        "id": str(contact.id),
        "score": contact.lead_score,
        "team": contact.lead_status,
        "priority": routing.get("priority"),
        "recommended_action": routing.get("recommended_action"),
        "signals": [x for x in result.get("signals", []) if x != "Mock LLM response"],
    }


class EmailIn(BaseModel):
    sender: Optional[str] = "customer@example.com"
    subject: str = ""
    body: str


@router.post("/emails")
async def analyze_email(email: EmailIn, db: Session = Depends(get_db)):
    """Run the Email Intelligence Agent now, save the email, and return the analysis."""
    orch = get_orchestrator()
    payload = {"from": email.sender, "subject": email.subject, "body": email.body}
    try:
        result = await orch.email_agent.execute({"email_data": payload})
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Email agent failed: {exc}")

    sentiment = result.get("sentiment", {})
    record = Email(
        from_email=email.sender,
        subject=email.subject,
        body=email.body,
        direction="inbound",
        sentiment=sentiment.get("label"),
        sentiment_score=sentiment.get("score"),
        emotion=sentiment.get("emotion"),
        category=result.get("category"),
        priority=result.get("priority"),
        draft_response=result.get("draft_response"),
        received_at=datetime.utcnow(),
    )
    db.add(record)
    db.commit()

    return {
        "id": str(record.id),
        "sentiment": sentiment,
        "category": result.get("category"),
        "priority": result.get("priority"),
        "draft_response": result.get("draft_response"),
        "follow_up_suggestions": result.get("follow_up_suggestions", []),
        "requires_human_review": result.get("requires_human_review", False),
    }
