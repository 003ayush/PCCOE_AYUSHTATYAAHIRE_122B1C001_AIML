"""LLM client interface.

All providers implement ``complete()`` returning raw text (usually JSON).
Structured validation/retries happen in the service layer, keeping this
interface minimal and provider-agnostic.
"""

from __future__ import annotations

from typing import Protocol


class LLMClient(Protocol):
    """Minimal chat-completion contract used across the app."""

    name: str

    def complete(self, prompt: str, system: str = "") -> str:
        """Return the model's text completion for the given prompt."""
        ...
