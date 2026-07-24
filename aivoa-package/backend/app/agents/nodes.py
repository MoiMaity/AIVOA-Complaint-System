"""Node implementations for the complaint intake graph.

Design rule followed throughout: a node that fails degrades the run, it never
kills it. A missing CAPA suggestion is an inconvenience; losing the extracted
batch number because the recommendation call timed out would not be.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.runnables import RunnableConfig

from app.agents.prompts import (
    COMPLAINT_TYPES,
    COMPLETENESS_SYSTEM,
    EXTRACTION_SYSTEM,
    FIELD_KEYS,
    PRIORITIES,
    RECOMMENDATION_SYSTEM,
    REQUIRED_FIELDS,
    RISK_SYSTEM,
    SEVERITIES,
    SUMMARY_SYSTEM,
)
from app.agents.state import IntakeState
from app.config import settings
from app.services import duplicates as duplicate_service
from app.services.heuristics import heuristic_extract
from app.services.llm import LLMUnavailableError, chat, chat_json

logger = logging.getLogger(__name__)

# Long documents are truncated: complaint letters put the substance up front,
# and this keeps token cost and latency predictable.
MAX_CHARS = 12_000

FIELD_LABELS = {
    "complaint_source": "complaint source",
    "customer_name": "customer name",
    "product_name": "product name",
    "product_strength": "product strength / grade",
    "batch_lot_number": "batch / lot number",
    "manufacturing_date": "manufacturing date",
    "expiry_date": "expiry date",
    "quantity_affected": "quantity affected",
    "quantity_unit": "quantity unit",
    "complaint_type": "complaint type",
    "complaint_date": "complaint date",
    "complaint_description": "complaint description",
    "initial_severity": "initial severity",
    "priority": "priority",
}


# --------------------------------------------------------------------------
# 1. Parse
# --------------------------------------------------------------------------
async def parse_input(state: IntakeState, config: RunnableConfig) -> dict[str, Any]:
    text = (state.get("raw_text") or "").strip()
    warnings: list[str] = []

    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS]
        warnings.append(
            f"Document truncated to the first {MAX_CHARS:,} characters for analysis."
        )

    return {"raw_text": text, "warnings": warnings}


# --------------------------------------------------------------------------
# 2. Extract fields
# --------------------------------------------------------------------------
async def extract_fields(state: IntakeState, config: RunnableConfig) -> dict[str, Any]:
    text = state.get("raw_text", "")
    if not text:
        return {"fields": {}, "warnings": ["No text to analyse."]}

    try:
        result = await chat_json(
            [
                {"role": "system", "content": EXTRACTION_SYSTEM},
                {"role": "user", "content": f"Complaint document:\n\n{text}"},
            ],
            model=settings.groq_model,
            max_tokens=2000,
        )
        fields = _clean_fields(result.get("fields", {}))
        if not fields:
            raise ValueError("Model returned no usable fields.")
        return {"fields": fields, "warnings": []}

    except (LLMUnavailableError, ValueError, KeyError) as exc:
        logger.warning("Falling back to rule-based extraction: %s", exc)
        return {
            "fields": _clean_fields(heuristic_extract(text)),
            "warnings": [
                "AI extraction unavailable — used rule-based extraction instead. "
                "Please review every field before saving."
            ],
        }


def _clean_fields(raw: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Keep known keys, coerce types, and force enums into the allowed vocabulary."""
    cleaned: dict[str, dict[str, Any]] = {}

    for key, payload in (raw or {}).items():
        if key not in FIELD_KEYS:
            continue
        if not isinstance(payload, dict):
            payload = {"value": payload, "confidence": 0.5}

        value = payload.get("value")
        if value is None or str(value).strip().lower() in {"", "null", "none", "n/a", "not stated"}:
            continue

        value = str(value).strip()

        if key == "complaint_type":
            value = _closest(value, COMPLAINT_TYPES) or value
        elif key == "initial_severity":
            value = _closest(value, SEVERITIES) or value
        elif key == "priority":
            value = _closest(value, PRIORITIES) or value

        try:
            confidence = float(payload.get("confidence", 0.5))
        except (TypeError, ValueError):
            confidence = 0.5

        cleaned[key] = {
            "value": value,
            "confidence": max(0.0, min(1.0, confidence)),
            "source_snippet": (payload.get("source_snippet") or None),
        }

    return cleaned


def _closest(value: str, options: list[str]) -> str | None:
    """Map a model's phrasing onto the controlled vocabulary."""
    lowered = value.lower()
    for option in options:
        if lowered == option.lower():
            return option
    for option in options:
        if lowered in option.lower() or option.lower() in lowered:
            return option
    return None


# --------------------------------------------------------------------------
# 3. Completeness check
# --------------------------------------------------------------------------
async def check_completeness(state: IntakeState, config: RunnableConfig) -> dict[str, Any]:
    fields = state.get("fields", {})
    missing = [key for key in REQUIRED_FIELDS if not fields.get(key, {}).get("value")]

    filled = len(REQUIRED_FIELDS) - len(missing)
    score = round(100 * filled / len(REQUIRED_FIELDS))

    questions: list[str] = []
    if missing:
        try:
            result = await chat_json(
                [
                    {"role": "system", "content": COMPLETENESS_SYSTEM},
                    {
                        "role": "user",
                        "content": (
                            f"Extracted so far: {_readable(fields)}\n\n"
                            f"Missing: {[FIELD_LABELS[m] for m in missing]}"
                        ),
                    },
                ],
                model=settings.groq_reasoning_model,
                max_tokens=500,
            )
            questions = [str(q) for q in result.get("follow_up_questions", [])][:4]
        except (LLMUnavailableError, ValueError) as exc:
            logger.warning("Completeness questions unavailable: %s", exc)
            questions = [
                f"Could you confirm the {FIELD_LABELS[m]}?" for m in missing[:4]
            ]

    return {
        "completeness": {
            "score": score,
            "missing_required": [FIELD_LABELS[m] for m in missing],
            "follow_up_questions": questions,
        }
    }


