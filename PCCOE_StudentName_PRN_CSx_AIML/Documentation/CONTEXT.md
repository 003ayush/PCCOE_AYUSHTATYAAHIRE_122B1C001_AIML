# CONTEXT.md — current status

> Plan note (2026-10-07): `PLAN.md` §6 now specifies **architecture ingestion of JSON/XML/CSV** (exports from modeling tools like Enterprise Architect / AUTOSAR) with Pydantic validation of uploads, and explicitly **no multimodal image AI** for diagrams. Phase 4 loaders must accept XML as well as JSON/CSV. Markdown ingestion is no longer required.

## Done
- Tolerant validation (2026-10-07): Groq wrote non-enum values (`"safety"`, lowercase STRIDE, word ratings) and all drafts were dropped → schemas now normalize (case-insensitive enums, alias maps, word/numeric ratings) and drop only the unmappable value, never the whole item; repeated identical errors deduped and capped in messages (48/48).
- Guided flow + contract self-check (2026-10-07): UI verifies its paths against live OpenAPI on load (stale API terminal → sidebar names the missing routes); step 1 auto-advances to Assets; auto-suggest is best-effort so a dead LLM never blocks the deterministic pipeline.
- Groq free-tier hardening (2026-10-07): retries with backoff (longer on 429s) in `complete_json`, analyst degrades to logged errors, services raise instead of silently emptying (routers → 502 with cause), per-provider `{PROVIDER}_MODEL` override, `active_model` on `/config`; tests hermetic to live `.env`.
- `.env` hygiene + blank handling (2026-10-07): blank entries verified inert (defaults resolve); removed dead blanks and neutralized `your_*_here` fake keys in `.env` — those fakes were treated as REAL keys and would have joined the fallback chain. Template documents this; `test_config.py` added. Real Groq key preserved; provider still `mock` until you flip it.
- Startup ingest + blank-env fix (2026-10-07): API lifespan indexes `Input_Data/threat_library.json` when empty (`ensure_library_indexed`, never raises); verified 60 records indexed on boot. `Settings` treats blank `.env` entries as unset — a blank `SQLITE_URL=` used to crash the server at import. `Code/chroma_db/` kept as built functional state (gitignored, rebuilds automatically).
- Fresh-machine path (2026-10-07): core `requirements.txt` (no torch — hash embeddings + in-memory store keep the full app working), `requirements-ml.txt` for BGE/Chroma, `run.bat`/`run.sh` one-shot launchers, light-mode fallback test; SQLite/API are localhost-only.
- Brush-up vs PROJECT.md (2026-10-07): verification links (`VerificationLink` + `verifications` endpoints, fifth chain element, new gap kind), quality metrics endpoint + `Evaluation_Results/metrics.json` snapshot script, knowledge lifecycle fields + staleness badges, root `Dockerfile`/`compose.yml`/`.dockerignore` (compose-validated; image build unverified — no daemon on this machine).
- Phases 9–14 complete: `app/agents/` (`state.TaraState`, deterministic retrieval step as sole RAGStore owner with NO_MATCH sentinel + optional LLM rewrite behind `KNOWLEDGE_LLM_REWRITE`, single analyst agent wrapping LLMClient on v2 prompts, `graph` with loop cap `MAX_KNOWLEDGE_ROUNDS=2`); all four pipelines (threats, mitigations, assets, risk rationale) run through `run_task`; routers/UI contracts unchanged (`/risks/assess` gains opt-in `rationale` flag); 7 new tests (import isolation, filters, loop cap, no-match, mock E2E, matrix fallback) — 34/34 passing; `langgraph`+`langchain-core` in root `requirements.txt`.
- Phases 5–8 complete: services (`architecture`, `assets`+`attack_surface`+`trust_boundaries`+`data_flows`, `threats`, `risk` via `risk_matrix.json`, `mitigations`, `traceability`, `review` with audit), 5 versioned prompt templates + `risk_matrix.json` in `Model_Prompts_Config/`, 17-route FastAPI app (`app/main.py`), Streamlit dashboard UI matching the approved mockup (dark sidebar nav, 7-stage stepper, step-1 card grid with SVG parsed-view diagram, master-detail review, Knowledge Base + Settings), Markdown report export, 27 tests all passing, mock end-to-end verified.
- Phase 1 complete: mandatory folder skeleton created under `PCCOE_StudentName_PRN_CSx_AIML/`.
- Phase 2 complete: `Code/app/schemas.py` (Asset, Interface, Component, Architecture, ThreatScenario, ImpactAssessment/FeasibilityAssessment per ISO/SAE 21434, Risk, Mitigation, AuditEntry, TaraReport). Every reviewable artefact carries `ReviewFields` (status/reviewer/note/timestamp) and `CitationMixin` (source_ids). `Code/app/db.py` SQLAlchemy models mirror them plus append-only `audit_log`; `init_db()` verified — `tara.db` created.
- `Code/requirements.txt` lists the full frame stack (Streamlit, FastAPI, ChromaDB, SQLAlchemy, Pydantic, OpenAI-compatible client, sentence-transformers, pytest).
- `Code/app/config.py` settings loader: env vars > `Model_Prompts_Config/.env` > offline defaults (`LLM_PROVIDER=mock`). Smoke-tested and importing cleanly.
- `Model_Prompts_Config/.env.example` added; no secrets committed.
- `python-dotenv` and `pydantic` installed into the venv (rest of requirements not yet installed).

