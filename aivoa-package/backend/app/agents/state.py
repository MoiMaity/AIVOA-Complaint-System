"""Shared state passed between LangGraph nodes.

Every node reads what it needs and writes only its own slice, so the graph can
be extended (or nodes reordered) without nodes stepping on each other.
"""

from __future__ import annotations

from typing import Annotated, Any, TypedDict


def merge_lists(existing: list[Any] | None, new: list[Any] | None) -> list[Any]:
    """Reducer so any node can append warnings without clobbering earlier ones."""
    return (existing or []) + (new or [])


class IntakeState(TypedDict, total=False):
    # Input
    raw_text: str
    filename: str | None

    # Node outputs
    fields: dict[str, dict[str, Any]]
    completeness: dict[str, Any]
    risk: dict[str, Any]
    duplicates: list[dict[str, Any]]
    recommendations: dict[str, Any]
    summary: str

    # Diagnostics surfaced to the user (e.g. "ran without an API key")
    warnings: Annotated[list[str], merge_lists]
