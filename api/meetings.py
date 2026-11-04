"""Meetings API Endpoints"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from pydantic import BaseModel
from database.connection import get_db
from database.models import Meeting

router = APIRouter()


class MeetingResponse(BaseModel):
    id: UUID
    title: str
    meeting_type: str
    scheduled_at: str
    status: str

    class Config:
        from_attributes = True


@router.get("/", response_model=List[MeetingResponse])
async def list_meetings(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List meetings"""
    meetings = db.query(Meeting).offset(skip).limit(limit).all()
    return meetings
