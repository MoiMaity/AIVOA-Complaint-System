"""Thin async wrapper around Groq's OpenAI-compatible chat completions API.

Two models are used on purpose:
  * gemma2-9b-it        — fast, cheap, does the structured field extraction
  * llama-3.3-70b-versatile — better reasoning for risk, CAPA and chat answers

Both are configurable via .env so a reviewer can force everything onto one model.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class LLMUnavailableError(RuntimeError):
    """No API key configured, or Groq could not be reached."""


async def chat(
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
    temperature: float = 0.1,
    json_mode: bool = False,
    max_tokens: int = 1500,
) -> str:
    if not settings.llm_enabled:
        raise LLMUnavailableError(
            "GROQ_API_KEY is not set. Add it to backend/.env to enable AI extraction."
        )

    payload: dict[str, Any] = {
        "model": model or settings.groq_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    headers = {
        "Authorization": f"Bearer {settings.groq_api_key}",
        "Content-Type": "application/json",
    }
    url = f"{settings.groq_base_url}/chat/completions"

    last_error: Exception | None = None
    for attempt in range(settings.groq_max_retries + 1):
        try:
            async with httpx.AsyncClient(timeout=settings.groq_timeout_seconds) as client:
                response = await client.post(url, json=payload, headers=headers)

            if response.status_code == 429:
                # Groq rate limit — back off and retry rather than failing the run.
                wait = 2**attempt
                logger.warning("Groq rate limited, retrying in %ss", wait)
                await asyncio.sleep(wait)
                last_error = LLMUnavailableError("Groq rate limit reached.")
                continue

            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]

        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:300]
            logger.error("Groq HTTP %s: %s", exc.response.status_code, detail)
            raise LLMUnavailableError(f"Groq returned {exc.response.status_code}.") from exc
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            last_error = exc
            logger.warning("Groq request failed (attempt %s): %s", attempt + 1, exc)
            await asyncio.sleep(1 + attempt)

    raise LLMUnavailableError(f"Could not reach Groq: {last_error}")


async def chat_json(
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
    temperature: float = 0.0,
    max_tokens: int = 1500,
) -> dict[str, Any]:
    """Ask for JSON and return a dict, tolerating the usual model quirks."""
    raw = await chat(
        messages,
        model=model,
        temperature=temperature,
        json_mode=True,
        max_tokens=max_tokens,
    )
    return parse_json_object(raw)


def parse_json_object(raw: str) -> dict[str, Any]:
    """Parse model output into a dict.

    Even in JSON mode a model occasionally wraps output in code fences or adds a
    sentence of preamble, so fall back to extracting the outermost object.
    """
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise ValueError(f"Model did not return JSON: {raw[:200]}")
        parsed = json.loads(match.group(0))

    if not isinstance(parsed, dict):
        raise ValueError("Expected a JSON object at the top level.")
    return parsed
