"""Vector store over the threat library, backed by ChromaDB.

If chromadb is not installed we fall back to a small in-memory cosine
store so the frame and tests still run. Metadata filters (e.g. by
``stride_category``) are supported by both backends.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List, Optional

from app.config import settings
from app.rag.embeddings import get_embedder


def _cosine(a: List[float], b: List[float]) -> float:
    """Cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


class InMemoryStore:
    """Minimal cosine-similarity store with the same interface as ChromaStore."""

    def __init__(self) -> None:
        """Start empty."""
        self._rows: List[Dict] = []

    def add(self, records: List[Dict], embeddings: List[List[float]]) -> None:
        """Insert records with their precomputed embeddings."""
        for rec, emb in zip(records, embeddings):
            self._rows.append({**rec, "_emb": emb})

    def query(
        self, embedding: List[float], top_k: int, where: Optional[Dict] = None
    ) -> List[Dict]:
        """Return the top-k rows by cosine similarity, honouring metadata filters."""
        rows = self._rows
        if where:  # exact-match metadata filter, same semantics as Chroma 'where'
            rows = [r for r in rows if all(r.get(k) == v for k, v in where.items())]
        scored = sorted(rows, key=lambda r: _cosine(embedding, r["_emb"]), reverse=True)
        return [{k: v for k, v in r.items() if k != "_emb"} for r in scored[:top_k]]

    def count(self) -> int:
        """Number of indexed records."""
        return len(self._rows)


class ChromaStore:
    """Persistent ChromaDB collection wrapper."""

    def __init__(self, persist_dir: Path) -> None:
        """Open (or create) the persisted collection."""
        import chromadb

        client = chromadb.PersistentClient(path=str(persist_dir))
        self._col = client.get_or_create_collection("threat_library")

    def add(self, records: List[Dict], embeddings: List[List[float]]) -> None:
        """Upsert records with caller-provided embeddings and metadata."""
        self._col.upsert(
            ids=[r["id"] for r in records],
            embeddings=embeddings,
            documents=[r["text"] for r in records],
            metadatas=[
                {k: v for k, v in r.items() if isinstance(v, (str, int, float, bool))}
                for r in records
            ],
        )

    def query(
        self, embedding: List[float], top_k: int, where: Optional[Dict] = None
    ) -> List[Dict]:
        """Query by embedding with optional Chroma metadata filter."""
        if self._col.count() == 0:  # empty library is a valid state
            return []
        res = self._col.query(
            query_embeddings=[embedding],
            n_results=min(top_k, self._col.count()),
            where=where,
        )
        out = []
        for doc, meta in zip(res["documents"][0], res["metadatas"][0]):
            out.append({**meta, "text": doc})
        return out

    def count(self) -> int:
        """Number of indexed records."""
        return self._col.count()


class RAGStore:
    """High-level ingest/retrieve facade used by the services."""

    def __init__(self, embedder=None, store=None) -> None:
        """Allow dependency injection for tests; default to configured backends."""
        self.embedder = embedder or get_embedder()
        if store is not None:
            self.store = store
        else:
            try:
                self.store = ChromaStore(settings.chroma_dir)
            except Exception:
                self.store = InMemoryStore()

    def ingest(self, records: List[Dict]) -> int:
        """Embed and index records; returns how many were added."""
        if not records:
            return 0
        vectors = self.embedder.encode([r["text"] for r in records])
        self.store.add(records, vectors)
        return len(records)

    def retrieve(
        self, query: str, top_k: int = 5, category: Optional[str] = None
    ) -> List[Dict]:
        """Semantic search; optional filter on ``stride_category``."""
        where = {"stride_category": category} if category else None
        return self.store.query(self.embedder.encode([query])[0], top_k, where=where)

    def count(self) -> int:
        """Number of indexed records (0 when the backend is unreachable)."""
        try:
            return self.store.count()
        except Exception:
            return 0


def ensure_library_indexed(library_path=None, store: "RAGStore | None" = None) -> int:
    """Ingest the threat library if the index is empty; return records added.

    Never raises: a missing file or a failed backend leaves an empty index,
    which the graph surfaces as NO_MATCH (flagged, never invented).
    """
    from app.rag.loaders import load_records

    store = store or RAGStore()
    if store.count() > 0:
        return 0
    path = Path(library_path) if library_path else settings.input_data_dir / "threat_library.json"
    if not path.is_file():
        return 0
    try:
        return store.ingest(load_records(path))
    except Exception:
        return 0
