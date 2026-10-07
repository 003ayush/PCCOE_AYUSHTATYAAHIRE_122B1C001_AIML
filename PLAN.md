# PLAN.md - TARA Assistant: Frame Build (No Data Yet)

> **For the developer agent.** Read `PROJECT.md`, this file, and `.agents/rules/project-workflow.md` before starting.

## 0. Scope of this build
We are building the **frame only**: architecture, modules, UI shell, and wiring with clearly marked extension points.
- **Real data is NOT available yet.** Do not invent large datasets. Use tiny, clearly labelled placeholder fixtures only where needed to prove the wiring works, and mark them `PLACEHOLDER`.
- Data (TCU architecture, threat library, etc.) will be wired in later. Design every data entry point so swapping in real files needs **no code changes** (config or file drop only).
- Research context is in the research notes (TCU, UN R155 Annex 5, ISO/SAE 21434 metrics) for later data work.

## 1. Non-negotiable working rules
1. **Approval gate:** do not start coding until the user approves this plan.
2. **Concise, idiomatic code.** If a library function or built-in does it in a few lines, use it. No long manual code, no reinvented utilities. Small, reusable functions.
3. **Proper comments:** a module docstring, a docstring for every public function and class, and inline comments for non-obvious logic.
4. **Always update `README.md` and `CONTEXT.md`** in the same change as the code.
   - `README.md`: setup, run instructions, architecture overview.
   - `CONTEXT.md`: current status of the app: done, in progress, next, key decisions, known gaps.
5. **Human-in-the-loop and traceability:** AI output must be citable to approved sources, and nothing is final until a reviewer approves it.
6. AI is a **decision-support assistant**: it analyses the architecture from an attacker-oriented perspective to identify assets, exposed interfaces, trust boundaries and attack surfaces. It does not act autonomously.

## 2. Mandatory folder structure
Root: `PCCOE_StudentName_PRN_CSx_AIML/` (placeholders; the user will supply real values).

```
PCCOE_StudentName_PRN_CSx_AIML/
├── Synopsis/
├── Input_Data/             # empty for now; real data dropped in later
├── Code/                   # application
├── Model_Prompts_Config/   # prompts, provider config, .env.example
├── Evaluation_Results/
├── Documentation/          # README.md, CONTEXT.md, diagrams
├── Video/
├── Declarations/
└── (ZIP of entire folder at the end)
```

## 3. Tech stack
Streamlit (UI), FastAPI (API), ChromaDB (vector store), SQLite via SQLAlchemy (structured storage), Pydantic (schemas), an OpenAI-compatible LLM client with free providers (Gemini, Groq, OpenRouter, NVIDIA) behind one interface, and open-source embeddings (Sentence Transformers or BGE).

## 4. Proposed layout of `Code/`
```
Code/
├── app/
│   ├── main.py            # FastAPI entry point
│   ├── config.py          # settings loaded from env and Model_Prompts_Config
│   ├── schemas.py         # Pydantic models: Asset, Interface, TrustBoundary, Threat, Risk, Mitigation
│   ├── db.py              # SQLite models, audit log
│   ├── llm/               # provider abstraction + fallback chain
│   ├── rag/               # ingest, embed, retrieve (ChromaDB)
│   ├── services/          # asset, attack-surface, threat, risk, mitigation, traceability
│   └── routers/           # API endpoints
├── ui/
│   └── streamlit_app.py   # multi-step review workflow
├── tests/
└── requirements.txt
```

## 5. Build phases (frame only)
Each phase ends with README.md and CONTEXT.md updated.

| Phase | Deliverable | Notes |
|---|---|---|
| 1 | Folder skeleton, `requirements.txt`, config loader, `.env.example` | No secrets committed |
| 2 | Pydantic schemas and SQLite models | Include audit log and approval status |
| 3 | LLM provider abstraction with fallback chain | Stub or mock provider for offline testing |
| 4 | RAG module: ingest, embed, retrieve with metadata filters | Works on an empty or placeholder library |
| 5 | Service layer: assets, attack surface, threats, risk, mitigation, traceability | Prompts live in `Model_Prompts_Config/`, not in code |
| 6 | FastAPI routers | Typed requests and responses |
| 7 | Streamlit UI shell | Upload, then assets, threats, risk, mitigations, report. Approve, edit or reject on every item |
| 8 | Report export and tests | Traceability: asset to threat to risk to control to test |

