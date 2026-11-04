"""Deals API Endpoints"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from pydantic import BaseModel
from database.connection import get_db
from database.models import Deal

router = APIRouter()


class DealCreate(BaseModel):
    name: str
    value: float
    stage: str
    contact_id: str = None
    company_id: str = None


class DealResponse(BaseModel):
    id: UUID
    name: str
    value: float
    stage: str
    health_score: int
    is_stalled: bool

    class Config:
        from_attributes = True


@router.get("/", response_model=List[DealResponse])
async def list_deals(
    skip: int = 0,
    limit: int = 100,
    stage: str = None,
    db: Session = Depends(get_db)
):
    """List all deals"""
    query = db.query(Deal)
    if stage:
        query = query.filter(Deal.stage == stage)
    deals = query.offset(skip).limit(limit).all()
    return deals


@router.get("/{deal_id}", response_model=DealResponse)
async def get_deal(deal_id: str, db: Session = Depends(get_db)):
    """Get deal by ID"""
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    return deal


@router.post("/", response_model=DealResponse)
async def create_deal(deal: DealCreate, db: Session = Depends(get_db)):
    """Create new deal"""
    db_deal = Deal(**deal.dict())
    db.add(db_deal)
    db.commit()
    db.refresh(db_deal)
    return db_deal


@router.patch("/{deal_id}/stage")
async def update_deal_stage(
    deal_id: str,
    stage: str,
    db: Session = Depends(get_db)
):
    """Update deal stage"""
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    deal.stage = stage
    db.commit()
    return {"status": "updated", "stage": stage}
