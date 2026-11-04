"""Analytics API Endpoints"""

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session
from database.connection import get_db
from database.models import Deal, Contact, Customer

router = APIRouter()


@router.get("/dashboard")
async def get_dashboard(db: Session = Depends(get_db)):
    """Get dashboard metrics"""

    # Count metrics
    total_leads = db.query(Contact).count()
    total_deals = db.query(Deal).count()
    total_customers = db.query(Customer).count()

    # Revenue metrics
    total_pipeline = db.query(Deal).filter(
        Deal.stage.in_(['prospecting', 'qualification', 'proposal', 'negotiation'])
    ).with_entities(func.sum(Deal.value)).scalar() or 0

    total_mrr = db.query(Customer).with_entities(
        func.sum(Customer.mrr)
    ).scalar() or 0

    return {
        "leads": {
            "total": total_leads,
            "qualified": db.query(Contact).filter(Contact.lead_status == 'qualified').count()
        },
        "deals": {
            "total": total_deals,
            "pipeline_value": float(total_pipeline)
        },
        "customers": {
            "total": total_customers,
            "mrr": float(total_mrr),
            "arr": float(total_mrr * 12)
        }
    }


@router.get("/pipeline")
async def get_pipeline_metrics(db: Session = Depends(get_db)):
    """Get pipeline breakdown by stage"""

    stages = ['prospecting', 'qualification', 'proposal', 'negotiation', 'closed_won', 'closed_lost']
    pipeline = {}

    for stage in stages:
        count = db.query(Deal).filter(Deal.stage == stage).count()
        value = db.query(Deal).filter(Deal.stage == stage).with_entities(
            func.sum(Deal.value)
        ).scalar() or 0

        pipeline[stage] = {
            "count": count,
            "value": float(value)
        }

    return pipeline
