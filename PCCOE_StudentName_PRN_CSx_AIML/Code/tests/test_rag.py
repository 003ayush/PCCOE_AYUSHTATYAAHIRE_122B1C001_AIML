"""RAG: loaders for JSON/XML/CSV, ingest, filtered retrieval, empty store."""

import pytest

from app.rag.loaders import load_records
from app.rag.embeddings import _HashEmbedder
from app.rag.store import InMemoryStore, RAGStore


def _store():
    return RAGStore(embedder=_HashEmbedder(), store=InMemoryStore())


def test_load_json_and_reject_markdown(tmp_path):
    """JSON array loads; unsupported extensions raise a clear error."""
    f = tmp_path / "lib.json"
    f.write_text('[{"id": "TH-1", "title": "Spoofing", "stride_category": "Spoofing"}]', encoding="utf-8")
    recs = load_records(f)
    assert recs[0]["id"] == "TH-1" and "Spoofing" in recs[0]["text"]
    with pytest.raises(ValueError):
        load_records(tmp_path / "lib.md")


def test_load_csv_and_xml(tmp_path):
    """CSV header rows and XML child elements both become records."""
    csv_f = tmp_path / "lib.csv"
    csv_f.write_text("id,title\nTH-2,Denial of service\n", encoding="utf-8")
    xml_f = tmp_path / "lib.xml"
    xml_f.write_text('<lib><threat id="TH-3"><title>Tampering</title></threat></lib>', encoding="utf-8")
    assert load_records(csv_f)[0]["id"] == "TH-2"
    assert load_records(xml_f)[0]["id"] == "TH-3"


def test_ingest_empty_is_noop_and_retrieve_filters():
    """Empty ingest returns 0; category filter narrows retrieval."""
    s = _store()
    assert s.ingest([]) == 0
    assert s.retrieve("anything") == []
    s.ingest([
        {"id": "A", "text": "spoofing backend server", "stride_category": "Spoofing"},
        {"id": "B", "text": "denial of service flood", "stride_category": "Denial of Service"},
    ])
    hits = s.retrieve("spoofing attack", category="Spoofing")
    assert [h["id"] for h in hits] == ["A"]


def test_real_library_loads():
    """The shipped 60-record library loads through the same path."""
    import pathlib
    lib = pathlib.Path(__file__).resolve().parents[2] / "Input_Data" / "threat_library.json"
    recs = load_records(lib)
    assert len(recs) == 60


def test_light_mode_fallbacks_without_ml_packages(monkeypatch):
    """Core-only install (no chromadb/torch): hash embeddings + in-memory store, still functional."""
    import sys
    monkeypatch.setitem(sys.modules, "chromadb", None)
    monkeypatch.setitem(sys.modules, "sentence_transformers", None)
    from app.rag.embeddings import get_embedder
    from app.rag.store import RAGStore
    from app.rag.store import InMemoryStore
    from app.rag.embeddings import _HashEmbedder
    assert type(get_embedder()).__name__ == "_HashEmbedder"
    store = RAGStore(embedder=_HashEmbedder())  # ChromaStore init fails -> in-memory fallback
    assert type(store.store).__name__ == "InMemoryStore"
    assert store.ingest([{"id": "A", "text": "spoofing backend", "stride_category": "Spoofing"}]) == 1
    assert [h["id"] for h in store.retrieve("spoofing", category="Spoofing")] == ["A"]


def test_ensure_indexes_once_then_skips(tmp_path):
    """First call ingests the file; second call sees a non-empty index; missing file is a no-op."""
    from app.rag.store import ensure_library_indexed
    lib = tmp_path / "threat_library.json"
    lib.write_text('[{"id": "TH-1", "title": "Spoofing", "stride_category": "Spoofing"}]', encoding="utf-8")
    store = RAGStore(embedder=_HashEmbedder(), store=InMemoryStore())
    assert ensure_library_indexed(lib, store) == 1
    assert ensure_library_indexed(lib, store) == 0
    assert ensure_library_indexed(tmp_path / "absent.json", _store()) == 0
