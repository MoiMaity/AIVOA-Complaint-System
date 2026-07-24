"""Duplicate complaint detection.

In a real QMS the same field issue often arrives twice — once by email from the
customer and once through the distributor — and logging both inflates complaint
metrics and splits the investigation. This check runs before saving.

Scoring is deterministic (no LLM call) so the result is reproducible and cheap:
  * same batch/lot number is the strongest signal
  * same product plus similar description is the next strongest
"""

from __future__ import annotations

from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Complaint
from app.schemas import DuplicateMatch

# Below this the match is noise; above it a reviewer should take a look.
SIMILARITY_THRESHOLD = 0.62
CANDIDATE_LIMIT = 200


def find_duplicates(
    db: Session,
    *,
    product_name: str | None,
    batch_lot_number: str | None,
    complaint_description: str | None,
    exclude_id: str | None = None,
) -> list[DuplicateMatch]:
    if not any([product_name, batch_lot_number, complaint_description]):
        return []

    stmt = select(Complaint).order_by(Complaint.created_at.desc()).limit(CANDIDATE_LIMIT)
    candidates = db.execute(stmt).scalars().all()

    matches: list[DuplicateMatch] = []
    for candidate in candidates:
        if exclude_id and candidate.id == exclude_id:
            continue

        score, reason = _score(
            candidate,
            product_name=product_name,
            batch_lot_number=batch_lot_number,
            complaint_description=complaint_description,
        )
        if score >= SIMILARITY_THRESHOLD:
            matches.append(
                DuplicateMatch(
                    complaint_id=candidate.id,
                    complaint_number=candidate.complaint_number,
                    similarity=round(score, 2),
                    reason=reason,
                )
            )

    matches.sort(key=lambda m: m.similarity, reverse=True)
    return matches[:5]


def _score(
    candidate: Complaint,
    *,
    product_name: str | None,
    batch_lot_number: str | None,
    complaint_description: str | None,
) -> tuple[float, str]:
    reasons: list[str] = []
    score = 0.0

    if batch_lot_number and candidate.batch_lot_number:
        batch_similarity = fuzz.ratio(
            _norm(batch_lot_number), _norm(candidate.batch_lot_number)
        ) / 100
        if batch_similarity > 0.9:
            score += 0.55
            reasons.append(f"same batch {candidate.batch_lot_number}")
        elif batch_similarity > 0.75:
            score += 0.25
            reasons.append("near-identical batch number")

    if product_name and candidate.product_name:
        product_similarity = fuzz.token_set_ratio(
            _norm(product_name), _norm(candidate.product_name)
        ) / 100
        if product_similarity > 0.85:
            score += 0.20
            reasons.append("same product")

    if complaint_description and candidate.complaint_description:
        text_similarity = fuzz.token_set_ratio(
            _norm(complaint_description), _norm(candidate.complaint_description)
        ) / 100
        score += 0.35 * text_similarity
        if text_similarity > 0.7:
            reasons.append("very similar description")

    return min(score, 1.0), ", ".join(reasons) or "partial field overlap"


def _norm(value: str) -> str:
    return " ".join(value.lower().split())
