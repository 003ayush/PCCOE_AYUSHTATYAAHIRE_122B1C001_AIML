"""FastAPI entry point: health, config (no secrets), and all routers."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.db import init_db
from app.routers import router


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Create tables and index the threat library (both idempotent).

    First boot downloads/loads the embedding model, so startup takes under a
    minute; later boots reuse the persisted Chroma collection and skip ingest.
    """
    init_db()
    try:
        from app.rag import ensure_library_indexed

        print(f"threat library indexed: {ensure_library_indexed()} new records")
    except Exception as exc:
        print(f"library ingest skipped ({exc}); retrieval will report NO_MATCH")
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(router)

init_db()  # also run at import so plain TestClient use (no lifespan) works; idempotent


@app.get("/health")
def health() -> dict:
    """Liveness probe."""
    return {"status": "ok", "app": settings.app_name}


@app.get("/config")
def config() -> dict:
    """Non-secret runtime config (provider name, models, paths)."""
    from app.llm import get_llm_client

    client = get_llm_client()
    return {
        "app_name": settings.app_name,
        "llm_provider": settings.llm_provider,
        "active_client": client.name,
        "active_model": getattr(client, "model", ""),
        "embedding_model": settings.embedding_model,
        "input_data_dir": str(settings.input_data_dir),
    }
