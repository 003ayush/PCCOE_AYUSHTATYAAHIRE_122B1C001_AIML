"""Embeddings: SentenceTransformers when available, deterministic hash otherwise.

The hash embedder keeps the frame and tests hermetic (no model downloads).
Set ``EMBEDDING_MODEL`` in config to a sentence-transformers model name to
use real embeddings; a missing package/model falls back with a warning.
"""

from __future__ import annotations

import hashlib
import math
import warnings
from typing import List

from app.config import settings

EMBEDDING_DIM = 384  # matches bge-small-en-v1.5; also used by the hash embedder


def _hash_embed(text: str) -> List[float]:
    """Deterministic bag-of-words embedding over hashed tokens (L2-normalised)."""
    vec = [0.0] * EMBEDDING_DIM
    for token in text.lower().split():
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:2], "big") % EMBEDDING_DIM
        sign = 1.0 if digest[2] % 2 == 0 else -1.0
        vec[idx] += sign
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


class _SentenceTransformerEmbedder:
    """Thin wrapper so the store can treat both backends uniformly."""

    def __init__(self, model_name: str) -> None:
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name)

    def encode(self, texts: List[str]) -> List[List[float]]:
        """Encode a batch of texts into embedding vectors."""
        return [list(map(float, v)) for v in self._model.encode(texts)]


class _HashEmbedder:
    """Offline embedder implementing the same ``encode`` contract."""

    def encode(self, texts: List[str]) -> List[List[float]]:
        """Embed each text with the deterministic hash embedder."""
        return [_hash_embed(t) for t in texts]


def get_embedder():
    """Return a SentenceTransformers embedder, else the hash fallback."""
    try:
        return _SentenceTransformerEmbedder(settings.embedding_model)
    except Exception:
        warnings.warn(
            f"sentence-transformers/model '{settings.embedding_model}' unavailable; "
            "using deterministic hash embeddings (PLACEHOLDER quality)"
        )
        return _HashEmbedder()
