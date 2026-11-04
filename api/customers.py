"""Customers API Endpoints"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from pydantic import BaseModel
from database.connection import get_db
from database.models import Customer

router = APIRouter()


class CustomerResponse(BaseModel):
    id: UUID
    plan: str
    mrr: float
    health_score: int
    churn_risk: str

    class Config:
        from_attributes = True


@router.get("/", response_model=List[CustomerResponse])
async def list_customers(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all customers"""
    customers = db.query(Customer).offset(skip).limit(limit).all()
    return customers


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(customer_id: str, db: Session = Depends(get_db)):
    """Get customer by ID"""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.get("/{customer_id}/health")
async def get_customer_health(customer_id: str, db: Session = Depends(get_db)):
    """Get customer health metrics"""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    return {
        "health_score": customer.health_score,
        "churn_risk": customer.churn_risk,
        "churn_probability": customer.churn_probability,
        "engagement": {
            "logins_per_week": customer.logins_per_week,
            "features_used": customer.features_used,
            "license_usage_percent": customer.license_usage_percent
        }
    }
