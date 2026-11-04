"""Emails API Endpoints"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from pydantic import BaseModel
from database.connection import get_db
from database.models import Email

router = APIRouter()


class EmailResponse(BaseModel):
    id: UUID
    subject: str
    sentiment: str
    category: str
    priority: str
    draft_response: str = None

    class Config:
        from_attributes = True


@router.get("/", response_model=List[EmailResponse])
async def list_emails(
    skip: int = 0,
    limit: int = 100,
    priority: str = None,
    db: Session = Depends(get_db)
):
    """List emails"""
    query = db.query(Email)
    if priority:
        query = query.filter(Email.priority == priority)
    emails = query.offset(skip).limit(limit).all()
    return emails
