"""LLM provider package: abstraction, mock, presets, fallback chain."""

from __future__ import annotations

from app.config import settings
from app.llm.base import LLMClient
from app.llm.fallback import FallbackChain
from app.llm.mock import MockLLMClient
from app.llm.providers import PROVIDER_PRESETS, build_provider


def get_llm_client() -> LLMClient:
    """Build the active client chain from settings.

    The configured provider is tried first; any other provider with a key
    in the environment becomes a fallback. With no keys at all we get the
    mock provider, which keeps the frame runnable offline.
    """
    if settings.llm_provider == "mock":
        return MockLLMClient()

    clients = []
    primary = build_provider(settings.llm_provider)
    if primary is not None:
        clients.append(primary)
    for name in PROVIDER_PRESETS:
        if name != settings.llm_provider:
            extra = build_provider(name)
            if extra is not None:
                clients.append(extra)
    if not clients:  # configured provider had no key -> offline fallback
        return MockLLMClient()
    return clients[0] if len(clients) == 1 else FallbackChain(clients)
