"""AI routes — document extraction (streamed) and the assistant chat."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.agents.graph import STAGES, intake_graph
from app.agents.prompts import CHAT_SYSTEM
from app.config import settings
from app.database import get_db
from app.schemas import ChatRequest, ChatResponse
from app.services.document_parser import UnsupportedDocumentError, extract_text
from app.services.llm import LLMUnavailableError, chat

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/extract")
async def extract(
    file: UploadFile | None = File(default=None),
    text: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    """Run the intake agent and stream progress as newline-delimited JSON.

    NDJSON rather than SSE: the client already posts a multipart body, and
    fetch + ReadableStream handles this without a second round trip.
    """
    source_text, filename = await _resolve_input(file, text)

    async def event_stream() -> AsyncGenerator[bytes, None]:
        yield _event(
            {
                "type": "progress",
                "percent": 5,
                "message": "Analysing document content and extracting key details…",
            }
        )

        state: dict[str, Any] = {}
        try:
            async for update in intake_graph.astream(
                {"raw_text": source_text, "filename": filename},
                config={"configurable": {"db": db}},
            ):
                for node_name, node_output in update.items():
                    _merge(state, node_output)
                    percent, message = STAGES.get(node_name, (0, ""))
                    if percent:
                        yield _event(
                            {
                                "type": "progress",
                                "stage": node_name,
                                "percent": percent,
                                "message": message,
                            }
                        )

        except Exception as exc:  # noqa: BLE001 — surface any failure to the UI
            logger.exception("Extraction failed")
            yield _event({"type": "error", "message": f"Extraction failed: {exc}"})
            return

        yield _event(
            {
                "type": "result",
                "result": {
                    "fields": state.get("fields", {}),
                    "completeness": state.get("completeness"),
                    "risk": state.get("risk"),
                    "duplicates": state.get("duplicates", []),
                    "recommendations": state.get("recommendations"),
                    "summary": state.get("summary"),
                    "warnings": state.get("warnings", []),
                    "raw_text_preview": source_text[:2000],
                    "source_document_name": filename,
                },
            }
        )

    return StreamingResponse(
        event_stream(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/chat", response_model=ChatResponse)
async def assistant_chat(payload: ChatRequest) -> ChatResponse:
    """Answer questions about the complaint currently open in the form."""
    form_lines = "\n".join(
        f"- {key}: {value}" for key, value in payload.form_state.items() if value
    ) or "(form is empty)"

    context = (
        f"Current form state:\n{form_lines}\n\n"
        f"Original complaint document:\n{(payload.source_text or '(none uploaded)')[:6000]}"
    )

    messages = [
        {"role": "system", "content": CHAT_SYSTEM},
        {"role": "system", "content": context},
        *[{"role": m.role, "content": m.content} for m in payload.history[-8:]],
        {"role": "user", "content": payload.message},
    ]

    try:
        reply = await chat(
            messages,
            model=settings.groq_reasoning_model,
            temperature=0.3,
            max_tokens=700,
        )
    except LLMUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return ChatResponse(reply=reply.strip())


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
async def _resolve_input(
    file: UploadFile | None, text: str | None
) -> tuple[str, str | None]:
    if file is not None and file.filename:
        data = await file.read()
        if len(data) > settings.max_upload_bytes:
            limit_mb = settings.max_upload_bytes // (1024 * 1024)
            raise HTTPException(
                status_code=413, detail=f"File is larger than the {limit_mb} MB limit."
            )
        try:
            return extract_text(file.filename, data), file.filename
        except UnsupportedDocumentError as exc:
            raise HTTPException(status_code=415, detail=str(exc)) from exc

    if text and text.strip():
        return text.strip(), None

    raise HTTPException(
        status_code=400, detail="Upload a complaint document or paste the complaint text."
    )


def _merge(state: dict[str, Any], update: dict[str, Any] | None) -> None:
    """Accumulate node outputs, appending warnings instead of replacing them."""
    for key, value in (update or {}).items():
        if key == "warnings":
            state.setdefault("warnings", []).extend(value or [])
        else:
            state[key] = value


def _event(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload) + "\n").encode("utf-8")
