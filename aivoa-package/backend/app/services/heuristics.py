"""Rule-based fallback extraction.

This exists so the app still demonstrates the full workflow when GROQ_API_KEY is
missing or Groq is unreachable — a reviewer can clone the repo and see the form
populate before wiring up a key. Confidences are capped low and the UI shows an
"offline mode" warning, so this is never mistaken for model output.
"""

from __future__ import annotations

import re
from datetime import datetime

from app.agents.prompts import COMPLAINT_TYPES

_LABEL_PATTERNS: dict[str, list[str]] = {
    "customer_name": [r"customer(?:\s*name)?", r"complainant", r"company", r"from"],
    "product_name": [r"product(?:\s*name)?", r"material", r"api\s*name"],
    "product_strength": [r"strength", r"grade", r"assay", r"potency"],
    "batch_lot_number": [r"batch(?:\s*(?:no|number|/lot))?", r"lot(?:\s*(?:no|number))?"],
    "manufacturing_date": [r"mfg\.?\s*date", r"manufactur\w*\s*date", r"date of mfg"],
    "expiry_date": [r"exp(?:iry)?\.?\s*date", r"use before", r"best before"],
    "complaint_date": [r"complaint\s*date", r"date\s*(?:of\s*)?complaint", r"date raised"],
    "quantity_affected": [r"quantity\s*affected", r"qty\s*affected", r"quantity"],
}

_TYPE_KEYWORDS: list[tuple[str, list[str]]] = [
    ("Contamination / Foreign Matter", ["foreign", "particle", "contamin", "black spot", "fibre", "fiber"]),
    ("Out of Specification (Analytical)", ["out of specification", "oos", "assay", "impurity", "dissolution", "specification limit"]),
    ("Packaging / Labelling Defect", ["label", "packag", "seal", "carton", "leaflet", "misprint"]),
    ("Documentation / CoA Error", ["coa", "certificate of analysis", "document", "typo in", "paperwork"]),
    ("Quantity / Shortage Discrepancy", ["short supply", "shortage", "missing drum", "quantity discrepan", "count mismatch"]),
    ("Transit Damage", ["damaged in transit", "transit", "dented", "broken during ship", "pallet damage"]),
    ("Stability / Degradation", ["degrad", "stability", "caking", "clump", "moisture"]),
    ("Odour / Colour Change", ["odour", "odor", "smell", "discolour", "discolor", "colour change", "color change"]),
    ("Adverse Event Related", ["adverse event", "patient reaction", "hospital", "side effect"]),
    ("Physical / Appearance Defect", ["appearance", "chipped", "cracked", "broken tablet", "physical defect"]),
]

_CRITICAL_WORDS = ["contamin", "foreign", "adverse event", "patient", "sterility", "wrong product", "recall"]
_MAJOR_WORDS = ["out of specification", "oos", "assay", "degrad", "unusable", "reject"]


def heuristic_extract(text: str) -> dict[str, dict]:
    """Best-effort field extraction from labelled complaint text."""
    fields: dict[str, dict] = {}

    for key, patterns in _LABEL_PATTERNS.items():
        value = _find_labelled(text, patterns)
        if value:
            fields[key] = _field(value, 0.45, value)

    # Batch numbers are often written without a label (e.g. "Batch API-2402-118").
    if "batch_lot_number" not in fields:
        match = re.search(r"\b([A-Z]{2,4}[-/]?\d{3,6}[-/]?[A-Z0-9]{0,4})\b", text)
        if match:
            fields["batch_lot_number"] = _field(match.group(1), 0.35, match.group(0))

    for key in ("manufacturing_date", "expiry_date", "complaint_date"):
        if key in fields:
            iso = _to_iso(fields[key]["value"])
            if iso:
                fields[key]["value"] = iso
            else:
                fields.pop(key)

    if "quantity_affected" in fields:
        raw = fields["quantity_affected"]["value"]
        number = re.search(r"[\d,.]+", raw)
        if number:
            fields["quantity_affected"] = _field(number.group(0).replace(",", ""), 0.4, raw)
            unit = re.search(r"\b(kg|g|mg|L|ml|vials?|bottles?|packs?|drums?)\b", raw, re.I)
            if unit:
                fields["quantity_unit"] = _field(unit.group(1).lower(), 0.4, raw)

    lowered = text.lower()

    for label, keywords in _TYPE_KEYWORDS:
        if any(word in lowered for word in keywords):
            fields["complaint_type"] = _field(label, 0.4, None)
            break
    else:
        fields["complaint_type"] = _field(COMPLAINT_TYPES[0], 0.2, None)

    if any(word in lowered for word in _CRITICAL_WORDS):
        severity, priority = "Critical", "Urgent"
    elif any(word in lowered for word in _MAJOR_WORDS):
        severity, priority = "Major", "High"
    else:
        severity, priority = "Minor", "Medium"
    fields["initial_severity"] = _field(severity, 0.3, None)
    fields["priority"] = _field(priority, 0.3, None)

    if "@" in text and "complaint_source" not in fields:
        fields["complaint_source"] = _field("Customer Email", 0.4, None)

    description = _longest_paragraph(text)
    if description:
        fields["complaint_description"] = _field(description[:1200], 0.35, None)

    return fields


def _field(value: str, confidence: float, snippet: str | None) -> dict:
    return {
        "value": str(value).strip(),
        "confidence": confidence,
        "source_snippet": snippet[:160] if snippet else None,
    }


def _find_labelled(text: str, patterns: list[str]) -> str | None:
    for pattern in patterns:
        match = re.search(
            rf"^\s*{pattern}\s*[:\-|]\s*(.+)$", text, re.IGNORECASE | re.MULTILINE
        )
        if match:
            value = match.group(1).strip().strip("|").strip()
            if value and len(value) < 200:
                return value
    return None


def _to_iso(value: str) -> str | None:
    value = value.strip()
    formats = [
        "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y",
        "%d %b %Y", "%d %B %Y", "%b %d, %Y", "%B %d, %Y", "%b %Y", "%m/%Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    match = re.search(r"\d{4}-\d{2}-\d{2}", value)
    return match.group(0) if match else None


def _longest_paragraph(text: str) -> str | None:
    paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 80]
    return max(paragraphs, key=len) if paragraphs else None
