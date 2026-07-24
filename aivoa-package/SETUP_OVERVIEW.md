# SETUP OVERVIEW

Step-by-step setup for the AIVOA complaint management system. Two processes run
side by side: the FastAPI backend on port **8000** and the Vite dev server on
port **5173**. The frontend proxies `/api` to the backend, so you only ever open
`http://localhost:5173` in the browser.

---

## 0. Prerequisites

| Tool | Version | Check |
|---|---|---|
| Python | 3.11+ | `python --version` |
| Node.js | 18+ | `node --version` |
| A database | PostgreSQL 13+ **or** MySQL 8+ | `psql --version` / `mysql --version` |
| Groq API key | — | from <https://console.groq.com/keys> |

> No Groq key handy? You can still run everything — the app starts in **offline
> mode** and uses a rule-based extractor. Add the key later to enable full AI
> extraction and chat.

---

## 1. Create the database

The app auto-creates its tables on first start (via SQLAlchemy). You only need
to create an empty database and a user.

### Option A — PostgreSQL (default)

```bash
# as a superuser
psql -c "CREATE USER aivoa WITH PASSWORD 'aivoa';"
psql -c "CREATE DATABASE aivoa_complaints OWNER aivoa;"
```

Connection URL:
```
postgresql+psycopg2://aivoa:aivoa@localhost:5432/aivoa_complaints
```

### Option B — MySQL

```sql
CREATE DATABASE aivoa_complaints CHARACTER SET utf8mb4;
CREATE USER 'aivoa'@'localhost' IDENTIFIED BY 'aivoa';
GRANT ALL PRIVILEGES ON aivoa_complaints.* TO 'aivoa'@'localhost';
FLUSH PRIVILEGES;
```

Connection URL:
```
mysql+pymysql://aivoa:aivoa@localhost:3306/aivoa_complaints
```

**Switching databases requires no code change** — only the `DATABASE_URL` in
`.env`.

---

## 2. Backend

```bash
cd backend

# isolated environment
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r requirements.txt

# configuration
cp .env.example .env
```

Edit `backend/.env`:

```ini
GROQ_API_KEY=gsk_your_real_key_here
GROQ_MODEL=gemma2-9b-it
GROQ_REASONING_MODEL=llama-3.3-70b-versatile

# use whichever line matches the DB you created in step 1
DATABASE_URL=postgresql+psycopg2://aivoa:aivoa@localhost:5432/aivoa_complaints
# DATABASE_URL=mysql+pymysql://aivoa:aivoa@localhost:3306/aivoa_complaints

CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

Run it:

```bash
uvicorn app.main:app --reload
```

Verify:

```bash
curl http://127.0.0.1:8000/api/health
# {"status":"ok","llm_enabled":true,"extraction_model":"gemma2-9b-it", ...}
```

Interactive API docs: <http://127.0.0.1:8000/docs>

> `llm_enabled: false` means the key wasn't picked up — the app runs in offline
> mode. Check `backend/.env` and restart.

---

## 3. Frontend

In a **second terminal**:

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>.

The dev server proxies `/api` → `http://127.0.0.1:8000`, so no CORS or base-URL
config is needed for local development. (For a deployed build on a different
origin, set `VITE_API_BASE_URL` in `frontend/.env`.)

---

## 4. Try the workflow

1. In the right-hand **AI Complaint Intake Assistant** panel, drag
   `backend/samples/complaint_03_oos_report.pdf` onto the dropzone
   (or click **Paste complaint text / email** and paste one of the `.txt`
   samples).
2. The progress bar advances through the real agent steps: reading → extracting
   → completeness → risk → duplicates → recommendations → summary.
3. The left-hand form fills in. AI-filled fields are tinted and show a
   confidence chip (amber under 60%). Edit anything — your value replaces the
   AI's and the tint clears.
4. Review the insight cards: summary, risk classification, completeness gaps,
   root causes, CAPA drafts.
5. Click **Save complaint**. A duplicate check runs first; if nothing similar
   exists, the record is saved as `CMP-2026-000N` and appears in *Recently
   logged complaints*.
6. Ask the assistant a question, e.g. *"What is the out-of-specification assay
   result?"* or *"What should we ask the customer next?"*

### See duplicate detection fire
Log `complaint_01_foreign_matter.txt`, then log it again (or a lightly edited
copy). On the second save you'll get a **Possible duplicate** banner with the
matching complaint number, similarity score, and reason, and the option to save
it as a separate complaint anyway.

---

## 5. Sample documents

| File | Format | Demonstrates |
|---|---|---|
| `complaint_01_foreign_matter.txt` | Email text | Contamination → Critical severity, reportable |
| `complaint_02_labelling.txt` | Portal form text | Labelling defect + references a prior batch |
| `complaint_03_oos_report.pdf` | PDF | Out-of-specification analytical result, PDF parsing |

All are fictional and were created for this demonstration.

---

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Badge shows **Offline mode** | `GROQ_API_KEY` missing or invalid in `backend/.env`; restart uvicorn |
| `sqlalchemy ... could not connect` | DB not running, or `DATABASE_URL` wrong |
| `psycopg2` build error | `pip install psycopg2-binary` (already in requirements) |
| Frontend can't reach API | Backend not on `:8000`, or started after the frontend — restart `npm run dev` |
| Chat returns 503 | AI is in offline mode — chat needs a live Groq key |
| Image upload rejected | Expected — OCR is out of scope; use a PDF or paste text |
| Rate-limit warnings in logs | Groq free-tier limit; the client backs off and retries automatically |

---

## Architecture at a glance

```
Browser (React + Redux, port 5173)
   │  multipart upload / paste
   ▼
POST /api/ai/extract  ──streams NDJSON──▶  progress + result
   │
   ▼
LangGraph intake agent
   parse → extract → completeness → risk → duplicates → recommend → summarise
                │                    │          │
          Groq gemma2-9b-it   Groq llama-3.3   SQLAlchemy (duplicate lookup)
   │
   ▼
Reviewer edits & saves  ──▶  POST /api/complaints  ──▶  Postgres / MySQL
```
