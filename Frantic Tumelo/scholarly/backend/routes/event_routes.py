"""
Event routes — upcoming tests and PTM scheduling.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import date

from database import get_db
from models import Teacher, Event
from auth import get_current_teacher

router = APIRouter(prefix="/api/events", tags=["events"])


class EventCreate(BaseModel):
    title: str
    description: Optional[str] = ""
    event_type: str  # "test" or "ptm"
    event_date: date
    target_class: Optional[int] = None
    target_section: Optional[str] = None

class EventOut(BaseModel):
    id: int
    title: str
    description: str
    event_type: str
    event_date: str
    target_class: int | None
    target_section: str | None
    teacher_name: str | None
    created_at: str

    class Config:
        from_attributes = True


@router.get("/", response_model=list[EventOut])
def list_events(
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    events = db.query(Event).filter(
        (Event.target_class == teacher.assigned_class) | (Event.target_class == None),
        (Event.target_section == teacher.assigned_section) | (Event.target_section == None),
    ).order_by(Event.event_date).all()
    return [_to_out(e) for e in events]


@router.post("/", response_model=EventOut, status_code=201)
def create_event(
    payload: EventCreate,
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    if payload.event_type not in ("test", "ptm"):
        raise HTTPException(status_code=400, detail="Event type must be 'test' or 'ptm'")
    if not payload.title.strip():
        raise HTTPException(status_code=400, detail="Title is required")
    
    event = Event(
        title=payload.title.strip(),
        description=payload.description or "",
        event_type=payload.event_type,
        event_date=payload.event_date,
        target_class=payload.target_class or teacher.assigned_class,
        target_section=payload.target_section or teacher.assigned_section,
        teacher_id=teacher.id,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return _to_out(event)


@router.delete("/{event_id}", status_code=204)
def delete_event(
    event_id: int,
    teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.teacher_id != teacher.id and not teacher.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    db.delete(event)
    db.commit()


def _to_out(e: Event) -> EventOut:
    return EventOut(
        id=e.id, title=e.title, description=e.description or "",
        event_type=e.event_type, event_date=str(e.event_date),
        target_class=e.target_class, target_section=e.target_section,
        teacher_name=e.teacher.full_name if e.teacher else None,
        created_at=e.created_at.strftime("%b %d, %Y") if e.created_at else "—",
    )
