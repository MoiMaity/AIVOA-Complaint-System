"""The complaint intake graph.

    parse ──▶ extract ──▶ completeness ──▶ risk ──▶ duplicates ──▶ recommend ──▶ summarise

It is a linear pipeline rather than a branching agent, and that is a deliberate
choice: QMS intake is a fixed regulated sequence, and every complaint must go
through the same steps in the same order so the result is auditable. LangGraph
still earns its place here — the shared state object, per-node error isolation,
and `astream` giving the UI real progress rather than a fake timer.
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agents import nodes
from app.agents.state import IntakeState

# Node name → (progress %, message shown under the progress bar).
STAGES: dict[str, tuple[int, str]] = {
    "parse": (10, "Reading the document…"),
    "extract": (45, "Extracting complaint details…"),
    "completeness": (60, "Checking the record is complete…"),
    "risk": (75, "Assessing severity and priority…"),
    "duplicates": (85, "Checking for duplicate complaints…"),
    "recommend": (95, "Drafting investigation and CAPA suggestions…"),
    "summarise": (100, "Done."),
}


def build_graph():
    builder = StateGraph(IntakeState)

    builder.add_node("parse", nodes.parse_input)
    builder.add_node("extract", nodes.extract_fields)
    builder.add_node("completeness", nodes.check_completeness)
    builder.add_node("risk", nodes.classify_risk)
    builder.add_node("duplicates", nodes.detect_duplicates)
    builder.add_node("recommend", nodes.recommend)
    builder.add_node("summarise", nodes.summarise)

    builder.add_edge(START, "parse")
    builder.add_edge("parse", "extract")
    builder.add_edge("extract", "completeness")
    builder.add_edge("completeness", "risk")
    builder.add_edge("risk", "duplicates")
    builder.add_edge("duplicates", "recommend")
    builder.add_edge("recommend", "summarise")
    builder.add_edge("summarise", END)

    return builder.compile()


# Compiled once at import; the graph itself is stateless between runs.
intake_graph = build_graph()