# --------------------------------------------------------------------------
# 4. Risk classification
# --------------------------------------------------------------------------
async def classify_risk(state: IntakeState, config: RunnableConfig) -> dict[str, Any]:
    fields = state.get("fields", {})

    try:
        result = await chat_json(
            [
                {"role": "system", "content": RISK_SYSTEM},
                {
                    "role": "user",
                    "content": (
                        f"Complaint fields: {_readable(fields)}\n\n"
                        f"Original text:\n{state.get('raw_text', '')[:4000]}"
                    ),
                },
            ],
            model=settings.groq_reasoning_model,
            max_tokens=600,
        )
        severity = _closest(str(result.get("severity", "")), SEVERITIES)
        priority = _closest(str(result.get("priority", "")), PRIORITIES)
        risk = {
            "severity": severity,
            "priority": priority,
            "rationale": result.get("rationale"),
            "regulatory_reportable": bool(result.get("regulatory_reportable", False)),
        }
    except (LLMUnavailableError, ValueError) as exc:
        logger.warning("Risk classification unavailable: %s", exc)
        risk = {
            "severity": fields.get("initial_severity", {}).get("value"),
            "priority": fields.get("priority", {}).get("value"),
            "rationale": None,
            "regulatory_reportable": False,
        }

    # The risk node is the authority on these two fields — it reasons about
    # patient impact, whereas extraction only reports what the letter claimed.
    updated = dict(fields)
    if risk["severity"]:
        updated["initial_severity"] = {
            "value": risk["severity"],
            "confidence": 0.8,
            "source_snippet": None,
        }
    if risk["priority"]:
        updated["priority"] = {
            "value": risk["priority"],
            "confidence": 0.8,
            "source_snippet": None,
        }

    return {"risk": risk, "fields": updated}


# --------------------------------------------------------------------------
# 5. Duplicate detection
# --------------------------------------------------------------------------
async def detect_duplicates(state: IntakeState, config: RunnableConfig) -> dict[str, Any]:
    db = (config.get("configurable") or {}).get("db")
    if db is None:
        return {"duplicates": []}

    fields = state.get("fields", {})
    matches = duplicate_service.find_duplicates(
        db,
        product_name=fields.get("product_name", {}).get("value"),
        batch_lot_number=fields.get("batch_lot_number", {}).get("value"),
        complaint_description=fields.get("complaint_description", {}).get("value"),
    )
    return {"duplicates": [m.model_dump() for m in matches]}


# --------------------------------------------------------------------------
# 6. Root cause & CAPA recommendations
# --------------------------------------------------------------------------
async def recommend(state: IntakeState, config: RunnableConfig) -> dict[str, Any]:
    fields = state.get("fields", {})
    risk = state.get("risk", {})

    try:
        result = await chat_json(
            [
                {"role": "system", "content": RECOMMENDATION_SYSTEM},
                {
                    "role": "user",
                    "content": (
                        f"Complaint: {_readable(fields)}\n"
                        f"Severity assessment: {risk.get('severity')} — "
                        f"{risk.get('rationale')}"
                    ),
                },
            ],
            model=settings.groq_reasoning_model,
            max_tokens=900,
        )
        recommendations = {
            "probable_root_causes": [str(x) for x in result.get("probable_root_causes", [])][:4],
            "investigation_steps": [str(x) for x in result.get("investigation_steps", [])][:5],
            "capa_actions": [str(x) for x in result.get("capa_actions", [])][:4],
        }
    except (LLMUnavailableError, ValueError) as exc:
        logger.warning("Recommendations unavailable: %s", exc)
        recommendations = {
            "probable_root_causes": [],
            "investigation_steps": [],
            "capa_actions": [],
        }

    return {"recommendations": recommendations}


# --------------------------------------------------------------------------
# 7. Summary
# --------------------------------------------------------------------------
async def summarise(state: IntakeState, config: RunnableConfig) -> dict[str, Any]:
    fields = state.get("fields", {})

    try:
        summary = await chat(
            [
                {"role": "system", "content": SUMMARY_SYSTEM},
                {"role": "user", "content": _readable(fields)},
            ],
            model=settings.groq_reasoning_model,
            temperature=0.2,
            max_tokens=250,
        )
        return {"summary": summary.strip()}
    except (LLMUnavailableError, ValueError) as exc:
        logger.warning("Summary unavailable: %s", exc)
        description = fields.get("complaint_description", {}).get("value")
        return {"summary": (description or "")[:400] or None}


def _readable(fields: dict[str, dict[str, Any]]) -> str:
    """Flatten extracted fields into a compact prompt-friendly block."""
    lines = [
        f"- {FIELD_LABELS.get(key, key)}: {payload.get('value')}"
        for key, payload in fields.items()
        if payload.get("value")
    ]
    return "\n".join(lines) or "(nothing extracted yet)"
