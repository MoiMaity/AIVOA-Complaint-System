"""FastAPI entrypoint for the AIVOA complaint management API."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routers import ai, complaints

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if not settings.llm_enabled:
        logger.warning(
            "GROQ_API_KEY is not set — extraction will fall back to rule-based "
            "parsing and chat will be unavailable."
        )
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description=(
        "AI-assisted customer complaint intake for API and FDF pharmaceutical "
        "manufacturing. Upload or paste a complaint, and a LangGraph agent "
        "extracts the record, classifies risk, checks for duplicates and drafts "
        "investigation and CAPA suggestions for a QA reviewer to approve."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(complaints.router, prefix=settings.api_prefix)
app.include_router(ai.router, prefix=settings.api_prefix)


@app.get(f"{settings.api_prefix}/health", tags=["system"])
def health() -> dict[str, object]:
    """Used by the UI to show whether AI features are live."""
    return {
        "status": "ok",
        "environment": settings.environment,
        "llm_enabled": settings.llm_enabled,
        "extraction_model": settings.groq_model,
        "reasoning_model": settings.groq_reasoning_model,
    }
