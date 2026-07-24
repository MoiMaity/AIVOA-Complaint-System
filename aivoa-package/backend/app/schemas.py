"""Pydantic schemas — the contract between FastAPI and the React client."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

SEVERITY = Literal["Critical", "Major", "Minor"]
PRIORITY = Literal["Urgent", "High", "Medium", "Low"]


# --------------------------------------------------------------------------
# Extraction
# --------------------------------------------------------------------------
class ExtractedField(BaseModel):
    """A single AI-extracted value plus how sure the model was about it.

    Confidence is surfaced in the UI so a QA reviewer knows which auto-filled
    fields deserve a second look before the record is saved.
    """

    value: str | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    source_snippet: str | None = None


class ExtractionResult(BaseModel):
    fields: dict[str, ExtractedField] = Field(default_factory=dict)
    completeness: "CompletenessReport | None" = None
    risk: "RiskAssessment | None" = None
    duplicates: list["DuplicateMatch"] = Field(default_factory=list)
    recommendations: "Recommendations | None" = None
    summary: str | None = None
    raw_text_preview: str | None = None
    warnings: list[str] = Field(default_factory=list)


class CompletenessReport(BaseModel):
    score: int = Field(default=0, ge=0, le=100)
    missing_required: list[str] = Field(default_factory=list)
    follow_up_questions: list[str] = Field(default_factory=list)


class RiskAssessment(BaseModel):
    severity: SEVERITY | None = None
    priority: PRIORITY | None = None
    rationale: str | None = None
    regulatory_reportable: bool = False


class DuplicateMatch(BaseModel):
    complaint_id: str
    complaint_number: str
    similarity: float
    reason: str


class Recommendations(BaseModel):
    probable_root_causes: list[str] = Field(default_factory=list)
    capa_actions: list[str] = Field(default_factory=list)
    investigation_steps: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------
# Complaint CRUD
# --------------------------------------------------------------------------
class ComplaintBase(BaseModel):
    complaint_source: str | None = None
    customer_name: str | None = None

    product_name: str | None = None
    product_strength: str | None = None
    batch_lot_number: str | None = None
    manufacturing_date: date | None = None
    expiry_date: date | None = None
    quantity_affected: float | None = None
    quantity_unit: str | None = "kg"

    complaint_type: str | None = None
    complaint_date: date | None = None
    complaint_description: str | None = None

    initial_severity: str | None = None
    priority: str | None = None


class ComplaintCreate(ComplaintBase):
    source_document_name: str | None = None
    source_text: str | None = None
    ai_metadata: dict[str, Any] | None = None


class ComplaintUpdate(ComplaintBase):
    status: str | None = None


class ComplaintRead(ComplaintBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    complaint_number: str
    status: str
    source_document_name: str | None = None
    ai_metadata: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class ComplaintListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    complaint_number: str
    product_name: str | None = None
    batch_lot_number: str | None = None
    complaint_type: str | None = None
    initial_severity: str | None = None
    priority: str | None = None
    status: str
    created_at: datetime


# --------------------------------------------------------------------------
# Chat
# --------------------------------------------------------------------------
class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = Field(default_factory=list)
    # Current (possibly human-edited) form state, so answers reflect the screen.
    form_state: dict[str, Any] = Field(default_factory=dict)
    source_text: str | None = None


class ChatResponse(BaseModel):
    reply: str


ExtractionResult.model_rebuild()
