"""Leads API Endpoints"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel
from database.connection import get_db
from database.models import Contact, Company

router = APIRouter()


class LeadCreate(BaseModel):
    email: str
    first_name: str = None
    last_name: str = None
    company_name: str = None
    job_title: str = None
    lead_source: str = None


class LeadResponse(BaseModel):
    id: UUID
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    lead_score: Optional[int] = None
    lead_status: Optional[str] = None

    class Config:
        from_attributes = True


@router.get("/", response_model=List[LeadResponse])
async def list_leads(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all leads"""
    leads = db.query(Contact).offset(skip).limit(limit).all()
    return leads


@router.get("/{lead_id}", response_model=LeadResponse)
async def get_lead(lead_id: str, db: Session = Depends(get_db)):
    """Get lead by ID"""
    lead = db.query(Contact).filter(Contact.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.post("/", response_model=LeadResponse)
async def create_lead(lead: LeadCreate, db: Session = Depends(get_db)):
    """Create new lead"""
    data = lead.model_dump()
    company_name = data.pop("company_name", None)
    if company_name:
        company = db.query(Company).filter(Company.name == company_name).first()
        if not company:
            company = Company(name=company_name)
            db.add(company)
            db.flush()
        data["company_id"] = company.id
    db_lead = Contact(**data)
    db.add(db_lead)
    db.commit()
    db.refresh(db_lead)
    return db_lead


@router.delete("/{lead_id}")
async def delete_lead(lead_id: str, db: Session = Depends(get_db)):
    """Delete lead"""
    lead = db.query(Contact).filter(Contact.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    db.delete(lead)
    db.commit()
    return {"status": "deleted"}