### 5a. Agentic upgrade (LangGraph + Knowledge Agent)
Phases 5-8 are procedural (service -> `rag.retrieve` -> prompt -> LLM). This upgrade replaces the pipeline internals with a LangGraph `StateGraph`. API routes, schemas, and the UI contract stay unchanged. Approval gate applies before coding.

| Phase | Deliverable | Notes |
|---|---|---|
| 9 | Add `langgraph` and `langchain-core` to `requirements.txt`; new package `Code/app/agents/` with `state.py` (`TaraState` TypedDict: architecture, assets, interfaces, knowledge_requests, retrieved_context, drafts, errors) | Wrap our `LLMClient` as a graph node; do not couple to a LangChain chat model, so provider fallback and the mock provider keep working |
| 10 | **Knowledge Agent** (`agents/knowledge.py`): the only component allowed to touch `RAGStore`. Input: user input plus the analyst's structured data requests (`{query, filters, top_k}`). Output: citable records (`id`, `text`, `source`) into `retrieved_context` | Deterministic (no LLM) by default; optional LLM query-rewrite behind a config flag. Applies metadata filters (STRIDE, asset type). Returns an explicit "no match" result so uncited output is flagged |
| 11 | **Analyst Agent** (`agents/analyst.py`): wraps the existing prompt templates. Emits either `drafts` or `knowledge_requests` when it needs more data | Prompts stay in `Model_Prompts_Config/`; add a `data_request` field to the output schema; version bump to `v2` |
| 12 | Graph wiring (`agents/graph.py`): `knowledge -> analyst -> (needs_more? loop to knowledge : validate) -> end` | Hard cap on loops (config `MAX_KNOWLEDGE_ROUNDS`, default 2); validation node does Pydantic check and `flag_uncited`; on exhaustion the output goes to review as "needs expert review" |
| 13 | Migrate pipelines one by one: threats first, then mitigations, assets, risk rationale. Services call `graph.invoke`; routers unchanged | Risk values stay matrix-computed, never LLM-decided. Human-in-the-loop approval stays outside the graph (review endpoints) |
| 14 | Tests and docs | Mock-LLM graph tests: knowledge agent returns filtered records; loop cap respected; uncited output flagged; existing 24 tests still pass. Update README.md (architecture diagram) and CONTEXT.md |

## 6. Design requirements
- **Architecture Ingestion (JSON/XML):** The application will ingest structured text formats (JSON, XML, or CSV) representing exports from professional modeling tools (like Enterprise Architect or AUTOSAR). We will *not* use Multimodal Image AI to read visual diagrams, as structured data is more reliable and industry-standard for automated pipelines. Validate all uploads with Pydantic and show clear errors.
- **Prompts externalised:** versioned template files with a version in each header.
- **Structured LLM output:** JSON schema validation with retries.
- **Citations:** every suggestion carries source IDs from the retrieved library. Anything not backed by the library is flagged "needs expert review".
- **Risk logic:** ISO/SAE 21434 style. Impact categories are Safety, Financial, Operational and Privacy. Attack feasibility uses expertise, resources, knowledge and window of opportunity. Risk value comes from a configurable matrix.
- **Configurable and private-ready:** switching to a private or local LLM is a config change only.
- **Audit:** log who approved what, when, and why.
- **Separation of knowledge and reasoning:** the LLM/Analyst never calls RAG directly. It states what data it needs; the Knowledge Agent retrieves it and passes it on. Every retrieval (query, filters, returned IDs) is recorded in the audit/trace for traceability.
- **Bounded agent loops:** all graph cycles have a hard iteration cap; the app must remain fully functional offline with the mock provider.

## 7. Definition of done for the frame
- The app starts, the UI renders every step, and the API docs load.
- A mock LLM run passes end to end on tiny placeholder fixtures.
- Tests pass and the code is commented.
- README.md and CONTEXT.md are accurate.

### Definition of done for the agentic upgrade
- Only `agents/knowledge.py` imports `RAGStore` (checked by a test).
- Threat suggestion runs through the LangGraph graph with the mock LLM and returns the same schema as before.
- Loop cap and no-match paths are tested; all existing tests still pass.
- README.md (architecture) and CONTEXT.md updated.

## 8. Out of scope for now
Real datasets, the threat library content, evaluation numbers, the video, and the declarations.
