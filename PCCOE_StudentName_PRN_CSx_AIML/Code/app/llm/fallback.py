"""Fallback chain: try each configured client in order, return first success."""

from __future__ import annotations

from typing import List

from app.llm.base import LLMClient


class FallbackChain:
    """Wraps several clients; on provider errors it moves to the next one."""

    name = "fallback-chain"

    def __init__(self, clients: List[LLMClient]) -> None:
        """Require at least one client; order defines priority."""
        if not clients:
            raise ValueError("FallbackChain needs at least one client")
        self._clients = clients

    def complete(self, prompt: str, system: str = "") -> str:
        """Return the first successful completion, or raise the last error."""
        last_error: Exception | None = None
        for client in self._clients:
            try:
                return client.complete(prompt, system=system)
            except Exception as exc:  # provider/network failure -> try next
                last_error = exc
        raise RuntimeError(f"All LLM providers failed: {last_error}") from last_error
