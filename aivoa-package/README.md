# AIVOA — AI-Powered Customer Complaint Management System

An AI-assisted customer-complaint intake system for **pharmaceutical API and FDF
manufacturing**, built for the AIVOA Round 1 full-stack assessment.

A QA reviewer uploads a complaint document (or pastes an email). A LangGraph
agent reads it, extracts a structured complaint record, classifies the risk,
checks for duplicates, and drafts investigation and CAPA suggestions. The form
populates itself, the reviewer verifies and edits, and the record is committed
to the QMS ledger. An embedded assistant answers questions about the complaint
on screen.

> **The human stays in charge.** Nothing is saved automatically. Every
> AI-filled field shows a confidence score and is editable; the risk
> classification and CAPA actions are framed as suggestions for a reviewer to
> accept or reject. This mirrors how a real Quality Management System works —
> the model proposes, a qualified person disposes.

---

## What it does

**Core workflow (from the demo)**
- Upload **PDF / DOCX / TXT / EML** or paste raw complaint text
- Streamed extraction progress driven by real agent steps, not a fake timer
- The four-section intake form auto-populates with per-field confidence
- Save allocates a QMS complaint number (`CMP-2026-0001`) and queues it for triage
- Ask the assistant follow-up questions grounded in the document and the form

**Bonus AI features (all implemented)**
| Feature | Where |
|---|---|
| Complaint completeness checker | `completeness` node → *Completeness check* card |
| AI risk classification (severity + priority + reportability) | `risk` node → *AI risk classification* card |
| Duplicate complaint detection | `duplicates` node + pre-save check → warning banner |
| Root-cause recommendation | `recommend` node → *Probable root causes* card |
| CAPA recommendation | `recommend` node → *Draft CAPA actions* card |
| Complaint summary | `summarise` node → *Complaint summary* card |

---

## Mandatory stack — as required

| Layer | Requirement | Used |
|---|---|---|
| Frontend | React + Redux | React 18 + Redux Toolkit + Vite |
| Backend | Python + FastAPI | FastAPI + Uvicorn |
| Agent framework | LangGraph | LangGraph `StateGraph` pipeline |
| LLM | Groq `gemma2-9b-it` | Extraction node. `llama-3.3-70b-versatile` for reasoning nodes |
| Database | MySQL / Postgres | SQLAlchemy — switch by changing one URL |
| Font | Google Inter | Loaded in `index.html`, used site-wide |

---

## How the agent is built

The intake agent is a **linear LangGraph pipeline**:

```
parse → extract → completeness → risk → duplicates → recommend → summarise
```

Linear rather than branching on purpose — QMS intake is a fixed regulated
sequence, and every complaint must pass through the same steps in the same order
to be auditable. LangGraph still earns its place: a shared typed state object,
per-node error isolation (a failed CAPA suggestion never loses the extracted
batch number), and `astream`, which lets the API report genuine progress to the
UI as each node finishes.

Two Groq models are used deliberately: fast `gemma2-9b-it` for structured
extraction, and `llama-3.3-70b-versatile` for the reasoning-heavy risk, CAPA and
chat steps. Both are configurable in `.env`.

Every classification the model makes is constrained to a **controlled
vocabulary** (complaint type, severity, priority) that is shared between the
backend prompts and the frontend dropdowns — so free-text drift can't corrupt
the data that a QMS would later use for trending and regulatory reporting.

### Offline mode
If `GROQ_API_KEY` is unset, extraction falls back to a rule-based parser and the
UI shows an **Offline mode** badge plus a per-run warning. This lets a reviewer
clone the repo and watch the whole workflow before wiring up a key — the
fallback is never presented as model output.

---

## Project layout

```
aivoa/
├── backend/
│   ├── app/
│   │   ├── agents/          # LangGraph graph, nodes, prompts, shared state
│   │   ├── routers/         # /ai (extract + chat), /complaints (CRUD)
│   │   ├── services/        # document parsing, Groq client, duplicates, fallback
│   │   ├── config.py  database.py  models.py  schemas.py  main.py
│   ├── samples/             # example complaints (2 text, 1 PDF)
│   ├── requirements.txt     .env.example
└── frontend/
    ├── src/
    │   ├── api/client.js     # REST + NDJSON streaming reader
    │   ├── store/            # Redux Toolkit slices (complaint, ai)
    │   ├── components/       # form + assistant panel
    │   ├── constants.js  App.jsx  main.jsx  index.css
    ├── index.html            package.json  vite.config.js
```

---

## Quick start

Full step-by-step is in **[SETUP_OVERVIEW.md](./SETUP_OVERVIEW.md)**. In short:

```bash
# 1. Database (Postgres shown)
createdb aivoa_complaints

# 2. Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # add your GROQ_API_KEY
uvicorn app.main:app --reload # → http://127.0.0.1:8000/api/health

# 3. Frontend (new terminal)
cd frontend
npm install
npm run dev                   # → http://localhost:5173
```

Open the app, drag `backend/samples/complaint_03_oos_report.pdf` into the
dropzone, and watch the form populate.

---

## Notes for the reviewer

- **Risk overrides extraction.** The extract node records what the complaint
  *claims*; the risk node reasons about patient impact and then overrides
  `initial_severity` / `priority` with a rationale. A customer calling something
  "urgent" shouldn't set your GMP severity.
- **Duplicate check runs before save**, because logging the same defect twice
  splits an investigation and skews complaint trending. Log
  `complaint_01`, then `complaint_02` (which references a prior batch) to see it.
- **Production-grade OCR is intentionally out of scope**, per the brief. Image
  uploads return a clear message asking for a PDF or pasted text.
- **This was built with AI assistance** and then reviewed and adapted by hand so
  the workflow matches the demo — as the assignment directs.

## AI development disclosure

Per the assignment's instructions, code was generated with AI assistance and
then read, adapted, and wired to the demonstrated workflow rather than pasted
verbatim. The architectural choices (linear graph, dual-model split, controlled
vocabularies, human-in-the-loop confidence, offline fallback) are deliberate and
are explained inline in the source.
