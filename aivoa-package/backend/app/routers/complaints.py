"""Complaint CRUD routes."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Complaint, ComplaintCounter
from app.schemas import (
    ComplaintCreate,
    ComplaintListItem,
    ComplaintRead,
    ComplaintUpdate,
    DuplicateMatch,
)
from app.services.duplicates import find_duplicates

router = APIRouter(prefix="/complaints", tags=["complaints"])


@router.post("", response_model=ComplaintRead, status_code=201)
def create_complaint(payload: ComplaintCreate, db: Session = Depends(get_db)):
    complaint = Complaint(
        complaint_number=_next_complaint_number(db),
        status="Pending Triage",
        **payload.model_dump(),
    )
    db.add(complaint)
    db.commit()
    db.refresh(complaint)
    return complaint


@router.get("", response_model=list[ComplaintListItem])
def list_complaints(
    db: Session = Depends(get_db),
    limit: int = Query(default=50, le=200),
    status: str | None = None,
):
    stmt = select(Complaint).order_by(Complaint.created_at.desc()).limit(limit)
    if status:
        stmt = stmt.where(Complaint.status == status)
    return db.execute(stmt).scalars().all()


@router.get("/{complaint_id}", response_model=ComplaintRead)
def get_complaint(complaint_id: str, db: Session = Depends(get_db)):
    complaint = db.get(Complaint, complaint_id)
    if complaint is None:
        raise HTTPException(status_code=404, detail="Complaint not found.")
    return complaint


@router.patch("/{complaint_id}", response_model=ComplaintRead)
def update_complaint(
    complaint_id: str, payload: ComplaintUpdate, db: Session = Depends(get_db)
):
    complaint = db.get(Complaint, complaint_id)
    if complaint is None:
        raise HTTPException(status_code=404, detail="Complaint not found.")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(complaint, key, value)

    db.commit()
    db.refresh(complaint)
    return complaint


@router.post("/check-duplicates", response_model=list[DuplicateMatch])
def check_duplicates(payload: ComplaintCreate, db: Session = Depends(get_db)):
    """Called from the form before saving, so the reviewer sees a warning first."""
    return find_duplicates(
        db,
        product_name=payload.product_name,
        batch_lot_number=payload.batch_lot_number,
        complaint_description=payload.complaint_description,
    )


def _next_complaint_number(db: Session) -> str:
    """Allocate the next CMP-<year>-<seq> number.

    with_for_update() locks the counter row so two reviewers saving at the same
    moment can't be handed the same complaint number.
    """
    year = date.today().year
    counter = db.execute(
        select(ComplaintCounter).where(ComplaintCounter.year == year).with_for_update()
    ).scalar_one_or_none()

    if counter is None:
        counter = ComplaintCounter(year=year, last_value=0)
        db.add(counter)
        db.flush()

    counter.last_value += 1
    db.flush()
    return f"CMP-{year}-{counter.last_value:04d}"