- Phase 3 complete: `Code/app/llm/` — `base.LLMClient` protocol, `mock.MockLLMClient` (offline placeholder JSON), `providers` (Gemini/Groq/OpenRouter/NVIDIA OpenAI-compatible presets, lazy `openai` import), `fallback.FallbackChain`, and `get_llm_client()` factory (configured provider first, keyed providers as fallback, mock when no keys). Smoke-tested: mock run and fallback-chain-with-failure both pass.
- Phase 4 complete (code): `Code/app/rag/` — `loaders` (JSON/XML/CSV, clear errors on bad format), `embeddings` (SentenceTransformers with deterministic hash fallback), `store.RAGStore` (ChromaDB persistent store with in-memory cosine fallback, metadata filters). Smoke-tested against `Input_Data/threat_library.json` (5 records, filtered retrieval OK).

## Data update (2026-10-07, user-supplied)
- `Code/scripts/build_threat_library.py` (new, user-authored; made its output path repo-relative) regenerates `Input_Data/threat_library.json` from UN R155 Annex 5 (OJ L 82, 9.3.2021, via EUR-Lex): 60 threats (`THREAT-001`–`THREAT-060`), verbatim Table A1 text + refs, official M1–M24 mitigations. `stride_category`/`typical_assets` are our annotations (need review). Excluded refs (4.2, 8.2, 11.2, 25.2, 30.x, 1.3, 3.1, 3.4) verified absent. Re-run verified deterministic.
- `asset_catalogue.json` expanded 4 → 12 assets; `tcu_architecture.json` extended (C-06–C-08, I-06–I-09). Both validated: no dangling asset refs, arch passes `Architecture` validation, library loads via `load_records`.
- **Breaking:** old `THREAT-001`–`THREAT-005` IDs now point to different threats; anything recorded against old IDs is stale.
- Added `Non-repudiation` to `SecurityProperty` enum (`app/schemas.py`) to match `ASSET-05`.
- Rewrote `Documentation/Synthetic_Data_Validation.md` as a provenance report (verbatim vs mapped-by-us split, exclusions, open items: M17 wording absent, refs 14.x/22.1 unaccounted).

## Dedup cleanup (2026-10-07)
- Deleted legacy `src/models.py` (stale subset of `Code/app/schemas.py`: missing review fields, citations, structured impact/feasibility, Risk, audit).
- Deleted top-level `data/` (stale duplicate of `Input_Data/` with conflicting IDs: `COMP-*/THREAT-LIB-*` vs canonical `C-*/THREAT-*`). `Input_Data/` is the single canonical fixture location per PLAN §2.
- Deleted generated artefacts from the tree (`Code/tara.db`, all `__pycache__/`); added `Code/.gitignore` (`__pycache__/`, `*.pyc`, `.env`, `tara.db`, `chroma_db/`).
- Removed unused `List` import in `Code/app/db.py`.

## In progress
- None.

## Next
- Frame + agentic upgrade complete. Remaining (out of scope per PLAN §8): real datasets beyond the R155 library, evaluation numbers, video, declarations, final ZIP.
- Optional hardening later: auth on the API, Alembic migrations, Chroma persistence path review, pagination on list endpoints.

## Key decisions
- Frame only: data is either regulation-sourced (`threat_library.json` via the builder script) or synthetic TCU fixtures (`Input_Data/`); every record states its provenance in `Synthetic_Data_Validation.md`.
- Config-only provider switching; mock provider lets the full pipeline run offline and in tests.
- Prompts will live in `Model_Prompts_Config/` as versioned templates, never hard-coded.
- AI output must cite source IDs from the retrieved library; anything uncited is flagged "needs expert review".

## Known gaps
- `requirements.txt` at the workspace root (user installs manually); venv currently has the full set.
- No auth on the API; no Alembic migrations (init_db only); list endpoints unpaginated — all acceptable for the frame, flagged for hardening.
- Perf notes (2026-10-07): UI uses one shared HTTP client, 5 s GET cache (cleared on POST), 30 s health cache, `fileWatcherType = "none"`. The dev API server is single-worker: if it ever goes sluggish, restart it (a request wedged in model load blocks all others).
