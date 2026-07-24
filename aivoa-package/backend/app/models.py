"""ORM models.

Complaint columns intentionally mirror the four sections of the intake form:
  1. Origin & customer details
  2. Product & batch identification
  3. Complaint details
  4. Initial assessment & priority

Extra columns (status, ai_metadata, source_*) exist because a QMS complaint
record has to carry its own audit trail: what came in, what the AI proposed,
and what a human ultimately saved.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Complaint(Base):
    __tablename__ = "complaints"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    complaint_number: Mapped[str] = mapped_column(String(32), unique=True, index=True)

    # 1. Origin & customer details
    complaint_source: Mapped[str | None] = mapped_column(String(120))
    customer_name: Mapped[str | None] = mapped_column(String(200))

    # 2. Product & batch identification
    product_name: Mapped[str | None] = mapped_column(String(200), index=True)
    product_strength: Mapped[str | None] = mapped_column(String(120))
    batch_lot_number: Mapped[str | None] = mapped_column(String(120), index=True)
    manufacturing_date: Mapped[date | None] = mapped_column(Date)
    expiry_date: Mapped[date | None] = mapped_column(Date)
    quantity_affected: Mapped[float | None] = mapped_column(Float)
    quantity_unit: Mapped[str | None] = mapped_column(String(32), default="kg")

    # 3. Complaint details
    complaint_type: Mapped[str | None] = mapped_column(String(120), index=True)
    complaint_date: Mapped[date | None] = mapped_column(Date)
    complaint_description: Mapped[str | None] = mapped_column(Text)

    # 4. Initial assessment & priority
    initial_severity: Mapped[str | None] = mapped_column(String(32))
    priority: Mapped[str | None] = mapped_column(String(32))

    # Workflow
    status: Mapped[str] = mapped_column(String(40), default="Pending Triage", index=True)

    # Audit / AI trail
    source_document_name: Mapped[str | None] = mapped_column(String(255))
    source_text: Mapped[str | None] = mapped_column(Text)
    # Holds confidences, completeness gaps, risk rationale, CAPA and summary.
    ai_metadata: Mapped[dict | None] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ComplaintCounter(Base):
    """Sequence for human-readable complaint numbers (CMP-2026-0001).

    A dedicated row is used rather than the primary key so the visible number
    stays gap-free per year even if records are created and rolled back.
    """

    __tablename__ = "complaint_counters"

    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    last_value: Mapped[int] = mapped_column(Integer, default=0)
