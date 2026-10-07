# TARA Assistant

AI-assisted Threat Analysis and Risk Assessment (TARA) for automotive systems, aligned with ISO/SAE 21434 and UN R155 Annex 5. Human-in-the-loop: the AI suggests, reviewers approve, edit, or reject every item.

## Status

Frame build complete (Phases 5–8 of 8). All 24 tests pass; mock end-to-end run verified (validate → attack surface → suggest → assess → review → audit → traceability → Markdown export). The threat library is regulation-sourced (UN R155 Annex 5 via `Code/scripts/build_threat_library.py`, 60 threats); STRIDE tags and asset links are our annotations — see `Documentation/Synthetic_Data_Validation.md`.

## Structure

```
PCCOE_StudentName_PRN_CSx_AIML/
├── Synopsis/
├── Input_Data/              # JSON/XML/CSV dropped in here; no code changes needed
├── Code/
│   ├── app/
│   │   ├── main.py          # FastAPI entry point  ✔
│   │   ├── config.py        # settings from env + Model_Prompts_Config/.env  ✔
│   │   ├── schemas.py       # Pydantic domain models + review/audit/traceability  ✔
│   │   ├── db.py            # SQLite via SQLAlchemy + audit log  ✔
│   │   ├── llm/             # provider abstraction + fallback chain  ✔
│   │   ├── rag/             # ingest, embed, retrieve via ChromaDB  ✔ (in-memory fallback included)
│   │   ├── services/        # asset/attack-surface/threat/risk/mitigation/traceability/review  ✔
│   │   └── routers/         # typed API endpoints (17 routes)  ✔
│   ├── ui/
│   │   ├── streamlit_app.py  # dashboard wireframe: stepper + cards + master-detail review  ✔
│   │   └── diagram.py        # dependency-free layered SVG of the architecture  ✔
│   ├── tests/               # 27 tests, all passing  ✔
│   └── scripts/             # build_threat_library.py regenerates the library
# plus workspace-root requirements.txt: pip install -r requirements.txt
├── Model_Prompts_Config/    # .env.example, versioned prompt templates
├── Evaluation_Results/
├── Documentation/           # this file, CONTEXT.md, diagrams
├── Video/
└── Declarations/
```

## Setup

```powershell
# from the workspace root (C:\Users\LEGION\Documents\TATA)
venv\Scripts\pip install -r requirements.txt
Copy-Item PCCOE_StudentName_PRN_CSx_AIML\Model_Prompts_Config\.env.example PCCOE_StudentName_PRN_CSx_AIML\Model_Prompts_Config\.env
# edit .env: set GROQ_API_KEY and LLM_PROVIDER=groq (or leave it for offline mock mode)
# optional, needs torch: venv\Scripts\pip install -r requirements-ml.txt  (BGE + ChromaDB)
```

Or one shot on Windows: `run.bat` (venv + deps + `.env` bootstrap + API + UI).
Everything runs on localhost: SQLite is a local file (`Code/tara.db`, created on
first run), the API serves the UI on `localhost:8000`, and only LLM provider
calls (e.g. Groq) leave the machine.

## Free-tier Groq notes

- Defaults: `llama-3.3-70b-versatile` (30 req/min, ~1,000 req/day, 100K tokens/day).
  Each suggest call sends a few thousand tokens of library context, so bursts
  hit the per-minute ceiling fast.
- The app retries with backoff (longer on 429s) and fails loudly with the cause
  instead of returning silent empties — watch the UI's `API error:` detail line.
- Roomier daily budget: set `GROQ_MODEL=llama-3.1-8b-instant` in `.env`
  (weaker at structured JSON; keep 70B for quality). Any provider model is
  overridable via `{PROVIDER}_MODEL`. `/config` shows the active model.

## Run

```powershell
cd PCCOE_StudentName_PRN_CSx_AIML\Code
..\..\venv\Scripts\uvicorn app.main:app --reload        # API + docs at http://localhost:8000/docs
..\..\venv\Scripts\streamlit run ui\streamlit_app.py   # UI (talks to API_URL, default localhost:8000)
..\..\venv\Scripts\python -m pytest tests -q            # 37 tests
```

## Run with Docker (PROJECT.md suggested stack)

```powershell
# from the workspace root (C:\Users\LEGION\Documents\TATA)
docker compose up --build        # API on :8000, UI on :8501, state in the tara-data volume
```

`compose.yml`/`Dockerfile` live at the workspace root (not inside the submission
folder). `compose config` validates; the image build itself is unverified on
machines without a Docker daemon. Secrets stay out of the image: copy
`Model_Prompts_Config/.env.example` to `.env` and mount/provide keys via environment.

## Config

`app/config.py` resolves settings from env vars, then `Model_Prompts_Config/.env`, then safe offline defaults (`LLM_PROVIDER=mock`). Every data path and provider key is config-only — switching to a private/local LLM or a new data folder is a config change, not a code change.

## Agentic pipeline (PLAN §5a)

Procedural services were replaced internally by a LangGraph `StateGraph` with
one analyst agent (the only LLM access) plus a deterministic retrieval step.
Routes, schemas, and the UI contract are unchanged.

```
suggest/assess call
  │  initial knowledge_requests + template variables
  ▼
┌───────────┐   requests   ┌──────────┐   drafts/requests   ┌──────────┐
│ Retrieval │ ───────────▶ │ Analyst  │ ─────────────────▶ │ Validate │ ─▶ drafts
│   step    │ ◀─────────── │  agent   │   needs more +      └──────────┘
└───────────┘  retrieved   └──────────┘   rounds < MAX_KNOWLEDGE_ROUNDS (2)
   │ context              (sole LLM access,
   │ deterministic;        v2 prompts from
   │ only module           Model_Prompts_Config/)
   │ touching RAGStore
   ▼
retrieval_log              Pydantic check + flag_uncited;
(query, filters,           budget exhaustion → "needs expert review"
 returned IDs)
```

Rules enforced by tests: only `agents/knowledge.py` (the deterministic retrieval step) imports `RAGStore` at runtime; loops are hard-capped (`MAX_KNOWLEDGE_ROUNDS`, default 2); risk values stay matrix-computed (`POST /risks/assess` gains only an opt-in `rationale` flag for analyst-proposed ratings); approval stays outside the graph (review endpoints).

## Verification & quality (PROJECT.md steps 21, 11)

- `POST /verifications` links a mitigation to a test activity (`test_method`, planned/passed/failed); verifications are reviewable and audited like everything else, and appear as the fifth element of every traceability chain. Unverified mitigations raise a `mitigation_without_verification` gap.
- `GET /report/metrics` returns knowledge-reuse %, review-completion %, and chain-completeness % computed from stored data; `Code/scripts/snapshot_metrics.py` writes the same snapshot to `Evaluation_Results/metrics.json`.
- Threat records carry `mapping_owner` / `mapping_review_date` / `mapping_version` (written by the builder); the Knowledge Base page badges each mapping fresh/stale (>365 days).
